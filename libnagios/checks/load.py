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

import psutil

from .. import plugin

class Check(plugin.Plugin):

    def cli(self):
        self.parser.add_argument("-w", "--warn",
            dest="warn",
            type=float,
            nargs=3,
            default=[10, 8, 7],
            help="Load average to warn at",
            )
        self.parser.add_argument("-c", "--critical",
            dest="critical",
            type=float,
            nargs=3,
            default=[12, 10, 9],
            help="Amount of disk free to mark critical [Default: %0.2(default)f]",
            )

    def execute(self):
        try:
            result = psutil.getloadavg()
        except OSError as err:
            self.message = "Error gathering load average: %s" % err
            self.status = plugin.Status.UNKNOWN
            return

        print(opts.warn)
        self.message = "Load average {:.2f} {:.2f} {:.2f}".format(
            result[0],
            result[1],
            result[2],
            )


def run():
    instance = Check()
    instance.main()


if __name__ == "__main__":
    run()
