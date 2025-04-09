# Independent axis support (for controlling non-3d printer machines)
#
# Copyright (C) 2025 Michael Albrecht (micha.albrecht95@gmail.com)
#
# This file may be distributed under the terms of the GNU GPLv3 license.

from typing import Dict
from configparser import RawConfigParser

from klippy.configfile import ConfigWrapper
from klippy.toolhead import ToolHead
from klippy.klippy import Printer
from klippy.stepper import PrinterStepper, MCU_stepper, error, getNumberOfAxis
from klippy.gcode import Coord
from klippy.variable_axis_count import enumerate_axis


class IndependentKinematics:
    def __init__(self, toolhead: ToolHead, config: ConfigWrapper):
        self._printer: Printer = config.get_printer()
        self._toolhead: ToolHead = toolhead

        self._steppers: [Dict[str, MCU_stepper]] = []
        self._number_of_axis: int = getNumberOfAxis(config)

        # load MCU_Stepper instances
        # We are not bound by XYZ and have to look for config section names starting with "stepper_.."
        # To not have to modify the GCode interface steppers are numerated alphabetically
        # Also enforces clear naming without gaps
        for axis_name in enumerate_axis(self._number_of_axis).keys():
            section_name = "stepper_" + axis_name
            if not config.has_section(section_name):
                raise error(
                    "Config section {} not found. You defined {} stepper sections but there is an enumeration gap."
                    .format(section_name, self._number_of_axis))

            inst = self._create_and_setup_mcu_stepper_inst(config.getsection(section_name))
            if inst is None:
                raise error("Creation of MCU_Stepper instance failed")
            self._steppers.append({axis_name: inst})

        # toolhead.Coord is fixed to X,Y,Z,E coordinates
        # Leaving it for now until a solution that satisfies our dynamic amount of steppers is found
        self.axes_minmax: Coord = toolhead.Coord(0., 0., 0., 0.)

    def get_steppers(self) -> [MCU_stepper]:
        return [stepper for axis_name, stepper in self._steppers]

    def calc_position(self, stepper_positions):
        return [0, 0, 0]

    def set_position(self, newpos, homing_axes):
        pass

    def clear_homing_state(self, clear_axes):
        pass

    def home(self, homing_state):
        pass

    def check_move(self, move):
        pass

    def get_status(self, eventtime):
        return {
            'homed_axes': '',
            'axis_minimum': self.axes_minmax,
            'axis_maximum': self.axes_minmax,
        }

    def _create_and_setup_mcu_stepper_inst(self, stepper_section_config: ConfigWrapper) -> MCU_stepper | None:
        # PrinterStepper is a helper function to create an MCU_Stepper object
        inst: MCU_stepper = PrinterStepper(stepper_section_config)

        # cartesian_stepper_alloc will set a calc_position callback internally depending on axis name
        # it has callbacks for X,Y,Z and nothing else. Not having a callback may come back to bite.
        fake_axis = "0"
        inst.setup_itersolve('cartesian_stepper_alloc', fake_axis.encode())
        return inst


def load_kinematics(toolhead, config):
    return IndependentKinematics(toolhead, config)
