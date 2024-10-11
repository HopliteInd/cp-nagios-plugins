#!/usr/bin/env python3
"""UNIT TEST for libnagios"""
import logging
import os
import sys
import unittest

sys.path.insert(0, "..")
import libnagios

TRUE = ("1", "true", "yes", "on")
FALSE = ("0", "false", "no", "off")

MAX = 2**32 - 1
MAXF = float(2**32 - 1)


class TestArgsRange(unittest.TestCase):
    def test_single_utils(self):
        one = libnagios.utils.Range("1")
        self.assertTrue(1 in one)
        self.assertFalse(2 in one)

        ten = libnagios.utils.Range("10")
        self.assertTrue(1 in ten)
        self.assertTrue(2 in ten)
        self.assertTrue(10 in ten)
        self.assertTrue(0 in ten)
        self.assertFalse(-1 in ten)
        self.assertFalse(11 in ten)

    def test_range_both_utils(self):
        t_range = libnagios.utils.Range("@1:10")
        self.assertTrue(1 in t_range)
        self.assertTrue(5 in t_range)
        self.assertTrue(10 in t_range)
        self.assertFalse(0 in t_range)
        self.assertFalse(11 in t_range)

        self.assertTrue(t_range.low == 1)
        self.assertTrue(t_range.high == 10)

    def test_range_high_utils(self):
        t_range = libnagios.utils.Range("@:10")
        self.assertTrue(1 in t_range)
        self.assertTrue(5 in t_range)
        self.assertTrue(10 in t_range)
        self.assertFalse(0 in t_range)
        self.assertFalse(11 in t_range)
        # Default low value is 1 test for it
        self.assertTrue(t_range.low == 1)
        self.assertTrue(t_range.high == 10)

    def test_range_low_utils(self):
        t_range = libnagios.utils.Range("@10:")
        self.assertFalse(1 in t_range)
        self.assertFalse(5 in t_range)
        self.assertTrue(10 in t_range)
        self.assertFalse(0 in t_range)
        self.assertTrue(11 in t_range)
        self.assertTrue(MAX in t_range)
        # Default low value is 1 test for it
        self.assertTrue(t_range.low == 10)
        self.assertTrue(t_range.high == MAX)

    def test_range_no_utils(self):
        t_range = libnagios.utils.Range("@:")
        self.assertTrue(1 in t_range)
        self.assertTrue(5 in t_range)
        self.assertTrue(10 in t_range)
        self.assertFalse(0 in t_range)
        self.assertTrue(11 in t_range)
        self.assertFalse(MAX + 1 in t_range)
        # Default low value is 1 test for it
        self.assertTrue(t_range.low == 1)
        self.assertTrue(t_range.high == MAX)

    def test_range_negative_utils(self):
        t_range = libnagios.utils.Range("@-10:12")
        self.assertTrue(1 in t_range)
        self.assertTrue(5 in t_range)
        self.assertTrue(10 in t_range)
        self.assertTrue(0 in t_range)
        self.assertTrue(-1 in t_range)
        self.assertTrue(-10 in t_range)
        self.assertTrue(12 in t_range)
        self.assertFalse(13 in t_range)
        self.assertFalse(123 in t_range)
        # Default low value is 1 test for it
        self.assertTrue(t_range.low == -10)
        self.assertTrue(t_range.high == 12)

    def test_inverse_utils(self):
        t_range = libnagios.utils.Range("@10:1")
        self.assertFalse(1 in t_range)
        self.assertFalse(5 in t_range)
        self.assertFalse(10 in t_range)
        self.assertTrue(0 in t_range)
        self.assertTrue(11 in t_range)

        self.assertTrue(t_range.low == 1)
        self.assertTrue(t_range.high == 10)

    def test_no_num_utils(self):
        with self.assertRaises(ValueError):
            t_range = libnagios.utils.Range("@a:b")


