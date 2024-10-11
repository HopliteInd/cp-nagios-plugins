#!/usr/bin/env python3
# Copyright 2022 Hoplite Industries, Inc.
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

"""SSH network check."""

import socket
import time

# 3rd party imports
import paramiko

# local imports
import libnagios

TEMPLATE = """{bit} bit {type} ssh2 connection established
Fingerprint: {fingerprint}
Public Key: {pubkey}
In {elapsed} seconds.
"""


class Check(libnagios.plugin.Plugin):
    """Nagios plugin to perform SSH connectivity check."""

    def cli(self):
        """Add command line arguments specific to the plugin."""
        self.parser.set_defaults(afinet=0)
        group = self.parser.add_mutually_exclusive_group()
        group.add_argument(
            "-4",
            "--ipv4",
            dest="afinet",
            action="store_const",
            const=socket.AF_INET,
            help="Only do IPv4",
        )
        group.add_argument(
            "-6",
            "--ipv6",
            dest="afinet",
            action="store_const",
            const=socket.AF_INET6,
            help="Only do IPv6",
        )
        self.parser.add_argument(
            "-p",
            "--port",
            dest="port",
            default=22,
            type=int,
            help="SSH port [Default: %(default)d]",
        )
        self.parser.add_argument(
            "-H",
            "--host",
            dest="host",
            default="localhost",
            help="SSH Host [Default: %(default)s]",
        )
        self.parser.add_argument(
            "-w",
            "--warn",
            dest="warn",
            type=float,
            default=5.0,
            help="Go warning after X seconds [Default: %(default)0.2f]",
        )
        self.parser.add_argument(
            "-c",
            "--critical",
            dest="critical",
            type=float,
            default=10.0,
            help="Go critical after X seconds [Default: %(default)0.2f]",
        )

    def execute(self):
        """Execute the actual working parts of the plugin."""

        try:
            possible = socket.getaddrinfo(
                self.opts.host,
                self.opts.port,
                family=self.opts.afinet,
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as err:
            self.message = f"{self.opts.host}:{self.opts.port} {str(err)}"
            self.status = libnagios.types.Status.CRITICAL
            return

        for family, sock_type, proto, _, sockaddr in possible:
            start = time.time()
            sock = socket.socket(family=family, type=sock_type, proto=proto)
            sock.settimeout(self.opts.critical)
            try:
                self.status = libnagios.types.Status.OK
                sock.connect(sockaddr)
                conn = paramiko.transport.Transport(sock)
                conn.start_client(timeout=self.opts.critical)
                if not conn.is_active():
                    self.message = "SSH session inactive error"
                    self.status = libnagios.types.Status.CRITICAL

                key = conn.get_remote_server_key()
                conn.close()

                elapsed = round(time.time() - start, 3)

                self.message = TEMPLATE.format(
                    bit=key.get_bits(),
                    type=key.get_name(),
                    fingerprint=key.get_fingerprint().hex(),
                    elapsed=elapsed,
                    pubkey=key.get_base64(),
                )

                # Check thresholds for timeouts
                if elapsed > self.opts.warn:
                    self.message = f"Timeout after {elapsed:.2f} seconds"
                    self.status = libnagios.types.Status.WARN
                if elapsed > self.opts.critical:
                    self.message = f"Timeout after {elapsed:.2f} seconds"
                    self.status = libnagios.types.Status.CRITICAL
            except paramiko.ssh_exception.SSHException as err:
                self.message = f"Error: {str(err)}"
                self.status = libnagios.types.Status.CRITICAL
            except socket.timeout:
                self.message = f"Timeout after {elapsed:.2f} seconds"
                self.status = libnagios.types.Status.CRITICAL
            except socket.gaierror as err:
                self.message = f"Socket error: {err}"
                self.status = libnagios.types.Status.CRITICAL
            except OSError as err:
                self.message = f"Generic Socket error: {err}"
                self.status = libnagios.types.Status.CRITICAL
            finally:
                elapsed = time.time() - start
                self.add_perf_multi({"elapsed": round(time.time() - start, 3)})
            return


def run():
    """Entry point from setup.py for installation of wrapper."""
    instance = Check()
    instance.main()


if __name__ == "__main__":
    run()
