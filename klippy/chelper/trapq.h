#pragma once
#ifdef __cplusplus
extern "C" {
#endif

#include "list.h" // list_node

struct coord {
    double * axis;
};

struct move {
    double print_time, move_t;
    double start_v, half_accel;
    struct coord start_pos;
    struct coord axis_r;

    struct list_node node;
};

struct trapq {
    struct list_head moves, history;
    size_t number_of_axis;
};

struct pull_move {
    double print_time, move_t;
    double start_v, accel;
    struct coord start_pos;
    struct coord axis_r;
};

struct move *move_alloc(size_t number_of_axis);
double move_get_distance(struct move *m, double move_time);
void move_get_coord(struct move *m, double move_time, size_t number_of_axis,
                    double * c_dest);
double move_get_coord_of_axis(struct move *m, double move_time, size_t axis_index);

struct trapq *trapq_alloc(size_t number_of_axis);
void trapq_free(struct trapq *tq);
void trapq_check_sentinels(struct trapq *tq);
void trapq_add_move(struct trapq *tq, struct move *m);
void trapq_append(struct trapq *tq, double print_time
                  , double accel_t, double cruise_t, double decel_t
                  , double start_pos[], double axes_r[]
                  , double start_v, double cruise_v, double accel);
void trapq_finalize_moves(struct trapq *tq, double print_time
                          , double clear_history_time);
void trapq_set_position(struct trapq *tq, double print_time
                        , double const pos[]);

struct pull_move * alloc_pull_move(size_t number_of_axis);
void free_pull_move(struct pull_move *p);

int trapq_extract_old(struct trapq *tq, struct pull_move *p, int max
                      , double start_time, double end_time);

struct coord coord_alloc(size_t number_of_axis);
void coord_free(struct coord *);

#ifdef __cplusplus
}
#endif
