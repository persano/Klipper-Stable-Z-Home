# Self-check with fakes, no Klipper needed: python test_stable_z_home.py
import stable_z_home as m


class Err(Exception):
    pass


class Stepper:
    def __init__(self, positions):
        self.positions, self.pos = iter(positions), 0.
    def get_name(self): return 'stepper_z'
    def mcu_to_commanded_position(self, p): return 0.
    def get_commanded_position(self): return self.pos


class Gcode:
    error = Err
    def __init__(self, stepper): self.s = stepper
    def register_command(self, *a, **k): pass
    def respond_info(self, msg): pass
    def run_script_from_command(self, script):
        if script == 'G28 Z':
            self.s.pos = next(self.s.positions)


class Cmd:
    error = Err
    def __init__(self, **p): self.p = p
    def get_int(self, k, d, **_): return self.p.get(k, d)
    def get_float(self, k, d, **_): return self.p.get(k, d)


class Tpl:
    def render(self): return ''


def run(positions, **params):
    s = Stepper(positions)
    z = m.StableZHome.__new__(m.StableZHome)
    z.gcode, z.before_homing_gcode = Gcode(s), Tpl()
    z.default_max_retries, z.default_retry_tolerance = 20, 0.0025
    z.default_window, z.default_max_deviation = 4, 0.
    z.last_range = z.last_attempts = None
    kin = type('K', (), {'get_status': lambda self, t: {'homed_axes': 'xy'},
                         'get_steppers': lambda self: [s]})()
    reactor = type('R', (), {'monotonic': lambda self: 0})()
    th = type('T', (), {'get_kinematics': lambda self: kin})()
    z.printer = type('P', (), {
        'lookup_object': lambda self, n, d=None: th,
        'get_reactor': lambda self: reactor})()
    z.cmd_STABLE_Z_HOME(Cmd(**params))
    return z


z = run([1.2, 1.1, 1.0, 1.0, 1.0, 1.0])
assert z.last_attempts == 6 and z.last_range <= 0.0025
try:
    run([1.0, 1.0, 0.2], MAX_DEVIATION=0.3)
    raise SystemExit('guard did not trip')
except Err as e:
    assert 'deviates' in str(e)
print('ok')
