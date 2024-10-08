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

import platform
import time

# 3rd party
import psutil

# Local imports
import libnagios

TEMPLATE = """Load {status} :: {msg}
One minute:      {one:.1f}
Five minute:     {five:.1f}
Fifteen minute:  {fifteen:.1f}
"""


class Check(libnagios.plugin.Plugin):
    """Nagios plugin to perform process checks."""

    RANGE_SPEC = True

    def cli(self):
        """Add command line arguments specific to the plugin."""
        warn = [1, 1]
        crit = [1, 1]
        self.parser.add_argument(
            "-w",
            "--warn",
            dest="warn",
            meta="<range>",
            type=libnagios.args.Range,
            default=libnagios.args.Range("1"),
            help="If the number of processes are outside this range then "
            "give a warning.  {} {} for <low> and <high> respecively".format(
                *warn
            ),
        )
        self.parser.add_argument(
            "-c",
            "--critical",
            dest="critical",
            type=int,
            nargs=2,
            default=[1, 1],
            help="Load average to go critical at. [Defaults: {:.1f}, "
            "{:.1f}, {:.1f} for 1, 5, 15 minute average.]".format(*crit),
        )

    def execute(self):
        """Execute the actual working parts of the plugin."""
        try:
            stats = dict(zip(["one", "five", "fifteen"], psutil.getloadavg()))
            if platform.system() == "Windows":
                time.sleep(5.5)
                stats = dict(
                    zip(["one", "five", "fifteen"], psutil.getloadavg())
                )
        except OSError as err:
            self.message = f"Error gathering load average: {err}"
            self.status = libnagios.plugin.Status.UNKNOWN
            return

        self.add_perf_multi({f"loadavg_{x}": stats[x] for x in stats})

        output = {}
        for status, values in (
            (libnagios.plugin.Status.WARN, self.opts.warn),
            (libnagios.plugin.Status.CRITICAL, self.opts.critical),
        ):
            output[status] = []
            one, five, fifteen = values
            if stats["one"] > one:
                self.status = status
                output[status].append("1 min: {stats['one']:.1f} > {one:.1f}")
            if stats["five"] > five:
                self.status = status
                output[status].append(
                    "5 min: {stats['five']:.1f} > {five:.1f}"
                )
            if stats["fifteen"] > fifteen:
                self.status = status
                output[status].append(
                    "15 min: {stats['fifteen']:.1f} > {fifteen:.1f}"
                )

        # pylint: disable=consider-using-f-string
        stats["msg"] = "{one:.1f}, {five:.1f}, {fifteen:.1f}".format(**stats)

        # Order matters.  Highest criticality must be last
        for status in (
            libnagios.plugin.Status.WARN,
            libnagios.plugin.Status.CRITICAL,
        ):
            if output[status]:
                self.status = status
                stats["msg"] = " :: ".join(output[status])

        stats["status"] = self.status.name
        self.message = TEMPLATE.strip().format(**stats)


def run():
    """Entry point from setup.py for installation of wrapper."""
    instance = Check()
    instance.main()


if __name__ == "__main__":
    run()
