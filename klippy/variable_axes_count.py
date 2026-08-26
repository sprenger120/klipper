# Helper functions for handling non-fixed amount of axis and their naming scheme
#
# Copyright (C) 2025 Michael Albrecht (micha.albrecht95@gmail.com)
#
# This file may be distributed under the terms of the GNU GPLv3 license.
from token import NUMBER
from typing import Dict
from string import ascii_lowercase, ascii_uppercase
import configparser

# Returns dictionary of {axis name: 0-based index}
# Axis name consists of lowercase english alphabet letters in the following scheme:
# a: 0, b: 1, c: 2, ..., z: 25, aa: 26, ab: 27, ..., az, ba, bb
def enumerate_axes_lowercase(number_of_axis: int) -> Dict[str, int]:
    return _enumerate_axes(number_of_axis, 'a', ascii_lowercase)


def enumerate_axes_uppercase(number_of_axis: int) -> Dict[str, int]:
    return _enumerate_axes(number_of_axis, 'A', ascii_uppercase)


def _enumerate_axes(number_of_axes: int, prefix: str, letters: str) -> Dict[str, int]:
    output: Dict[str, int] = {}
    _BASE = len(letters)
    for i in range (1, number_of_axes+1):
        number = i
        axis_name = ""
        while number > 0:
            number, remainder = divmod(number-1, _BASE)
            axis_name = letters[remainder] + axis_name
        output[prefix + axis_name] = i-1
    return output


__NUMBER_OF_AXIS : int | None = None
def getNumberOfAxes() -> int:
    if __NUMBER_OF_AXIS is None:
        raise "init_number_of_axis() not called at least once before"
    return __NUMBER_OF_AXIS

def init_number_of_axis(config_file : str):
    cfg = configparser.ConfigParser()
    cfg.read(config_file)
    global __NUMBER_OF_AXIS
    __NUMBER_OF_AXIS = \
        sum(s.startswith("stepper_") for s in cfg.sections())