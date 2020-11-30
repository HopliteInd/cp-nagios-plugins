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

from .. import plugin

class Check(plugin.Plugin):

    def cli(self):
        group = self.parser.add_mutually_exclusive_group()
        group.add_argument("-p", "--percent",
            dest="percent",
            action="store_true",
            default=False,
            help="Warning/Critical values are a percentage (default)"
            )
        group.add_argument("-m", "--mega-bytes",
            dest="mb",
            action="store_true",
            default=False,
            help="Warning/Critical values are in Mega-Bytes"
            )
        group.add_argument("-g", "--giga-bytes",
            dest="gb",
            action="store_true",
            default=False,
            help="Warning/Critical values are in Giga-Bytes"
            )
        self.parser.add_argument("-w", "--warn",
            dest="warn",
            type=float,
            default=20.0,
            help="Amount of disk free to warn at",
            )
        self.parser.add_argument("-c", "--critical",
            dest="critical",
            type=float,
            default=10.0,
            help="Amount of disk free to mark critical [Default: %0.2(default)f]",
            )
        self.parser.add_argument("disk",
            help="Directory path for disk to check",
            )

    def execute(self):
        try:
            result = shutil.disk_usage(self.opts.disk)
        except OSError as err:
            self.message = "Error gathering disk usage: %s" % err
            self.status = plugin.Status.UNKNOWN
            return

        if self.opts.mb or self.opts.gb:
            divisor = 1024 * 1024 if self.opts.mb else 1024 * 1024 * 1024
            free = result.free / divisor
        else:
            # Fallback to percentage
            free = result.free / result.total

        if free < self.opts.critical:
            self.status = plugin.Status.CRITICAL
        elif free < self.opts.warn:
            self.status = plugin.Status.WARN
        else:
            self.status = plugin.Status.OK

        self.message = "Disk space for {:}: {:,.3f}GB Free ({:.2%})".format(
            self.opts.disk,
            result.free / (1024 * 1024 * 1024),
            result.free / result.total
            )


def run():
    instance = Check()
    instance.main()

