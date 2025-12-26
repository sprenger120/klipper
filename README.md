Welcome to the Klipper project!

[![Klipper](docs/img/klipper-logo-small.png)](https://www.klipper3d.org/)

https://www.klipper3d.org/

The Klipper firmware controls 3d-Printers. It combines the power of a
general purpose computer with one or more micro-controllers. See the
[features document](https://www.klipper3d.org/Features.html) for more
information on why you should use the Klipper software.

Start by [installing Klipper software](https://www.klipper3d.org/Installation.html).

Klipper software is Free Software. See the [license](COPYING) or read
the [documentation](https://www.klipper3d.org/Overview.html). We
depend on the generous support from our
[sponsors](https://www.klipper3d.org/Sponsors.html).

## About this fork

klipper offers the unique ability to control to more than one 3D-Printer
motherboard which I used to let you add as many motion axis as you want.
This can be used make some cool motion art on a small dime as 3D-Printer 
electronics are very cheap to get.
Beware that the code is broken in multiple places and I would advise you 
to only use `G0` to move axis.

**This fork is extremely work in progress. I would encourage you to look at my changes**

## Configuration

Config looks almost like what you would normally use, but the axis enumeration
is different.

```ini
# first motherboard, doesn't matter which one must not have a name
[mcu]
serial: /dev/serial/by-id/usb-Klipper_stm32f446xx_240032000751323438353631-if00
baud: 375000
restart_method: command

# next motherboard named ender
[mcu ender]
serial: /dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AG0JPLUI-if00-port0
baud: 250000
restart_method: command

# new kinematic implemented by this fork (required)
[printer]
kinematics: independent
max_velocity: 300
max_accel: 8000

# all axis must follow this naming scheme
# aa, ab, ac, ..., az, aaa, aab, ...

# first board driver0
[stepper_aa]
step_pin: PF13
dir_pin: !PF12
enable_pin: !PF14
microsteps: 16
rotation_distance: 81.7

# first board driver1
[stepper_ab]
step_pin: PG0
dir_pin: PG1
enable_pin: !PF15
microsteps: 16
rotation_distance: 81.7

# ...

# note ender pin prefix, telling klipper which board the pins are attached to
# ender driver0 (x)
[stepper_as]
step_pin: ender:PF0
dir_pin: ender:PF1
enable_pin: !ender:PD7
microsteps: 16
rotation_distance: 81.7
```

# Usage

Start klipper as normal. Use Octoprint or another print host of your choosing to 
send GCode commands. They look like this 

```gcode
G0 AA10 AB-50.0 AS4 F200
```

You can no longer use X,Y,Z, E.. as axis names; feed rate (F) works. Homing works the same as long as you
have end stops for every axis. This might become tedious if you have a lot of motors.

