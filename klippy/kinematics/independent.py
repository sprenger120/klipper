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
from klippy.stepper import PrinterStepper, MCU_stepper

class IndependentKinematics:
    def __init__(self, toolhead : ToolHead, config : ConfigWrapper):
        self._printer : Printer = config.get_printer()
        self._toolhead : ToolHead = toolhead
        self._raw_config : RawConfigParser = config.fileconfig

        self._steppers : [Dict[str, MCU_stepper]] = []

        # load MCU_Stepper instances
        # We are not bound by XYZ and have to look for config section names starting with "stepper_.."
        # To not have to modify the GCode interface steppers are numerated alphabetically
        # scheme: index 0: aa, 1: ab, ..., 25th: az, 26: aaa, 27: aab
        for section in self._raw_config.sections():
            DELIMITER = "_"
            if section.startswith('stepper' + DELIMITER):
                axis_name : str = section.split(DELIMITER)[1]
                # PrinterStepper is a helper function to create a MCU_Stepper object
                inst = PrinterStepper(config.getsection(section))
                self._steppers.append({axis_name : inst})

        self.axes_minmax = toolhead.Coord(0., 0., 0., 0.)
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

def load_kinematics(toolhead, config):
    return IndependentKinematics(toolhead, config)
