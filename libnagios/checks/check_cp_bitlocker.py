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

"""Bitlocker checks."""

import os.path
import subprocess

import libnagios

TEMPLATE = """Disk {disk} :: Bitlocker State: {state}
{stdout}
"""


class Check(libnagios.plugin.Plugin):
    """Nagios plugin to perform Disk checks."""

    def cli(self):
        """Add command line arguments specific to the plugin."""
        self.parser.add_argument(
            "disk",
            help="Directory path for disk to check",
        )

    def execute(self):
        """Execute the actual working parts of the plugin."""
        try:
            cmd = [
                os.path.join(
                    "C:", os.sep, "Windows", "system32", "manage-bde.exe"
                ),
                "-status",
                self.opts.disk,
                "-ProtectionAsErrorLevel",
            ]
            # pylint: disable=subprocess-run-check
            exe = subprocess.run(cmd, capture_output=True)
        except OSError as err:
            self.message = f"Error gathering disk usage: {err}"
            self.status = libnagios.types.Status.UNKNOWN
            return

        # Stats and stuff
        stats = {
            "disk": self.opts.disk,
            "state": "Active" if exe.returncode == 0 else "Inactive",
            "stdout": exe.stdout.decode("utf-8"),
        }

        self.status = libnagios.types.Status.CRITICAL
        if exe.returncode == 0:
            self.status = libnagios.types.Status.OK

        self.message = TEMPLATE.strip().format(**stats)


def run():
    """Entry point from setup.py for installation of wrapper."""
    instance = Check()
    instance.main()


if __name__ == "__main__":
    run()
