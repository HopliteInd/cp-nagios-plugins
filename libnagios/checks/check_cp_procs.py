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

import platform
import pwd
import time

# 3rd party
import psutil

# Local imports
import libnagios

TEMPLATE = """Processes {status} :: {prefix}{msg}{postfix}{range}"""


class Check(libnagios.plugin.Plugin):
    """Nagios plugin to perform process checks."""

    RANGE_SPEC = True

    def cli(self):
        """Add command line arguments specific to the plugin."""
        self.parser.add_argument(
            "-w",
            "--warn",
            dest="warn",
            metavar="<range>",
            type=libnagios.args.Range,
            default=libnagios.args.Range("1"),
            help=(
                "Processes outside the range spec flag warning. See range "
                "spec above for details on what this means.  [Default: 1]"
            ),
        )
        self.parser.add_argument(
            "-c",
            "--critical",
            dest="critical",
            metavar="<range>",
            type=libnagios.args.Range,
            default=libnagios.args.Range("1"),
            help=(
                "Processes outside the range spec flag critical. See range "
                "spec above for details on what this means.  [Default: 1]"
            ),
        )
        self.parser.add_argument(
            "-m",
            "--metric",
            choices=("PROCS", "VSZ", "RSS", "CPU", "ELAPSED"),
            default="PROCS",
            dest="metric",
            help=(
                "Choose which metric to do the comparison against: "
                "[Default: %(default)s]"
            ),
        )
        self.parser.add_argument(
            "-C",
            "--command",
            dest="command",
            metavar="<command>",
            default=None,
            help="Only scan for exact matches of <command> (without path).",
        )
        self.parser.add_argument(
            "-u",
            "--user",
            dest="user",
            metavar="<user>",
            default=None,
            help="Only scan processes belonging to user",
        )
        self.parser.add_argument(
            "-r",
            "--rss",
            dest="rss",
            metavar="<rss>",
            default=None,
            help="Only scan for processes with RSS higher than indicated.",
        )

    def process_procs(self, user: str | None, state: dict[str, str]):
        """Process PROCS metrics flavor

        Parameters:
            user: User to filter processes by.  If None don't filter.
            state: state dictionary from the execute function

        """
        # Filter processes based on criteria
        count = 0
        for proc in psutil.process_iter():
            with proc.oneshot():
                if self.opts.command and proc.name() != self.opts.command:
                    continue

                if user and proc.username() != user:
                    continue

                if self.opts.rss is not None and proc.rss() < self.opts.rss:
                    # Skip processes that don't meet the minimum RSS size
                    continue

                # increment various counters
                count += 1
        state["msg"] = f"{count} processes"
        if count not in self.opts.warn:
            self.status = libnagios.types.Status.WARN
            word = "inside" if self.opts.warn.inverse else "outside"
            state["range"] = (
                f" - {word} range {self.opts.warn.low} "
                f"to {self.opts.warn.high}"
            )
        if count not in self.opts.critical:
            self.status = libnagios.types.Status.CRITICAL
            word = "inside" if self.opts.critical.inverse else "outside"
            state["range"] = (
                f" - {word} range {self.opts.critical.low} "
                f"to {self.opts.critical.high}"
            )

    def execute(self):
        """Execute the actual working parts of the plugin."""

        user = None
        if self.opts.user:
            try:
                # Test for user being a uid
                uid = int(self.opts.user)
                user = pwd.getpwuid(uid).pw_name
            except ValueError as err:
                # not a uid.  Must be a user name instead
                try:
                    user = pwd.getpwnam(self.opts.user).pw_name
                except KeyError as err:
                    raise libnagios.exceptions.UnknownError(
                        f"Invalid user [{self.opts.user}]"
                    ) from None
            except KeyError as err:
                raise libnagios.exceptions.UnknownError(
                    f"Invalid uid [{self.opts.user}]"
                ) from None

        # Default values for template
        state = {
            "prefix": (
                f"Command {self.opts.command} has "
                if self.opts.command
                else ""
            ),
            "postfix": f" for user {user}" if user else "",
            "range": "",
            "msg": "OK",
            "status": self.status.name,
        }

        # Start checking stuff
        match self.opts.metric:
            case "PROCS":
                self.process_procs(user, state)
            case _:
                state["msg"] = f"Unhandled metric type {self.opts.metric}"
                self.status = libnagios.types.Status.UNKNOWN

        state["status"] = self.status.name
        self.message = TEMPLATE.strip().format(**state)


def run():
    """Entry point from setup.py for installation of wrapper."""
    instance = Check()
    instance.main()


if __name__ == "__main__":
    run()
