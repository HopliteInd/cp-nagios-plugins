# Copyright 2020 Hoplite Industries, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Disk checks."""

import dbm
import json
import os.path
import platform
import sys
import time

# 3rd party
import psutil

from .. import plugin

TEMPLATE = """CPU Usage  {swap_free:,.3f} GB ({swap_free_pct:.2%})
Swap Total: {swap_total:,.3f} GB
Swap Used: {swap_used:,.3f} GB ({swap_used_pct:.2f})
"""


class Check(plugin.Plugin):
    """Nagios plugin to perform CPU checks."""

    def cli(self):
        """Add command line arguments specific to the plugin."""
        # Default config.ini path
        winpath = os.path.join(
            os.path.dirname(os.path.realpath(sys.argv[0])), "check_cp_cpu.db"
        )
        posixpath = os.path.expanduser("~/.check_cp_cpu.db")
        cfgpath = winpath if platform.system() == "Windows" else posixpath

        self.current = psutil.cpu_times()

        self.parser.add_argument(
            "-t",
            "--time-span",
            dest="span",
            type=int,
            default=300,
            help="Time in seconds to do calculations for.  This value should "
            "be some multiple of the frequency of your checks. [Default: "
            "%(default)d]",
        )
        self.parser.add_argument(
            "-s",
            "--state-file",
            dest="state",
            default=cfgpath,
            help="Path to state database [Default: %(default)s]",
        )
        self.parser.add_argument(
            "-w",
            "--warn",
            dest="warn",
            nargs=2,
            action="append",
            metavar="<type> <value>",
            default=[["user", 80.0], ["system", 50.0]],
            help="CPU usage percent to warn at.  The defaults are 80 for "
            "'user' and 50 for 'system'.  Valid states are: %s"
            % ", ".join(self.current._fields),
        )
        self.parser.add_argument(
            "-c",
            "--critical",
            dest="critical",
            nargs=2,
            action="append",
            metavar="<type> <value>",
            default=[["user", 80.0], ["system", 50.0]],
            help="CPU usage percent to go critical at.  The defaults are 90 "
            "for 'user' and 75 for 'system'.  Valid states are: %s"
            % ", ".join(self.current._fields),
        )

    def execute(self):
        """Execute the actual working parts of the plugin."""
        # validate types
        warn = {}
        critical = {}
        current = self.current._asdict()
        for key, value in self.opts.warn:
            if key not in current:
                self.message = (
                    "Invalid CPU state: [%s]. Valid values are [%s]"
                    % (
                        key,
                        ", ".join(current.keys()),
                    )
                )
                self.status = plugin.Status.UNKNOWN
                return
            try:
                warn[key] = float(value)
            except ValueError:
                self.message = "Warn value for %s must be a float" % key
                self.status = plugin.Status.UNKNOWN
                return

        for key, value in self.opts.critical:
            if key not in current:
                self.message = (
                    "Invalid CPU state: [%s]. Valid values are [%s]"
                    % (
                        key,
                        ", ".join(current.keys()),
                    )
                )
                self.status = plugin.Status.UNKNOWN
                return
            try:
                critical[key] = float(value)
            except ValueError:
                self.message = "Warn value for %s must be a float" % key
                self.status = plugin.Status.UNKNOWN
                return

        try:
            db = dbm.open(self.opts.state, "c")
        except Exception as err:
            self.message = "Failed to open state db: %s" % err
            self.status = plugin.Status.UNKNOWN
            return

        now = int(time.time())
        old = now - self.opts.span * 3

        db[str(now)] = json.dumps(self.current._asdict())

        closest = None
        for key in list(db.keys()):
            ts = int(key.decode("utf-8"))

            # Cleanup of old stuff
            if ts < old:
                del db[key]
                continue

            # Ignore current timestamp
            if ts == now:
                continue

            if closest is None:
                closest = ts
                continue

            cl_distance = abs(self.opts.span - (now - closest))

            if abs(self.opts.span - (now - ts)) < cl_distance:
                closest = ts

        if closest is None:
            self.message = "Not enough data points yet.."
            return

        history = json.loads(db[str(closest)])
        db.close()

        start_ticks = sum([history[x] for x in history])
        end_ticks = sum([current[x] for x in current])
        total = end_ticks - start_ticks

        self.message = "ticks: %d" % total

        used = (
            sum(
                [
                    (current[x] - history[x])
                    for x in current
                    if x not in ("idle",)
                ]
            )
            / total
            * 100
        )
        stats = {x: ((current[x] - history[x]) / total) * 100 for x in current}
        output = []

        for key, value in critical.items():
            if stats[key] > value:
                output.append(
                    "CRITICAL: %s CPU is %d%% for the last %d seconds"
                    % (key, stats[key], abs(closest - now))
                )
                self.status = plugin.Status.CRITICAL

        if not output:
            for key, value in warn.items():
                if stats[key] > value:
                    output.append(
                        "WARNING: %s CPU is %d%% for the last %d seconds"
                        % (key, stats[key], abs(closest - now))
                    )
                    self.status = plugin.Status.WARN

        if not output:
            output = ["CPU Usage OK at %0.2f%%" % used]

        for key in sorted(stats.keys()):
            output.append("%s CPU usage: %0.2f%%" % (key, stats[key]))

        self.message = "\n".join(output)
        self.add_perf_multi({"cpu_%s" % x: stats[x] for x in stats})


def run():
    """Entry point from setup.py for installation of wrapper."""
    instance = Check()
    instance.main()


if __name__ == "__main__":
    run()
