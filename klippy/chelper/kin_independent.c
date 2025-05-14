// Independent kinematics stepper pulse time generation
//
// Copyright (C) 2024 Michael Albrecht <micha.albrecht95@gmail.com>
//
// This file may be distributed under the terms of the GNU GPLv3 license.
#include <stdlib.h> // malloc
#include <string.h> // memset
#include "compiler.h" // __visible
#include "itersolve.h"
#include "trapq.h"

static double
ind_stepper_calc_position(struct stepper_kinematics *sk, struct move *m
        , double move_time)
{
    return move_get_coord_of_axis(m, move_time, sk->active_axis_index);
}

struct stepper_kinematics * __visible
independent_stepper_alloc(size_t axis_index)
{
    struct stepper_kinematics *sk = malloc(sizeof(*sk));
    memset(sk, 0, sizeof(*sk));
    sk->active_axis_index = axis_index;
    sk->calc_position_cb = ind_stepper_calc_position;
    return sk;
}