#!/usr/bin/env python3
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

# Local imports
import libnagios

TEMPLATE = """CPU Usage  {swap_free:,.3f} GB ({swap_free_pct:.2%})
Swap Total: {swap_total:,.3f} GB
Swap Used: {swap_used:,.3f} GB ({swap_used_pct:.2f})
"""


class ReturnErr(Exception):
    """Exception indicating the error message to return"""

    def __init__(self, message, status):
        super().__init__(message)
        self.message = message
        self.status = status


# pylint: disable=consider-using-generator
class Check(libnagios.plugin.Plugin):
    """Nagios plugin to perform CPU checks."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current = psutil.cpu_times()

    def cli(self):
        """Add command line arguments specific to the plugin."""
        # Default config.ini path
        winpath = os.path.join(
            os.path.dirname(os.path.realpath(sys.argv[0])), "check_cp_cpu.db"
        )
        posixpath = os.path.expanduser("~/.check_cp_cpu.db")
        cfgpath = winpath if platform.system() == "Windows" else posixpath

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
        # pylint: disable=consider-using-f-string
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

    def get_history(self):
        """Get the history and state from the db cache"""
        try:
            statedb = dbm.open(self.opts.state, "c")
        except dbm.error as err:
            raise ReturnErr(
                f"Failed to open state db: {err}",
                libnagios.types.Status.UNKNOWN,
            ) from None

        now = int(time.time())
        old = now - self.opts.span * 3

        statedb[str(now)] = json.dumps(self.current._asdict())

        closest = None
        for key in list(statedb.keys()):
            timestamp = int(key.decode("utf-8"))

            # Cleanup of old stuff
            if timestamp < old:
                del statedb[key]
                continue

            # Ignore current timestamp
            if timestamp == now:
                continue

            if closest is None:
                closest = timestamp
                continue

            cl_distance = abs(self.opts.span - (now - closest))

            if abs(self.opts.span - (now - timestamp)) < cl_distance:
                closest = timestamp

        if closest is None:
            raise ReturnErr(
                "Not enough data points yet..", libnagios.types.Status.UNKNOWN
            ) from None

        history = json.loads(statedb[str(closest)])
        statedb.close()
        return closest, history

    # Yes we know this is a big function.
    # pylint: disable=too-many-locals,too-many-branches
    def execute(self):
        """Execute the actual working parts of the plugin."""
        # validate types
        warn = {}
        critical = {}
        current = self.current._asdict()
        for key, value in self.opts.warn:
            if key not in current:
                # pylint: disable=consider-using-f-string
                self.message = (
                    "Invalid CPU state: [%s]. Valid values are [%s]"
                    % (
                        key,
                        ", ".join(current.keys()),
                    )
                )
                self.status = libnagios.types.Status.UNKNOWN
                return
            try:
                warn[key] = float(value)
            except ValueError:
                self.message = f"Warn value for {key} must be a float"
                self.status = libnagios.types.Status.UNKNOWN
                return

        for key, value in self.opts.critical:
            if key not in current:
                self.message = (
                    # pylint: disable=consider-using-f-string
                    "Invalid CPU state: [%s]. Valid values are [%s]"
                    % (
                        key,
                        ", ".join(current.keys()),
                    )
                )
                self.status = libnagios.types.Status.UNKNOWN
                return
            try:
                critical[key] = float(value)
            except ValueError:
                self.message = f"Warn value for {key} must be a float"
                self.status = libnagios.types.Status.UNKNOWN
                return

        now = time.time()
        try:
            closest, history = self.get_history()
        except ReturnErr as err:
            self.message = err.message
            self.status = err.status
            return

        start_ticks = sum([history[x] for x in history])
        end_ticks = sum([current[x] for x in current])
        total = end_ticks - start_ticks

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

        self.message = f"ticks: {total}"

        stats = {x: ((current[x] - history[x]) / total) * 100 for x in current}
        output = []

        for key, value in critical.items():
            if stats[key] > value:
                seconds = abs(closest - now)
                output.append(
                    f"CRITICAL: {key} CPU is {stats[key]}% for the last "
                    f"{seconds} seconds"
                )
                self.status = libnagios.types.Status.CRITICAL

        if not output:
            for key, value in warn.items():
                if stats[key] > value:
                    output.append(
                        f"WARNING: {key} CPU is {stats[key]}% for the last "
                        f"{seconds} seconds"
                    )
                    self.status = libnagios.types.Status.WARN

        if not output:
            output = [f"CPU Usage OK at {used:.2f}%"]

        for key in sorted(stats.keys()):
            output.append(f"{key} CPU usage: {stats[key]:.2f}%")

        self.message = "\n".join(output)
        self.add_perf_multi({f"cpu_{x}": stats[x] for x in stats})


def run():
    """Entry point from setup.py for installation of wrapper."""
    instance = Check()
    instance.main()


if __name__ == "__main__":
    run()
