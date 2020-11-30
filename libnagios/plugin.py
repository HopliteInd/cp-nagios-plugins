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

"""Plugin template"""

import argparse
import base64
import enum
import io
import json
import logging
import os
import sys
import time
import typing


logging.getLogger(__name__).addHandler(logging.NullHandler())


class Status(enum.Enum):
    """Nagios statuses."""

    OK = 0
    WARN = 1
    CRITICAL = 2
    UNKNOWN = 3


class Plugin:
    def __init__(self):
        log = logging.getLogger("%s.Plugin" % __name__)
        log.debug("Initilization")

        # Public variables
        self.parser = None
        self.opts = None

        self._message = None
        self._status = Status.OK
        self._perfdata = {}

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, value):
        if not isinstance(value, str):
            raise ValueError(
                "'message' must be a 'str'" % (__name__)
            )
        if "|" in value:
            raise ValueError(
                "'message' must not contain the pipe '|' character"
                % (__name__)
            )
        self._message = value.strip()

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        if not isinstance(value, Status):
            raise ValueError(
                "'status' must be an instance of '%s.Status'"
                % (__name__, __name__)
            )
        self._status = value

    def add_perf(self, key: str, value: typing.Union[str, float, int]):
        log = logging.getLogger("%s.Plugin.add_perf" % __name__)
        log.debug("%s=%s", repr(key), repr(value))
        if not isinstance(key, str):
            raise ValueError(
                "When adding perf data 'key' must be a 'str'" % (__name__)
            )

        if not (isinstance(key, (str, float, int))):
            raise ValueError(
                "For key=%s 'value' must in ('str', 'float', 'int')"
                % (repr(key), __name__)
            )

        self._perfdata[key] = value

    def add_perf_multi(
        self,
        data: dict,
    ):
        log = logging.getLogger("%s.Plugin.add_perf_multi" % __name__)
        log.debug("data is %s", type(data))

        if not isinstance(data, dict):
            raise ValueError(
                "When adding multiple values 'data' must be a 'dict'"
                % (__name__)
            )

        for key, value in data.items():
            self.add_perf(key, value)

    def finish(self, as_json=False, limit=4096):
        log = logging.getLogger("%s.Plugin.finish" % __name__)
        log.debug("(as_json=%s, limit=%s", repr(as_json), repr(limit))
        output = io.StringIO()

        if self._message:
            output.write(self._message)
        else:
            output.write("CRITICAL %s.Plugin.message udefined...." % __name__)
            self._status = Status.CRITICAL
        if self._perfdata:
            output.write("|")

            if as_json:
                output.write(json.dumps(self._perfdata))
            else:
                perfdata = []
                for key, value in self._perfdata.items():
                    perfdata.append("%s=%s" % (key, str(value)))
                output.write("\n".join(perfdata))
        output.seek(0)
        sys.stdout.write(output.read(limit))
        sys.exit(self._status.value)


    def cli(self):
        raise RuntimeError("You must implement Plugin.cli in subclass")

    def execute(self):
        raise RuntimeError("You must implement Plugin.execute in subclass")

    def _parse_args(self):
        random_session = base64.urlsafe_b64encode(os.urandom(9)).decode("utf-8")
        session_id = os.getenv("SESSION_ID", random_session)

        self.parser = argparse.ArgumentParser()
        self.parser.add_argument(
            "--debug",
            dest="debug",
            default=False,
            action="store_true",
            help="Turn on debug output",
        )
        self.parser.add_argument(
            "--log",
            dest="debug_log",
            default=None,
            help="Specify a file for debug output. Implies --debug",
        )
        self.parser.add_argument(
            "--verbose",
            dest="verbose",
            default=False,
            action="store_true",
            help="Turn on verbose output",
        )
        self.parser.add_argument(
            "--session-id",
            dest="session_id",
            default=session_id,
            help="Specify a session id for logging",
        )

        self.cli()
        self.opts = self.parser.parse_args()
        if self.opts.debug_log:
            self.opts.debug = True

    def main(self):
        self._parse_args()
        start = time.time()
        self.execute()
        end = time.time()
        self.add_perf("epoch", start)
        self.add_perf("runtime", "%0.2f" % (end - start))
        self.finish()
