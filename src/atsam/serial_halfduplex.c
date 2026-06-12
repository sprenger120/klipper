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

#define STEP_WAIT_IDLE 0
#define STEP_WAIT_BREAK 1
#define STEP_TX_UNTIL_EMPTY 2
#define STEP_FINISHED 3
uint8_t step = STEP_FINISHED;


// TX irq enabled -> check for data in queue
// - no data -> disable
// - data -> enable idle line detection, disable tx irq (wait for empty line until send)
// - Idle line IRQ received -> disable idle line, send break, enable tx irq
// - wait for tx irq, disable break, transmit until empty
// - disable tx irq

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

// after calling this function, wait for TXRDY and then call stop break
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
    uint32_t status = Port->US_CSR;
    if (status & US_CSR_RXRDY_Msk)
    {
        serial_rx_byte(Port->US_RHR);
    }
    if (status & US_CSR_TXRDY_Msk) {
        uint8_t data;
        // todo drive pin
        int ret = serial_get_tx_byte(&data);
        if (ret)
            serial_disable_tx_irq();
        else
            Port->US_THR = data;
        // drive pin disable on TXEMPTY
    }
    if (status & US_CSR_USART_LIN_TIMEOUT_Msk)
    {
        // todo
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
    Port->US_IER = US_IER_RXRDY_Msk;
    armcm_enable_irq(USARTx_Handler, USARTx_IRQn, 0);
    Port->US_CR = US_CR_RXEN | US_CR_TXEN;
}
DECL_INIT(serial_halfduplex_init);