# Helper functions for handling non-fixed amount of axis and their naming scheme
#
# Copyright (C) 2025 Michael Albrecht (micha.albrecht95@gmail.com)
#
# This file may be distributed under the terms of the GNU GPLv3 license.

from typing import Dict
from string import ascii_lowercase, ascii_uppercase


# Returns dictionary of {axis name: 0-based index}
# Axis name consists of lowercase english alphabet letters in the following scheme:
# 0: aa, 1: ab, 2: ac, ..., 25: az, 26: aaa, 27: aab, ...
def enumerate_axis_lowercase(number_of_axis: int) -> Dict[str, int]:
    return _enumerate_axis(number_of_axis, 'a', ascii_lowercase)


# 0: AA, 1: AB, 2: AC, ..., 25: AZ, 26: AAA, 27: AAB, ...'
def enumerate_axis_uppercase(number_of_axis: int) -> Dict[str, int]:
    return _enumerate_axis(number_of_axis, 'A', ascii_uppercase)


def _enumerate_axis(number_of_axis: int, prefix: str, letters: str) -> Dict[str, int]:
    output: Dict[str, int] = {}
    while len(output) < number_of_axis:
        for letter in letters:
            output[prefix + letter] = len(output)
            if len(output) == number_of_axis:
                break
        prefix += prefix[0]
    return output
