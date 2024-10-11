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

import shutil

# Local imports
import libnagios

TEMPLATE = """Disk {disk} :: Free: {disk_free:,.3f} GB ({disk_free_pct:.2f})
Disk Total: {disk_total:,.3f} GB
Disk Used: {disk_used:,.3f} GB ({disk_used_pct:.2f})
"""


class Check(libnagios.plugin.Plugin):
    """Nagios plugin to perform Disk checks."""

    def cli(self):
        """Add command line arguments specific to the plugin."""
        group = self.parser.add_mutually_exclusive_group()
        group.add_argument(
            "-p",
            "--percent",
            dest="percent",
            action="store_true",
            default=False,
            help="Warning/Critical values are a percentage (default)",
        )
        group.add_argument(
            "-m",
            "--mega-bytes",
            dest="mb",
            action="store_true",
            default=False,
            help="Warning/Critical values are in Mega-Bytes",
        )
        group.add_argument(
            "-g",
            "--giga-bytes",
            dest="gb",
            action="store_true",
            default=False,
            help="Warning/Critical values are in Giga-Bytes",
        )
        self.parser.add_argument(
            "-w",
            "--warn",
            dest="warn",
            type=float,
            default=20.0,
            help="Amount of disk free to warn at",
        )
        self.parser.add_argument(
            "-c",
            "--critical",
            dest="critical",
            type=float,
            default=10.0,
            help="Amount of disk free to mark critical "
            "[Default: %0.2(default)f]",
        )
        self.parser.add_argument(
            "disk",
            help="Directory path for disk to check",
        )

    def execute(self):
        """Execute the actual working parts of the plugin."""
        try:
            result = shutil.disk_usage(self.opts.disk)
        except OSError as err:
            self.message = f"Error gathering disk usage: {err}"
            self.status = libnagios.types.Status.UNKNOWN
            return

        # Stats and stuff
        stats = {
            "disk": self.opts.disk,
            "disk_total": result.total / (1024 * 1024 * 1024),
            "disk_used": result.used / (1024 * 1024 * 1024),
            "disk_free": result.free / (1024 * 1024 * 1024),
            "disk_free_pct": (result.free / result.total) * 100.0,
            "disk_used_pct": (result.used / result.total) * 100.0,
        }

        if self.opts.mb or self.opts.gb:
            divisor = 1024 * 1024 if self.opts.mb else 1024 * 1024 * 1024
            free = result.free / divisor
        else:
            # Fallback to percentage
            free = (result.free / result.total) * 100.0

        if free < self.opts.critical:
            self.status = libnagios.types.Status.CRITICAL
        elif free < self.opts.warn:
            self.status = libnagios.types.Status.WARN
        else:
            self.status = libnagios.types.Status.OK

        self.message = TEMPLATE.strip().format(**stats)
        self.add_perf_multi(stats)


def run():
    """Entry point from setup.py for installation of wrapper."""
    instance = Check()
    instance.main()


if __name__ == "__main__":
    run()
