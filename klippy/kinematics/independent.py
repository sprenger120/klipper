# Independent axis support (for controlling non-3d printer machines)
#
# Copyright (C) 2025 Michael Albrecht (micha.albrecht95@gmail.com)
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import stepper
from . import idex_modes


import os
print(os.getcwd())

from klippy.configfile import ConfigWrapper
from klippy.toolhead import ToolHead

class IndependentKinematics:
    def __init__(self, toolhead : ToolHead, config : ConfigWrapper):
        self.printer = config.get_printer()
        self.test = config.section

        self.axes_minmax = toolhead.Coord(0., 0., 0., 0.)
    def get_steppers(self):
        return []
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
