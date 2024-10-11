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

"""Exceptions for libnagios"""

import logging

# Local imports
from . import types

logging.getLogger(__name__).addHandler(logging.NullHandler())


class NagiosException(Exception):
    """Base exception for libnagios"""

    STATUS = types.Status.UNKNOWN

    def __init__(self, message: str, perfdata: None | dict[str, any] = None):
        self._message = message
        self._perfdata = perfdata
        super().__init__(message)

    @property
    def message(self) -> str:
        """Message property"""
        return self._message

    @property
    def perfdata(self) -> dict[str, any]:
        """Performance data if set"""
        return {} if self._perfdata is None else self._perfdata

    @property
    def status(self) -> types.Status:
        """Nagios Status code"""
        return self.STATUS


class OKError(NagiosException):
    """Short circuit way to generate an OK status"""

    STATUS = types.Status.OK


class WarnError(NagiosException):
    """Short circuit way to generate an WARN status"""

    STATUS = types.Status.WARN


class CriticalError(NagiosException):
    """Short circuit way to generate an CRITICAL status"""

    STATUS = types.Status.WARN


class UnknownError(NagiosException):
    """Raised when an UNKNOWN condition exists"""

    STATUS = types.Status.UNKNOWN
