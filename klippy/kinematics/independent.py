# Independent axis support (for controlling non-3d printer machines)
#
# Copyright (C) 2025 Michael Albrecht (micha.albrecht95@gmail.com)
#
# This file may be distributed under the terms of the GNU GPLv3 license.

from typing import Dict, List, Tuple
from configparser import RawConfigParser

from klippy.configfile import ConfigWrapper
from klippy.toolhead import ToolHead
from klippy.klippy import Printer
from klippy.stepper import PrinterStepper, MCU_stepper, error, getNumberOfAxes, PrinterRail
from klippy.gcode import Coord
from klippy.variable_axes_count import enumerate_axes_lowercase
from klippy.extras.homing import Homing


class IndependentKinematics:
    def __init__(self, toolhead: ToolHead, config: ConfigWrapper):
        self._printer: Printer = config.get_printer()
        self._toolhead: ToolHead = toolhead

        self._axes: List[Tuple[str, int, PrinterRail]] = []
        self._number_of_axes: int = getNumberOfAxes(config)

        # load PrinterRail instances
        # We are not bound by XYZ and have to look for config section names starting with "stepper_.."
        # To not have to modify the GCode interface steppers are numerated alphabetically
        # Also enforces clear naming without gaps
        for axis_name, axis_index in enumerate_axes_lowercase(self._number_of_axes).items():
            section_name = "stepper_" + axis_name
            if not config.has_section(section_name):
                raise error(
                    "Config section {} not found. You defined {} stepper sections but there is an enumeration gap."
                    .format(section_name, self._number_of_axes))

            inst = PrinterRail(config.getsection(section_name))
            if inst is None:
                raise error("Creation of PrinterRail instance failed")
            inst.setup_itersolve('independent_stepper_alloc', axis_index)
            # all steppers must be able to move at the same time, so they get to share the same trapq
            inst.set_trapq(self._toolhead.get_trapq())
            # register stepper instances with ToolHead
            self._toolhead.register_step_generator(inst.get_steppers()[0].generate_steps)
            self._axes.append((axis_name, axis_index, inst))


        # toolhead.Coord is fixed to X,Y,Z,E coordinates
        # todo still necessary?
        # Leaving it for now until a solution that satisfies our dynamic amount of steppers is found
        self.axes_minmax: Coord = toolhead.Coord(0., 0., 0., 0.)

    def get_steppers(self) -> List[MCU_stepper]:
        return [rail.get_steppers()[0] for axis_name, index, rail in self._axes]

    def calc_position(self, stepper_positions):
        return [0, 0, 0]

    def set_position(self, newpos : List, homing_axes : str):
        # todo required for homing
        # todo newpos list is usually four entries long, how long is it now?
        # todo ToolHead.set_position to independent size
        pass

    def clear_homing_state(self, clear_axes):
        pass

    def home(self, homing_state : Homing):
        # todo required for homing
        # todo setup for homing
        # homing_state.home call to start the process
        pass

    def check_move(self, move):
        pass

    def get_status(self, eventtime):
        return {
            'homed_axes': '',
            'axis_minimum': self.axes_minmax,
            'axis_maximum': self.axes_minmax,
        }

    # config_name is 'stepper_x' or 'stepper_aa'
    def lookup_stepper(self, config_name: str) -> MCU_stepper | None:
        searched_axis_name = config_name.split('_')
        if len(searched_axis_name) != 2:
            return None
        for axis_name, index, rail in self._axes:
            if axis_name == searched_axis_name[1]:
                return rail.get_steppers()[0]
        return None


def load_kinematics(toolhead, config):
    return IndependentKinematics(toolhead, config)
