// same70 half-duplex serial port
//
// Copyright (C) 2026  Michael Albrecht <michael.albrecht@ovgu.de>
//
// This file may be distributed under the terms of the GNU GPLv3 license.

#include "autoconf.h" // CONFIG_SERIAL_BAUD
#include "board/armcm_boot.h" // armcm_enable_irq
#include "board/serial_irq.h" // serial_rx_data
#include "command.h" // DECL_CONSTANT_STR
#include "internal.h" // gpio_peripheral
#include "sched.h" // DECL_INIT
#include "gpio.h" // gpio_out_setup
#include "board/io.h"

#ifdef CONFIG_MACH_SAME70
#define USARTx_IRQn USART2_IRQn
static Usart * const Port = USART2;
static const uint32_t Pmc_id = ID_USART2;
static const uint32_t rx_pin = GPIO('D', 15), tx_pin = GPIO('D', 16);
static const uint32_t drive_enable_pin = GPIO('C', 10);
static const char usart_periph = 'B';
DECL_CONSTANT_STR("RESERVE_PINS_serial", "PD15,PD16,PC10");
#else
#error "Architecture not supported"
#endif


struct gpio_out drive_enable_out = {0};
uint8_t first_serial_data_byte = {};

#define STATE_IDLE 0
#define STATE_INITIAL_TXRDY 1
#define STATE_IDLE_LINE_TIMEOUT 2
#define STATE_BREAK_FINSHED_TXRDY 3
#define STATE_TX_UNTIL_QUEUE_EMPTY_TXRDY 4
#define STATE_TX_UNTIL_EMPTY_TXEMPTY 5
uint8_t state = STATE_IDLE;


void
serial_enable_tx_irq(void)
{
    Port->US_IER = US_IER_TXRDY;
}

void
serial_disable_tx_irq(void)
{
    Port->US_IDR = US_IDR_TXRDY;
}

void
serial_data_direction_tx(void)
{
    //Port->US_CR = US_CR_RXDIS | US_CR_TXEN;
    gpio_out_write(drive_enable_out, 1);
}


void
serial_data_direction_rx(void)
{
    //Port->US_CR = US_CR_RXEN | US_CR_TXDIS;
    gpio_out_write(drive_enable_out, 0);
}

void
serial_start_break(void)
{
    // Starts transmission of a break after the characters present in US_THR and the Transmit Shift Register have
    // been transmitted. No effect if a break is already being transmitted.
    Port->US_CR = US_CR_USART_STTBRK_Msk;
}

void
serial_stop_break(void)
{
    // Stops transmission of the break after a minimum of one character length and transmits a high level during
    // 12-bit periods. No effect if no break is being transmitted.
    Port->US_CR = US_CR_USART_STPBRK_Msk;
}

void
serial_start_timeout(void)
{
    // timeout length, two characters of 8N1
    Port->US_RTOR = (1+8+1) * 2;
    // start timeout immediately
    Port->US_CR = US_CR_USART_RETTO_Msk;
    // enable timeout interrupt
    Port->US_IER = US_IER_USART_LIN_TIMEOUT_Msk;
}

void
serial_end_timeout(void)
{
    // disable timeout interrupt
    Port->US_IDR = US_IDR_USART_LIN_TIMEOUT_Msk;
    // clear timeout condition causing interrupt
    Port->US_CR = US_CR_USART_STTTO_Msk;
    // disable timeout detection
    Port->US_RTOR = 0;
}



void
USARTx_Handler(void)
{
    uint8_t data;
    uint32_t status = Port->US_CSR;
    if (status & US_CSR_RXRDY_Msk)
    {
        serial_rx_byte(Port->US_RHR);
        return;
    }
    if (status & US_CSR_TXRDY_Msk) {
        // applications signals available TX data by enabling TXRDY IRQ
        // -> TX can't be disabled to avoid getting into this branch
        //     to never miss chance to TX.
        // This switch-case has to have all available states to not land in
        // default case even when current state doesn't care about TXRDY.
        // TXRDY is spurious in nature.
        switch (readb(&state))
        {
        case STATE_IDLE:
            serial_disable_tx_irq();
            if (serial_get_tx_byte(&first_serial_data_byte))
            {
                // no data available
                break;
            }
            writeb(&state, STATE_INITIAL_TXRDY);
            serial_data_direction_rx();
            serial_start_timeout();
            break;
        case STATE_INITIAL_TXRDY:
            // avoid default case due to spurious TXRDY nature
            break;
        case STATE_IDLE_LINE_TIMEOUT:
            serial_stop_break();
            serial_data_direction_tx();
            Port->US_THR = first_serial_data_byte;
            serial_enable_tx_irq();
            writeb(&state, STATE_BREAK_FINSHED_TXRDY);
            break;
        case STATE_BREAK_FINSHED_TXRDY:
            [[fallthrough]];
        case STATE_TX_UNTIL_QUEUE_EMPTY_TXRDY:
            writeb(&state, STATE_TX_UNTIL_QUEUE_EMPTY_TXRDY);
            if (serial_get_tx_byte(&data))
            {
                // TX queue emptied
                // wait for peripheral to signal it's completely finished

                serial_disable_tx_irq();
                // enable TXEMPTY irq
                Port->US_IER = US_IER_TXEMPTY_Msk;
                writeb(&state, STATE_TX_UNTIL_EMPTY_TXEMPTY);
                break;
            }
            Port->US_THR = data;
            break;
        case STATE_TX_UNTIL_EMPTY_TXEMPTY:
            // avoid default case due to spurious TXRDY nature
            break;
        default:
            shutdown("Invalid state");
        }
    }
    if (status & US_CSR_TXEMPTY_Msk)
    {
        // disable TXEMPTY irq
        Port->US_IDR = US_IDR_TXEMPTY_Msk;
        if (readb(&state) == STATE_TX_UNTIL_EMPTY_TXEMPTY)
        {
            serial_data_direction_rx();
            writeb(&state, STATE_IDLE);
        }
    }
    if (status & US_CSR_USART_LIN_TIMEOUT_Msk)
    {
        serial_end_timeout();
        if (readb(&state) == STATE_INITIAL_TXRDY)
        {
            volatile int a = 0;
            serial_data_direction_tx();
            serial_start_break();
            serial_enable_tx_irq();
            writeb(&state, STATE_IDLE_LINE_TIMEOUT);
        }
    }
}


void
serial_halfduplex_init(void)
{
    gpio_peripheral(rx_pin, usart_periph, 1);
    gpio_peripheral(tx_pin, usart_periph, 0);
    drive_enable_out = gpio_out_setup(drive_enable_pin, 0);

    // Reset uart
    enable_pclock(Pmc_id);
    Port->US_CR = (US_CR_RSTRX | US_CR_RSTTX
                     | US_CR_RXDIS | US_CR_TXDIS);
    Port->US_IDR = 0xFFFFFFFF;

    // Enable uart
    Port->US_MR = (US_MR_USART_MODE_NORMAL | US_MR_USART_CHMODE_NORMAL | US_MR_USCLKS_MCK |
        US_MR_CHRL_8_BIT | US_MR_USART_PAR_NO);
    Port->US_BRGR = get_pclock_frequency(Pmc_id) / (16 * CONFIG_SERIAL_BAUD);

    serial_data_direction_rx();
    Port->US_CR = US_CR_RXEN_Msk | US_CR_TXEN_Msk;
    Port->US_IER = US_IER_RXRDY_Msk;
    armcm_enable_irq(USARTx_Handler, USARTx_IRQn, 0);
}
DECL_INIT(serial_halfduplex_init);