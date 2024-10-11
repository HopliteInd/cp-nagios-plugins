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

"""Plugin template."""

import argparse
import base64
import io
import json
import logging
import os
import sys
import time
import typing

# 3rd party imports
import rich.markdown
import rich_argparse

# Local imports
from . import exceptions
from . import types

logging.getLogger(__name__).addHandler(logging.NullHandler())


class Plugin:
    """This class is a template for a nagios plugin.

    Attributes:
        parser (argparse.ArgumentParser): To be used in your subclasses as
            to add command line arugments within your :ref:`Plugin.cli` method.
        opts (argparse.Namespace): The options returned from parsing the
            command line arguments.  To be used in your :ref:`Plugin.execute`
            method.

    """

    DESCRIPTION = None
    EPILOG = None

    def __init__(self):
        log = logging.getLogger(f"{__name__}.Plugin")
        log.debug("Initilization")

        # Public variables
        self.parser = None
        self.opts = None

        self._message = None
        self._status = types.Status.OK
        self._perfdata = {}
        self.init()

    def init(self):
        """Meant to be overridden if your module needs additinal setup"""

    @property
    def message(self):
        """(str) Status message to give to Nagios.

        This can be a multi-line output string.  The first line is what
        Nagios will display when looking at the summary.  The details page will
        show the full output.

        .. note::

            This value may not have a pipe (|) character in it.

        """
        return self._message

    @message.setter
    def message(self, value):
        if not isinstance(value, str):
            raise ValueError("'message' must be a 'str'")
        if "|" in value:
            raise ValueError(
                "'message' must not contain the pipe '|' character"
            )
        self._message = value.strip()

    @property
    def status(self):
        """(Status) Status of the plugin run.

        Defaults to :ref:`OK <Status>`
        """
        return self._status

    @status.setter
    def status(self, value):
        if not isinstance(value, types.Status):
            raise ValueError(
                "'status' must be an instance of 'libnagios.types.Status'"
            )
        self._status = value

    def add_perf(self, key: str, value: typing.Union[str, float, int]):
        """Add performance data to the Nagios output.

        Only str, float or int values may be added.

        Parameters:
            key: Key name for the performance data.  There are three keys
                that are reserved and will be overridden by the
                :ref:`Plugin.main` method.

                * ``epoch``: Time in seconds since 00:00:00 Jan 1, 1970 GMT.
                * ``runtime``: Time it took to run the :meth:`Plugin.execute`
                    method from your subclass.
                * ``state``: String value for the state of the plugin run.

            value (str, float, or int): Performance metric value to record.

        """
        log = logging.getLogger(f"{__name__}.Plugin.add_perf")
        log.debug("%s=%s", repr(key), repr(value))
        if not isinstance(key, str):
            raise ValueError("When adding perf data 'key' must be a 'str'")

        if not isinstance(key, (str, float, int)):
            raise ValueError(
                f"For key={repr(key)} 'value' must in ('str', 'float', 'int')"
            )

        self._perfdata[key] = value

    def add_perf_multi(self, data: dict):
        """Add performance data to the Nagios output.

        Add the contents of the dictionary to the perfdata output of your
        plugin.

        Parameters:
            data: Key value pairs added to the perfdata output of the plugin.
                each key/value pair is sent through
                :meth:`libnagios.plugin.Plugin.add_perf` to add the data.

        Raises:
            ValueError: Raised on multiple conditions:

                * Raised when ``data`` is not a ``dict`` instance.
                * Raised when a key in the dictionary is not a ``str``
                * Raised when a value in the dictionary is not one of ``str``,
                  ``float``, ``int``.

        .. note::

            See :meth:`libnagios.plugin.Plugin.add_perf` for details on
            reserved keys.
        """

        log = logging.getLogger(f"{__name__}.Plugin.add_perf_multi")
        log.debug("data is {type(data)}")

        if not isinstance(data, dict):
            raise ValueError(
                "When adding multiple values 'data' must be a 'dict'"
            )

        for key, value in data.items():
            self.add_perf(key, value)

    def finish(self, as_json: bool = False, limit: int = 4096):
        """Print plugin output for Nagios and exit.

        Last method called by :meth:`libnagios.plugin.Plugin.main` to print
        the nagios output (message and perfdata).  Then it exits with the
        appropriate exit status from :meth:`libnagios.plugin.Plugin.status`

        Parameters:
            as_json: If ``True`` print the perfdata as JSON.  If ``False``
                (default) print the perf data as ``key=value`` one line per
                key.
            limit: The amount of output to print.  By defult Nagios will only
                take the first 4k of output, anything after that will be
                discarded.  If you compiled your Nagios to handle more
                than 4k you may adjust ``limit`` to accommodate that.

        """
        log = logging.getLogger(f"{__name__}.Plugin.finish")
        log.debug("(as_json=%s, limit=%s)", repr(as_json), repr(limit))
        output = io.StringIO()

        if self._message:
            output.write(self._message)
        else:
            output.write(f"CRITICAL {__name__}.Plugin.message udefined....")
            self._status = types.Status.CRITICAL
        if self._perfdata:
            output.write("|")

            if as_json:
                output.write(json.dumps(self._perfdata))
            else:
                perfdata = []
                for key, value in self._perfdata.items():
                    perfdata.append(f"{key}={str(value)}")
                output.write("\n".join(perfdata))
        output.seek(0)
        sys.stdout.write(output.read(limit))
        sys.exit(self._status.value)

    def cli(self):
        """Override me.

        Class to be overridden in a subclass to handle command line arguments
        for your plugin.  You may use the
        :attr:`libnagios.plugin.Plugin.parser` variable to add command line
        arguments.

        """
        raise RuntimeError("You must implement Plugin.cli in subclass")

    def execute(self):
        """Override me.

        Class to be overridden in a subclass to do the actual work for your
        plugin.  You may access the command line options via the
        :attr:`libnagios.plugin.Plugin.opts` variable.

        """
        raise RuntimeError("You must implement Plugin.execute in subclass")

    def _parse_args(self):
        random_session = base64.urlsafe_b64encode(os.urandom(9)).decode(
            "utf-8"
        )
        session_id = os.getenv("SESSION_ID", random_session)

        epilog = (
            rich.markdown.Markdown(self.EPILOG, style="argparse.text")
            if self.EPILOG
            else None
        )
        description = (
            rich.markdown.Markdown(self.DESCRIPTION, style="argparse.text")
            if self.DESCRIPTION
            else None
        )
        self.parser = argparse.ArgumentParser(
            formatter_class=rich_argparse.RichHelpFormatter,
            description=description,
            epilog=epilog,
        )

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
        self.parser.add_argument(
            "--json",
            dest="as_json",
            default=False,
            action="store_true",
            help="Output perfdata as json",
        )

        self.cli()
        self.opts = self.parser.parse_args()
        if self.opts.debug_log:
            self.opts.debug = True

    def main(self):
        """Entry point into the class and it's subclasses.

        When using the ``Plugin`` class to create a nagios plugin you will
        need to use this method as the primary entry point.  This class will
        perform the checks and report back the proper status to the calling
        Nagios entity.

        .. note::

            This function exits the program, so make sure no vital code is
            executed after the call to ``main()``.

        """
        self._parse_args()
        handlers = []
        # Set up stderr logging
        stderr = logging.StreamHandler(stream=sys.stderr)
        handlers.append(stderr)

        # Set the defaults
        fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
        level = logging.CRITICAL
        args = {}

        if self.opts.debug:
            level = logging.DEBUG
            if self.opts.debug_log:
                args = {
                    "filename": self.opts.debug_log,
                    "filemode": "a",
                }
        elif self.opts.verbose:
            level = logging.INFO
        else:
            fmt = "%(name)s: %(message)s"
        logging.basicConfig(level=level, format=fmt, handlers=handlers, **args)
        log = logging.getLogger()
        log.setLevel(level)

        start = time.time()
        try:
            self.execute()
        except exceptions.NagiosException as err:
            self.message = err.message
            self.add_perf_multi(err.perfdata)
            self.status = err.status
        runtime = time.time() - start
        self.add_perf("epoch", start)
        self.add_perf("runtime", f"{runtime:.2f}")
        self.add_perf("state", self.status.name)
        self.finish(as_json=self.opts.as_json)
