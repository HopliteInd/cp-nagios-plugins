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

"""Tools for manipulating command line arguments"""

import logging
import re

logging.getLogger(__name__).addHandler(logging.NullHandler())


class Range:
    """Class accepts a range specification from the command line

    Parameter:
        range_spec: String indicating the range spec

    RANGEs are prefixed with @ and specified 'min:max' or 'min:' or ':max'
    (or 'max'). If specified 'max:min', a warning status will be generated
    if the count is inside the specified range

    Single values indicate  the upper

    This plugin checks the number of currently running processes and
    generates WARNING or CRITICAL states if the process count is outside
    the specified threshold ranges. The process count can be filtered by
    process owner, parent process PID, current state (e.g., 'Z'), or may
    be the total number of running processes

    """

    RE_RANGE = re.compile(
        "^@"
        "(?P<lval>-?(?:[0-9]+[.])?[0-9]+)?"
        ":"
        "(?P<rval>-?(?:[0-9]+[.])?[0-9]+)?"
        "$"
    )
    RE_SINGLE = re.compile("^[0-9]+$")
    CONV = int
    MIN = 0
    MAX = 2**32 - 1

    def __init__(self, range_spec: str):
        self._range_spec = range_spec
        self._low_bounds = None
        self._high_bounds = None
        self._inverse = False

        log = logging.getLogger(f"{__name__}.{__class__.__name__}")
        log.debug("Range Spec: %r", range_spec)

        found = False
        mobj = self.RE_RANGE.match(range_spec)
        if mobj:  # Range found
            log.debug("Range found")
            self._range_parse(mobj)
            found = True

        if not found:
            if self.RE_SINGLE.match(range_spec):
                log.debug("Single value found")
                self._low_bounds = self.CONV(0)
                self._high_bounds = self.CONV(range_spec)
                found = True

        if not found:
            raise ValueError(f"Invalid range spec detected: {range_spec}")

    def _range_parse(self, mobj: re.Match):
        """Parse ranges"""
        log = logging.getLogger(
            f"{__name__}.{__class__.__name__}._range_parse"
        )
        try:
            lval = mobj.group("lval")
            if lval:
                lval = self.CONV(lval)
            else:
                lval = self.CONV(self.MIN)
        except TypeError as err:
            raise TypeError(
                f"Invalid conversion for left side of range: {err}"
            ) from None
        try:
            rval = mobj.group("rval")
            if rval:
                rval = self.CONV(rval)
            else:
                rval = self.CONV(self.MAX)
        except TypeError as err:
            raise TypeError(
                f"Invalid conversion for right side of range: {err}"
            ) from None

        if lval > rval:  # max:min
            log.debug("Inverse found: lval=%r rval=%r", lval, rval)
            self._inverse = True
            self._low_bounds = rval
            self._high_bounds = lval
        elif lval <= rval:  # min: min:max or :max
            log.debug("Normal bounds found: lval=%r rval=%r", lval, rval)
            self._low_bounds = lval
            self._high_bounds = rval
        else:
            # Never should be hit
            raise ValueError(f"Fatal Error parsing value: {self._range_spec}")

    def __contains__(self, value: int | float):
        """Test to see if value is in the range

        If the inverse flag is set (max:min range given) then this tests to
        see if the value is outside the range

        """

        log = logging.getLogger(
            f"{__name__}.{__class__.__name__}.__contains__"
        )
        log.debug(
            "low=%r high=%r value=%r inverse=%r",
            self._low_bounds,
            self._high_bounds,
            value,
            self._inverse,
        )
        if not isinstance(value, self.CONV):
            raise TypeError("Comparison to invalid type {type(value)}")

        in_it = True
        if value > self._high_bounds:
            in_it = False
        if self._low_bounds > value:
            in_it = False
        if self._inverse:
            in_it = not in_it
        return in_it

    @property
    def spec(self) -> str:
        """Return the original range spec given"""
        return self._range_spec

    @property
    def low(self) -> int:
        """Low bounds"""
        return self._low_bounds

    @property
    def high(self) -> int:
        """High bounds"""
        return self._high_bounds

    @property
    def inverse(self) -> int:
        """Get the status of the inverse flag"""
        return self._inverse


class FRange(Range):
    """Floating point version of Range"""

    RE_RANGE = re.compile(
        "^@"
        "(?P<lval>-?(?:[0-9]+[.])?[0-9]+)?"
        ":"
        "(?P<rval>-?(?:[0-9]+[.])?[0-9]+)?"
        "$"
    )
    RE_SINGLE = re.compile("^(?:[0-9]+[.])?[0-9]+$")
    CONV = float
    MIN = 0.0
    MAX = float(2**32 - 1)

    @property
    def low(self) -> float:
        """Low bounds"""
        return self._low_bounds

    @property
    def high(self) -> float:
        """High bounds"""
        return self._high_bounds


def units(value: int | float) -> str:
    """Convert int or float into a number with kB/GB/TB etc after it"""

    labels = ["kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    label = ""
    valcopy = value
    try:
        while valcopy > 1024:
            valcopy /= 1024
            label = labels.pop(0)
    except IndexError:
        valcopy = value
        label = ""
    return f"{valcopy:0.1f} {label}".strip()


if __name__ == "__main__":
    x = Range("1")
