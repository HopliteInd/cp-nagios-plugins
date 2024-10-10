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


class TestArgs(unittest.TestCase):
    def test_single_args(self):
        one = libnagios.args.Range("1")
        self.assertTrue(1 in one)
        self.assertFalse(2 in one)

        ten = libnagios.args.Range("10")
        self.assertTrue(1 in ten)
        self.assertTrue(2 in ten)
        self.assertTrue(10 in ten)
        self.assertTrue(0 in ten)
        self.assertFalse(-1 in ten)
        self.assertFalse(11 in ten)

    def test_range_args(self):
        on2ten = libnagios.args.Range("@1:10")
        self.assertTrue(1 in on2ten)
        self.assertTrue(5 in on2ten)
        self.assertTrue(10 in on2ten)
        self.assertFalse(0 in on2ten)
        self.assertFalse(11 in on2ten)

        self.assertTrue(on2ten.low == 1)
        self.assertTrue(on2ten.high == 10)

        toTen = libnagios.args.Range("@:10")
        self.assertTrue(1 in toTen)
        self.assertTrue(5 in toTen)
        self.assertTrue(10 in toTen)
        self.assertFalse(0 in toTen)
        self.assertFalse(11 in toTen)
        # Default low value is 1 test for it
        self.assertTrue(toTen.low == 1)
        self.assertTrue(toTen.high == 10)

        toInfinity = libnagios.args.Range("@10:")
        self.assertFalse(1 in toInfinity)
        self.assertFalse(5 in toInfinity)
        self.assertTrue(10 in toInfinity)
        self.assertFalse(0 in toInfinity)
        self.assertTrue(11 in toInfinity)
        self.assertTrue(MAX in toInfinity)
        # Default low value is 1 test for it
        self.assertTrue(toInfinity.low == 10)
        self.assertTrue(toInfinity.high == MAX)

        nospec = libnagios.args.Range("@:")
        self.assertTrue(1 in nospec)
        self.assertTrue(5 in nospec)
        self.assertTrue(10 in nospec)
        self.assertFalse(0 in nospec)
        self.assertTrue(11 in nospec)
        self.assertFalse(MAX + 1 in nospec)
        # Default low value is 1 test for it
        self.assertTrue(toInfinity.low == 1)
        self.assertTrue(toInfinity.high == MAX)

    def test_inverse_args(self):
        on2ten = libnagios.args.Range("@10:1")
        self.assertFalse(1 in on2ten)
        self.assertFalse(5 in on2ten)
        self.assertFalse(10 in on2ten)
        self.assertTrue(0 in on2ten)
        self.assertTrue(11 in on2ten)

        self.assertTrue(on2ten.low == 1)
        self.assertTrue(on2ten.high == 10)


def setup():
    handlers = []
    # Set up stderr logging
    stderr = logging.StreamHandler(stream=sys.stderr)
    handlers.append(stderr)

    # Set the defaults
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    level = logging.ERROR
    args = {}

    debug = os.getenv("DEBUG", "false").lower()
    verbose = os.getenv("VERBOSE", "false").lower()
    if debug in TRUE:
        level = logging.DEBUG
    elif verbose in TRUE:
        level = logging.INFO
    else:
        fmt = "%(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, handlers=handlers, **args)
    log = logging.getLogger()
    log.setLevel(level)


if __name__ == "__main__":
    setup()
    unittest.main()