class TestArgsFRange(unittest.TestCase):
    def test_single_utils(self):
        one = libnagios.utils.FRange("1")
        self.assertTrue(1.0 in one)
        self.assertFalse(2.0 in one)

        one = libnagios.utils.FRange("1.0")
        self.assertTrue(1.0 in one)
        self.assertFalse(2.0 in one)

        ten = libnagios.utils.FRange("10.0")
        self.assertTrue(1.0 in ten)
        self.assertTrue(2.0 in ten)
        self.assertTrue(10.0 in ten)
        self.assertTrue(0.0 in ten)
        self.assertFalse(-1.0 in ten)
        self.assertFalse(11.0 in ten)

    def test_range_both_utils(self):
        t_range = libnagios.utils.FRange("@1:10")
        self.assertTrue(1.0 in t_range)
        self.assertTrue(5.0 in t_range)
        self.assertTrue(10.0 in t_range)
        self.assertFalse(0.0 in t_range)
        self.assertFalse(11.0 in t_range)

        self.assertTrue(t_range.low == 1.0)
        self.assertTrue(t_range.high == 10.0)

    def test_range_high_utils(self):
        t_range = libnagios.utils.FRange("@:10")
        self.assertTrue(1.0 in t_range)
        self.assertTrue(5.0 in t_range)
        self.assertTrue(10.0 in t_range)
        self.assertFalse(0.0 in t_range)
        self.assertFalse(11.0 in t_range)
        # Default low value is 1 test for it
        self.assertTrue(t_range.low == 1.0)
        self.assertTrue(t_range.high == 10.0)

    def test_range_low_utils(self):
        t_range = libnagios.utils.FRange("@10:")
        self.assertFalse(1.0 in t_range)
        self.assertFalse(5.0 in t_range)
        self.assertTrue(10.0 in t_range)
        self.assertFalse(0.0 in t_range)
        self.assertTrue(11.0 in t_range)
        self.assertTrue(MAXF in t_range)
        # Default low value is 1 test for it
        self.assertTrue(t_range.low == 10.0)
        self.assertTrue(t_range.high == MAXF)

    def test_range_no_utils(self):
        t_range = libnagios.utils.FRange("@:")
        self.assertTrue(1.0 in t_range)
        self.assertTrue(5.0 in t_range)
        self.assertTrue(10.0 in t_range)
        self.assertFalse(0.0 in t_range)
        self.assertTrue(11.0 in t_range)
        self.assertFalse(MAXF + 1 in t_range)
        # Default low value is 1 test for it
        self.assertTrue(t_range.low == 1.0)
        self.assertTrue(t_range.high == MAXF)

    def test_range_negative_utils(self):
        t_range = libnagios.utils.FRange("@-10.0:12")
        self.assertTrue(1.0 in t_range)
        self.assertTrue(5.0 in t_range)
        self.assertTrue(10.0 in t_range)
        self.assertTrue(0.0 in t_range)
        self.assertTrue(-1.0 in t_range)
        self.assertTrue(-10.0 in t_range)
        self.assertTrue(12.0 in t_range)
        self.assertFalse(13.0 in t_range)
        self.assertFalse(123.0 in t_range)
        # Default low value is 1 test for it
        self.assertTrue(t_range.low == -10.0)
        self.assertTrue(t_range.high == 12.0)

    def test_inverse_utils(self):
        t_range = libnagios.utils.FRange("@10:1.0")
        self.assertFalse(1.0 in t_range)
        self.assertFalse(5.0 in t_range)
        self.assertFalse(10.0 in t_range)
        self.assertTrue(0.0 in t_range)
        self.assertTrue(11.0 in t_range)

        self.assertTrue(t_range.low == 1)
        self.assertTrue(t_range.high == 10)

    def test_no_num_utils(self):
        with self.assertRaises(ValueError):
            t_range = libnagios.utils.FRange("@a:b")


def setup():
    handlers = []
    # Set up stderr logging
    stderr = logging.StreamHandler(stream=sys.stderr)
    handlers.append(stderr)

    # Set the defaults
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    level = logging.ERROR
    utils = {}

    debug = os.getenv("DEBUG", "false").lower()
    verbose = os.getenv("VERBOSE", "false").lower()
    if debug in TRUE:
        level = logging.DEBUG
    elif verbose in TRUE:
        level = logging.INFO
    else:
        fmt = "%(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, handlers=handlers, **utils)
    log = logging.getLogger()
    log.setLevel(level)


if __name__ == "__main__":
    setup()
    unittest.main()
