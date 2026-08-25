# Independent axis support (for controlling non-3d printer machines)
#
# Copyright (C) 2025 Michael Albrecht (micha.albrecht95@gmail.com)
#
# This file may be distributed under the terms of the GNU GPLv3 license.

from typing import Dict, List, Tuple

from klippy.configfile import ConfigWrapper
from klippy.toolhead import ToolHead
from klippy.klippy import Printer
from klippy.stepper import MCU_stepper, error, PrinterRail
from klippy.gcode import Coord
from klippy.variable_axes_count import enumerate_axes_lowercase, getNumberOfAxes
from klippy.extras.homing import Homing


class IndependentKinematics:
    __UNHOMED_AXIS_LIMIT = (1.0, -1.0)
    def __init__(self, toolhead: ToolHead, config: ConfigWrapper):
        self._printer: Printer = config.get_printer()
        self._toolhead: ToolHead = toolhead

        self._axes: List[Tuple[str, PrinterRail]] = []
        self._number_of_axes: int = getNumberOfAxes()

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
            self._axes.append((axis_name, inst))

        # toolhead.Coord is fixed to X,Y,Z,E coordinates
        # todo still necessary?
        # Leaving it for now until a solution that satisfies our dynamic amount of steppers is found
        self.axes_minmax = toolhead.Coord()

        self.limits: List[Tuple[float, float]] = [self.__UNHOMED_AXIS_LIMIT] * self._number_of_axes
    def get_steppers(self) -> List[MCU_stepper]:
        return [rail.get_steppers()[0] for axis_name, rail in self._axes]

    def calc_position(self, stepper_positions):
        return [0, 0, 0]

    def set_position(self, newpos: List[float], homing_axes: List[str] | None):
        # inform rail about update which informs all lower level components
        for axis_name, rail in self._axes:
            rail.set_position(newpos)

        if homing_axes is None: return
        # set axis limit, signal that it is homed
        for axis_name in homing_axes:
            for index, entry in enumerate(self._axes):
                if entry[0] == axis_name:
                    rail = entry[1]
                    self.limits[index] = rail.get_range()
                    break

    def clear_homing_state(self, clear_axes : List[str]):
        for axis_name in clear_axes:
            for index, entry in enumerate(self._axes):
                if entry[0] == axis_name:
                    self.limits[index] = self.__UNHOMED_AXIS_LIMIT
                    break

    def home(self, homing_state: Homing):
        # Each axis is homed independently and in order
        for axis in homing_state.get_axes():
            if axis < 0 or axis > self._number_of_axes:
                raise "Unknown axis index requested"
            rail = self._axes[axis][1]

            # Determine movement
            position_min, position_max = rail.get_range()
            hi = rail.get_homing_info()
            # Axis that don't get homed are None
            homepos : List[float | None] = [None] * self._number_of_axes
            homepos[axis] = hi.position_endstop
            forcepos : List[float | None] = list(homepos)
            if hi.positive_dir:
                forcepos[axis] -= 1.5 * (hi.position_endstop - position_min)
            else:
                forcepos[axis] += 1.5 * (position_max - hi.position_endstop)
            # Perform homing
            homing_state.home_rails([rail], forcepos, homepos)

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
        for axis_name, rail in self._axes:
            if axis_name == searched_axis_name[1]:
                return rail.get_steppers()[0]
        return None


def load_kinematics(toolhead, config):
    return IndependentKinematics(toolhead, config)
