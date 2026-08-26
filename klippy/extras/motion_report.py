# Diagnostic tool for reporting stepper and kinematic positions
#
# Copyright (C) 2021  Kevin O'Connor <kevin@koconnor.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging
import chelper
from . import bulk_sensor
from klippy.variable_axes_count import enumerate_axes_lowercase, getNumberOfAxes

# Extract stepper queue_step messages
class DumpStepper:
    def __init__(self, printer, mcu_stepper):
        self.printer = printer
        self.mcu_stepper = mcu_stepper
        self.last_batch_clock = 0
        self.batch_bulk = bulk_sensor.BatchBulkHelper(printer,
                                                      self._process_batch)
        api_resp = {'header': ('interval', 'count', 'add')}
        self.batch_bulk.add_mux_endpoint("motion_report/dump_stepper", "name",
                                         mcu_stepper.get_name(), api_resp)
    def get_step_queue(self, start_clock, end_clock):
        mcu_stepper = self.mcu_stepper
        res = []
        while 1:
            data, count = mcu_stepper.dump_steps(128, start_clock, end_clock)
            if not count:
                break
            res.append((data, count))
            if count < len(data):
                break
            end_clock = data[count-1].first_clock
        res.reverse()
        return ([d[i] for d, cnt in res for i in range(cnt-1, -1, -1)], res)
    def log_steps(self, data):
        if not data:
            return
        out = []
        out.append("Dumping stepper '%s' (%s) %d queue_step:"
                   % (self.mcu_stepper.get_name(),
                      self.mcu_stepper.get_mcu().get_name(), len(data)))
        for i, s in enumerate(data):
            out.append("queue_step %d: t=%d p=%d i=%d c=%d a=%d"
                       % (i, s.first_clock, s.start_position, s.interval,
                          s.step_count, s.add))
        logging.info('\n'.join(out))
    def _process_batch(self, eventtime):
        data, cdata = self.get_step_queue(self.last_batch_clock, 1<<63)
        if not data:
            return {}
        clock_to_print_time = self.mcu_stepper.get_mcu().clock_to_print_time
        first = data[0]
        first_clock = first.first_clock
        first_time = clock_to_print_time(first_clock)
        self.last_batch_clock = last_clock = data[-1].last_clock
        last_time = clock_to_print_time(last_clock)
        mcu_pos = first.start_position
        start_position = self.mcu_stepper.mcu_to_commanded_position(mcu_pos)
        step_dist = self.mcu_stepper.get_step_dist()
        d = [(s.interval, s.step_count, s.add) for s in data]
        return {"data": d, "start_position": start_position,
                "start_mcu_position": mcu_pos, "step_distance": step_dist,
                "first_clock": first_clock, "first_step_time": first_time,
                "last_clock": last_clock, "last_step_time": last_time}

NEVER_TIME = 9999999999999999.

# Extract trapezoidal motion queue (trapq)
class DumpTrapQ:
    def __init__(self, printer, name, trapq):
        self.printer = printer
        self.name = name
        self.trapq = trapq
        self.last_batch_msg = (0., 0.)
        self.batch_bulk = bulk_sensor.BatchBulkHelper(printer,
                                                      self._process_batch)
        api_resp = {'header': ('time', 'duration', 'start_velocity',
                               'acceleration', 'start_position', 'direction')}
        self.batch_bulk.add_mux_endpoint("motion_report/dump_trapq",
                                         "name", name, api_resp)
    def extract_trapq(self, start_time, end_time):
        ffi_main, ffi_lib = chelper.get_ffi()
        res = []
        while 1:
            data_raw = self._create_pullmove_buffer(ffi_main, ffi_lib,
                                                number_of_entries=128)
            count = ffi_lib.trapq_extract_old(self.trapq,
                                              ffi_main.addressof(data_raw),
                                              data_raw.number_of_entries,
                                              start_time, end_time)
            if not count:
                break
            data = data_raw.entries
            res.append((data, count))
            if count < data_raw.number_of_entries:
                break
            end_time = data[count-1].print_time
        res.reverse()
        return ([d[i] for d, cnt in res for i in range(cnt-1, -1, -1)], res)
    def log_trapq(self, data):
        if not data:
            return
        out = ["Dumping trapq '%s' %d moves:" % (self.name, len(data))]
        axes_names = enumerate_axes_lowercase(getNumberOfAxes()).keys()
        for i, m in enumerate(data):
            out.append("move %d: pt=%.6f mt=%.6f sv=%.6f a=%.6f"
                       " sp=(%s) ar=(%s)"
                       % (i, m.print_time, m.move_t, m.start_v, m.accel,
                          self._print_coord(m.start_pos, axes_names),
                          self._print_coord(m.axis_r, axes_names)))
        logging.info('\n'.join(out))
    def _print_coord(self, coord_struct_ptr, axes_names):
        ffi_main, ffi_lib = chelper.get_ffi()
        iteratable = ffi_main.unpack(coord_struct_ptr.axis, getNumberOfAxes())
        return ",".join(["{}:{:.6f}".format(v,n) for v, n in zip(iteratable, axes_names)])
    def get_trapq_position(self, print_time):
        ffi_main, ffi_lib = chelper.get_ffi()
        data = self._create_pullmove_buffer(ffi_main, ffi_lib, number_of_entries=1)
        count = ffi_lib.trapq_extract_old(self.trapq, ffi_main.addressof(data),
                                          data.number_of_entries, 0.,
                                          print_time)
        if not count:
            return None, None
        move = data.entries[0]
        move_time = max(0., min(move.move_t, print_time - move.print_time))
        dist = (move.start_v + .5 * move.accel * move_time) * move_time

        start_pos = ffi_main.unpack(move.start_pos.axis, getNumberOfAxes())
        axis_r = ffi_main.unpack(move.axis_r.axis, getNumberOfAxes())
        pos = [start * r + dist for start, r in
               zip(start_pos, axis_r)]
        velocity = move.start_v + move.accel * move_time
        return pos, velocity
    def _create_pullmove_buffer(self, ffi_main, ffi_lib,
                                number_of_entries: int):
        return ffi_main.gc(
            ffi_lib.alloc_pull_move_array(number_of_entries, getNumberOfAxes()),
            ffi_lib.free_pull_move_array)

    def _process_batch(self, eventtime):
        qtime = self.last_batch_msg[0] + min(self.last_batch_msg[1], 0.100)
        data, cdata = self.extract_trapq(qtime, NEVER_TIME)
        d = [(m.print_time, m.move_t, m.start_v, m.accel,
              set(m.start_pos.axis), set(m.axis_r.axis))
             for m in data]
        if d and d[0] == self.last_batch_msg:
            d.pop(0)
        if not d:
            return {}
        self.last_batch_msg = d[-1]
        return {"data": d}

