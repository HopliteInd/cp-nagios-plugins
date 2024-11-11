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

import logging
import platform
import time

# 3rd party
import psutil

# Local imports
import libnagios

logging.getLogger(__name__).addHandler(logging.NullHandler())

TEMPLATE = """Load {status} :: {msg}
One minute:      {one:.1f}
Five minute:     {five:.1f}
Fifteen minute:  {fifteen:.1f}
"""


class ScaledLoadTriple:
    """Take an argument as either a single number or a series of 3 numbers"""

    def __init__(self, value: str):
        log = logging.getLogger(f"{__name__}.{__class__.__name__}")
        self._one = -1
        self._five = -1
        self._fifteen = -1

        self._cores = psutil.cpu_count(logical=True)

        tmp = value.split(",")
        if len(tmp) == 1:
            # Single integer
            try:
                single = float(int(tmp[0]))
                if single <= 0:
                    raise ValueError("Value must be > 0")

                one = single
                five = single
                fifteen = single
            except ValueError as err:
                raise libnagios.exceptions.UnknownError(
                    f"Invalid integer value: {err}"
                ) from None
        else:
            # Parsed triple
            one = float(int(tmp[0]))
            five = float(int(tmp[1]))
            fifteen = float(int(tmp[2]))
            if one <= 0:
                raise ("One minute value must be > 0")
            if five <= 0:
                raise ("Five minute value must be > 0")
            if fifteen <= 0:
                raise ("Fifteen minute value must be > 0")

        # Calcualte load averages as a function of the core counts
        self._one = (one / 100.0) * self._cores
        self._five = (five / 100.0) * self._cores
        self._fifteen = (fifteen / 100.0) * self._cores

        log.debug(
            "Warn levels: %0.1f %0.1f %0.1f",
            self._one,
            self._five,
            self._fifteen,
        )
        log.debug(
            "Critical levels: %0.1f %0.1f %0.1f",
            self._one,
            self._five,
            self._fifteen,
        )

    def __iter__(self):
        yield self._one
        yield self._five
        yield self._fifteen

    def __getitem__(self, offset):
        match offset:
            case 0:
                retval = self._one
            case 1:
                retval = self._five
            case 2:
                retval = self._fifteen
            case _:
                raise IndexError("list index out of range")
        return retval

    def __len__(self):
        return 3

    @property
    def one(self) -> float:
        """One minute load average"""
        return self._one

    @property
    def five(self) -> float:
        """Five minute load average"""
        return self._five

    @property
    def fifteen(self) -> float:
        """Fifteen minute load average"""
        return self._fifteen


class Check(libnagios.plugin.Plugin):
    """Nagios plugin to perform Load checks."""

    def cli(self):
        """Add command line arguments specific to the plugin."""

        w_group = self.parser.add_mutually_exclusive_group()
        c_group = self.parser.add_mutually_exclusive_group()
        warn = [12, 10, 8]
        crit = [15, 12, 10]
        w_group.add_argument(
            "-w",
            "--warn",
            dest="warn",
            type=float,
            nargs=3,
            default=warn,
            help="Load average to warn at. [Defaults: {:.1f}, "
            "{:.1f}, {:.1f} for 1, 5, 15 minute average.]".format(*warn),
        )
        w_group.add_argument(
            "-W",
            "--warn-scaled",
            dest="warn",
            type=ScaledLoadTriple,
            default=None,
            help=(
                "Scale load average checks based on a percentage of the "
                "number of CPU cores in the system. You may give either a "
                "single number or three comma separated numbers for 1, 5 "
                "and 15 minute averages."
            ),
        )
        c_group.add_argument(
            "-c",
            "--critical",
            dest="critical",
            type=float,
            nargs=3,
            default=crit,
            help="Load average to go critical at. [Defaults: {:.1f}, "
            "{:.1f}, {:.1f} for 1, 5, 15 minute average.]".format(*crit),
        )
        c_group.add_argument(
            "-C",
            "--critical-scaled",
            dest="critical",
            type=ScaledLoadTriple,
            default=None,
            help=(
                "Scale load average checks based on a percentage of the "
                "number of CPU cores in the system. You may give either a "
                "single number or three comma separated numbers for 1, 5 "
                "and 15 minute averages."
            ),
        )

    def execute(self):
        """Execute the actual working parts of the plugin."""
        log = logging.getLogger(f"{__name__}.{__class__.__name__}.execute")
        try:
            stats = dict(zip(["one", "five", "fifteen"], psutil.getloadavg()))
            if platform.system() == "Windows":
                time.sleep(5.5)
                stats = dict(
                    zip(["one", "five", "fifteen"], psutil.getloadavg())
                )
        except OSError as err:
            self.message = f"Error gathering load average: {err}"
            self.status = libnagios.types.Status.UNKNOWN
            return

        self.add_perf_multi({f"loadavg_{x}": stats[x] for x in stats})

        output = {}
        for status, values in (
            (libnagios.types.Status.WARN, self.opts.warn),
            (libnagios.types.Status.CRITICAL, self.opts.critical),
        ):
            log.debug("one:%0.1f five:%0.1f fifteen:%0.1f", *list(values))
            output[status] = []
            one, five, fifteen = values
            if stats["one"] > one:
                self.status = status
                output[status].append(f"1 min: {stats['one']:.1f} > {one:.1f}")
            if stats["five"] > five:
                self.status = status
                output[status].append(
                    f"5 min: {stats['five']:.1f} > {five:.1f}"
                )
            if stats["fifteen"] > fifteen:
                self.status = status
                output[status].append(
                    f"15 min: {stats['fifteen']:.1f} > {fifteen:.1f}"
                )

        # pylint: disable=consider-using-f-string
        stats["msg"] = "{one:.1f}, {five:.1f}, {fifteen:.1f}".format(**stats)

        # Order matters.  Highest criticality must be last
        for status in (
            libnagios.types.Status.WARN,
            libnagios.types.Status.CRITICAL,
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
