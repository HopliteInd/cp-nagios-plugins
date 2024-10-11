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

import pwd

# 3rd party
import psutil

# Local imports
import libnagios

TEMPLATE = """Processes {check} {status} :: {prefix}{msg}{postfix}{range}"""


class Check(libnagios.plugin.Plugin):
    """Nagios plugin to perform process checks."""

    EPILOG = libnagios.doc.RANGE_DOC

    def init(self):
        """Initialize things that are needed in this module"""
        # pylint: disable=attribute-defined-outside-init
        self._user_set = False
        self._user = None

    def cli(self):
        """Add command line arguments specific to the plugin."""
        self.parser.add_argument(
            "-w",
            "--warn",
            dest="warn",
            metavar="<range>",
            type=libnagios.utils.Range,
            default=libnagios.utils.Range("1"),
            help=(
                "Processes outside the range spec flag warning. See range "
                "spec below for details on what this means.  [Default: 1]"
            ),
        )
        self.parser.add_argument(
            "-c",
            "--critical",
            dest="critical",
            metavar="<range>",
            type=libnagios.utils.Range,
            default=libnagios.utils.Range("1"),
            help=(
                "Processes outside the range spec flag critical. See range "
                "spec below for details on what this means.  [Default: 1]"
            ),
        )
        self.parser.add_argument(
            "-m",
            "--metric",
            choices=("PROCS", "VSZ", "RSS"),
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
            type=int,
            default=None,
            help="Only scan for processes with RSS higher than indicated.",
        )
        self.parser.add_argument(
            "-z",
            "--vsz",
            dest="vsz",
            metavar="<vsz>",
            type=int,
            default=None,
            help="Only scan for processes with VSZ higher than indicated.",
        )

    def skip_proc(self, proc: psutil.Process) -> bool:
        """Apply base filters to processes

        Returns:
            True if the process should be skiped due to common rules being
            triggered.  False if the process should not be filtered out.

        """
        skip = False
        if not skip and self.opts.command and proc.name() != self.opts.command:
            skip = True

        if not skip and self.user and proc.username() != self.user:
            skip = True

        if not skip:
            meminfo = proc.memory_info()

            if (
                not skip
                and self.opts.rss is not None
                and meminfo.rss < self.opts.rss
            ):
                # Skip processes that don't meet the minimum RSS size
                skip = True

            if (
                not skip
                and self.opts.vsz is not None
                and meminfo.vms < self.opts.vsz
            ):
                # Skip processes that don't meet the minimum VSZ size
                skip = True
        return skip

    def process_procs(self, state: dict[str, str]):
        """Process PROCS metrics flavor

        Parameters:
            state: state dictionary from the execute function

        """
        # Filter processes based on criteria
        count = 0
        for proc in psutil.process_iter():
            with proc.oneshot():
                if self.skip_proc(proc):
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

    def process_vsz_rss(self, flavor: str, state: dict[str, str]):
        """Process VSZ and RSS metrics flavor

        Parameters:
            flavor: Either string 'vsz' or 'rss'
            state: state dictionary from the execute function

        """
        # Filter processes based on criteria
        errors = []
        for proc in psutil.process_iter():
            with proc.oneshot():
                if self.skip_proc(proc):
                    continue

                # increment various counters
                meminfo = proc.memory_info()
                match flavor:
                    case "vsz":
                        value = getattr(meminfo, "vms")
                    case "rss":
                        value = getattr(meminfo, "rss")
                    case _:
                        raise ValueError(
                            f"flavor must be either vsz or rss not {flavor}"
                        )
                comps = [
                    (libnagios.types.Status.CRITICAL, self.opts.critical),
                    (libnagios.types.Status.WARN, self.opts.warn),
                ]

                for status, comp_range in comps:
                    if value not in comp_range:
                        self.status = (
                            status if self.status < status else self.status
                        )
                        word = "inside" if comp_range.inverse else "outside"
                        value_str = libnagios.utils.units(value)
                        low_str = libnagios.utils.units(comp_range.low)
                        high_str = libnagios.utils.units(comp_range.high)
                        errors.append(
                            f" {status.name} pid[{proc.pid}] {proc.name()} "
                            f"[{value_str}] {word} range {low_str} to "
                            f"{high_str}"
                        )
                        break
        state["range"] = "\n".join(errors)
        state["msg"] = f"{len(errors)} processes"

    @property
    def user(self):
        """Uset attribute for the purposes of filtering.  None is no filter"""
        # pylint: disable=attribute-defined-outside-init
        if not self._user_set:
            if self.opts.user:
                try:
                    # Test for user being a uid
                    uid = int(self.opts.user)
                    self._user = pwd.getpwuid(uid).pw_name
                except ValueError:
                    # not a uid.  Must be a user name instead
                    try:
                        self._user = pwd.getpwnam(self.opts.user).pw_name
                    except KeyError:
                        raise libnagios.exceptions.UnknownError(
                            f"Invalid user [{self.opts.user}]"
                        ) from None
                except KeyError:
                    raise libnagios.exceptions.UnknownError(
                        f"Invalid uid [{self.opts.user}]"
                    ) from None
            else:
                self._user = None
            self._user_set = True
        return self._user

    def execute(self):
        """Execute the actual working parts of the plugin."""

        # Default values for template
        state = {
            "prefix": (
                f"Command {self.opts.command} has "
                if self.opts.command
                else ""
            ),
            "postfix": f" for user {self.user}" if self.user else "",
            "range": "",
            "msg": "OK",
            "status": self.status.name,
        }

        # Start checking stuff
        match self.opts.metric:
            case "PROCS":
                self.process_procs(state)
            case "VSZ":
                self.process_vsz_rss("vsz", state)
            case "RSS":
                self.process_vsz_rss("rss", state)
            case _:
                state["msg"] = f"Unhandled metric type {self.opts.metric}"
                self.status = libnagios.types.Status.UNKNOWN

        state["status"] = self.status.name
        state["check"] = self.opts.metric
        self.message = TEMPLATE.strip().format(**state)


def run():
    """Entry point from setup.py for installation of wrapper."""
    instance = Check()
    instance.main()


if __name__ == "__main__":
    run()
