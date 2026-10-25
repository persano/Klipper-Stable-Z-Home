# Repeats homing on the Z axis until the resulting stepper position has
# fully stabilized within tolerance, and optionally runs a specific Gcode
# sequence before each attempt.
#
# Copyright (C) 2021 Matthew Lloyd <github@matthewlloyd.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import logging


class StableZHome:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        gcode_macro = self.printer.load_object(config, 'gcode_macro')
        self.before_homing_gcode = gcode_macro.load_template(config, 'gcode', '')
        # Runs once when homing fails (e.g. TURN_OFF_HEATERS)
        self.failure_gcode = gcode_macro.load_template(
            config, 'failure_gcode', '')
        self.default_max_retries = config.getint("retries", 20, minval=0)
        self.default_retry_tolerance = \
            config.getfloat("retry_tolerance", 1 / 400., above=1/1000.)
        self.default_window = config.getint("window", 4, minval=3)
        # 0 disables the guard
        self.default_max_deviation = config.getfloat(
            "max_deviation", 0., minval=0.)
        self.last_range = None
        self.last_attempts = 0
        # Register STABLE_Z_HOME command
        self.gcode.register_command(
            'STABLE_Z_HOME', self.cmd_STABLE_Z_HOME,
            desc=self.cmd_STABLE_Z_HOME_help)
    def get_status(self, eventtime):
        return {'last_range': self.last_range,
                'attempts': self.last_attempts}
    def _log_result(self, result):
        # One greppable line per run in klippy.log: grep STABLE_Z_HOME
        logging.info("STABLE_Z_HOME %s: attempts=%d last_range=%s",
                     result, self.last_attempts,
                     '-' if self.last_range is None
                     else '%.4f' % self.last_range)

    def _fail(self, msg):
        self._log_result('failed')
        try:
            self.gcode.run_script_from_command(self.failure_gcode.render())
        except Exception:
            logging.exception("Exception running failure_gcode")
        return self.gcode.error(msg)
    cmd_STABLE_Z_HOME_help = (
        "Repeatedly home Z until the Z stepper position stabilizes")
    def cmd_STABLE_Z_HOME(self, gcmd):
        max_retries = gcmd.get_int('RETRIES', self.default_max_retries,
                                   minval=0)
        retry_tolerance = gcmd.get_float('RETRY_TOLERANCE',
                                         self.default_retry_tolerance,
                                         minval=1/1000.)
        window = gcmd.get_int('WINDOW', self.default_window, minval=3)
        max_deviation = gcmd.get_float('MAX_DEVIATION',
                                       self.default_max_deviation, minval=0.)
        self.last_range = None
        self.last_attempts = 0

        toolhead = self.printer.lookup_object('toolhead', None)
        if toolhead is None:
            raise gcmd.error("Printer not ready")
        kin = toolhead.get_kinematics()

        # Check X and Y are homed first.
        curtime = self.printer.get_reactor().monotonic()
        homed_axes = kin.get_status(curtime)['homed_axes']
        if 'x' not in homed_axes or 'y' not in homed_axes:
            raise gcmd.error("Must home X and Y axes first")

        steppers = kin.get_steppers()
        stepper = None
        for s in steppers:
            if s.get_name().startswith('stepper_z'):
                stepper = s
                break
        if stepper is None:
            raise gcmd.error("No Z steppers found")

        self.gcode.respond_info(
            'Stable Z home: %.4f tolerance, window %d, %d max retries\n'
            % (retry_tolerance, window, max_retries))

        mcu_z_readings = []
        retries = 1
        retry_tolerance += 1e-4  # allow for floating point rounding errors
        while retries <= max_retries:
            try:
                self.gcode.run_script_from_command(
                    self.before_homing_gcode.render())
            except Exception as e:
                logging.exception("Exception running pre-home script")
                raise self._fail('Pre-home Gcode failed: %s' % (e,))

            self.gcode.run_script_from_command('G28 Z')

            mcu_position_offset = -stepper.mcu_to_commanded_position(0)
            mcu_pos = stepper.get_commanded_position() + mcu_position_offset
            # Abort before the next attempt drives the nozzle down on a
            # bad (e.g. false) trigger.
            if (max_deviation and mcu_z_readings
                    and abs(mcu_pos - mcu_z_readings[0]) > max_deviation):
                raise self._fail(
                    'Z position %.4f deviates more than %.4f from first '
                    'reading %.4f, aborting'
                    % (mcu_pos, max_deviation, mcu_z_readings[0]))
            mcu_z_readings.append(mcu_pos)
            mcu_z_readings = mcu_z_readings[-window:]
            if len(mcu_z_readings) == window:
                window_range = max(mcu_z_readings) - min(mcu_z_readings)
            else:
                window_range = None

            window_range_str = \
                '%.4f' % (window_range,) if window_range is not None else '-'
            self.gcode.respond_info(
                'Retry %d: %s position %.4f, window range %s\n'
                % (retries, stepper.get_name(), mcu_pos, window_range_str))

            self.last_range = window_range
            self.last_attempts = retries
            if window_range is not None and window_range <= retry_tolerance:
                self.gcode.respond_info('Succeeded\n')
                self._log_result('ok')
                break

            retries += 1

        if retries > max_retries:
            raise self._fail('Max retries exceeded\n')


def load_config(config):
    return StableZHome(config)
