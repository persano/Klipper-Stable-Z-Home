# Exposes the wall-clock time to macros as printer.wall_clock.epoch
# (Klipper's Jinja has no clock). Needs "[wall_clock]" in printer.cfg.
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import time


class WallClock:
    def get_status(self, eventtime):
        return {'epoch': int(time.time())}


def load_config(config):
    return WallClock()