STATUS_REFRESH_TIME = 0.250

class PrinterMotionReport:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.steppers = {}
        self.trapqs = {}
        # get_status information
        self.next_status_time = 0.
        gcode = self.printer.lookup_object('gcode')
        self.last_status = {
            'live_position': gcode.Coord(),
            'live_velocity': 0., 'live_extruder_velocity': 0.,
            'steppers': [], 'trapq': [],
        }
        # Register handlers
        self.printer.register_event_handler("klippy:connect", self._connect)
        self.printer.register_event_handler("klippy:shutdown", self._shutdown)
    def register_stepper(self, config, mcu_stepper):
        ds = DumpStepper(self.printer, mcu_stepper)
        self.steppers[mcu_stepper.get_name()] = ds
    def _connect(self):
        # Lookup toolhead trapq
        toolhead = self.printer.lookup_object("toolhead")
        trapq = toolhead.get_trapq()
        self.trapqs['toolhead'] = DumpTrapQ(self.printer, 'toolhead', trapq)
        # Populate 'trapq' and 'steppers' in get_status result
        self.last_status['steppers'] = list(sorted(self.steppers.keys()))
        self.last_status['trapq'] = list(sorted(self.trapqs.keys()))
    # Shutdown handling
    def _dump_shutdown(self, eventtime):
        # Log stepper queue_steps on mcu that started shutdown (if any)
        shutdown_time = NEVER_TIME
        for dstepper in self.steppers.values():
            mcu = dstepper.mcu_stepper.get_mcu()
            sc = mcu.get_shutdown_clock()
            if not sc:
                continue
            shutdown_time = min(shutdown_time, mcu.clock_to_print_time(sc))
            clock_100ms = mcu.seconds_to_clock(0.100)
            start_clock = max(0, sc - clock_100ms)
            end_clock = sc + clock_100ms
            data, cdata = dstepper.get_step_queue(start_clock, end_clock)
            dstepper.log_steps(data)
        if shutdown_time >= NEVER_TIME:
            return
        # Log trapqs around time of shutdown
        for dtrapq in self.trapqs.values():
            data, cdata = dtrapq.extract_trapq(shutdown_time - .100,
                                               shutdown_time + .100)
            dtrapq.log_trapq(data)
        # Log estimated toolhead position at time of shutdown
        dtrapq = self.trapqs.get('toolhead')
        if dtrapq is None:
            return
        pos, velocity = dtrapq.get_trapq_position(shutdown_time)
        if pos is not None:
            logging.info("Requested toolhead position at shutdown time %.6f: %s"
                         , shutdown_time, pos)
    def _shutdown(self):
        self.printer.get_reactor().register_callback(self._dump_shutdown)
    # Status reporting
    def get_status(self, eventtime):
        if eventtime < self.next_status_time or not self.trapqs:
            return self.last_status
        self.next_status_time = eventtime + STATUS_REFRESH_TIME
        toolhead = self.printer.lookup_object('toolhead')
        xyzpos = toolhead.Coord()
        xyzvelocity =  0.
        # Calculate current requested toolhead position
        mcu = self.printer.lookup_object('mcu')
        print_time = mcu.estimated_print_time(eventtime)
        pos, velocity = self.trapqs['toolhead'].get_trapq_position(print_time)
        if pos is not None:
            xyzpos = pos
            xyzvelocity = velocity

        # Report status
        self.last_status = dict(self.last_status)
        self.last_status['live_position'] = toolhead.Coord(*xyzpos)
        self.last_status['live_velocity'] = xyzvelocity
        return self.last_status

def load_config(config):
    return PrinterMotionReport(config)
