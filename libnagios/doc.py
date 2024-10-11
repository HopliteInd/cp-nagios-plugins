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

"""Documentation types used by libnagios

The docs here are meant to be formatted with a markdown formatter.
"""

# Documentation for ranges specified on the cli
RANGE_DOC = """
# RANGES

Ranges are specified in two ways.  First is via a single value which
represents the upper bounds of a range that starts at 0.  The second
is where you can specify the upper and lower bounds of the range in
one argument.

RANGEs are prefixed with @ and specified **@min:max**, **@min:** or
**@:max**.  If specified **max:min**, then you are testing for things
outside of the specified range.

Examples:

* **@10:30**    Tests for membership in range 10 - 30 inclusive.
* **@10:**      Tests for membership in range 10 - 2^32-1 inclusive.
* **@:30**      Tests for membership in range 0 - 30 inclusive.
* **@30:10**    Tests for membership outside the range 10 - 30 (9 and
    below or 31 and above)
"""
