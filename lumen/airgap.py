"""Airgap mode — a hard, process-wide block on all outbound network.

When engaged, Lumen patches the socket layer so any connection to a
non-loopback address is refused. Local model servers (127.0.0.1 / localhost)
keep working; anything that would leave the machine cannot. This turns
"privacy-first" from a promise into something you can prove: with airgap on,
your code physically cannot be uploaded, even by a bug or a rogue dependency.
"""

from __future__ import annotations

import ipaddress
import socket

_LOCAL_HOSTNAMES = {"localhost", "localhost.localdomain", "ip6-localhost", ""}

_ORIG_CONNECT = socket.socket.connect
_ORIG_CONNECT_EX = socket.socket.connect_ex
_ORIG_CREATE_CONNECTION = socket.create_connection

_enabled = False


class AirgapBlocked(OSError):
    """Raised when airgap mode refuses an outbound connection."""


def _is_local(address) -> bool:
    # AF_UNIX or unusual address shapes are local IPC — allow.
    if not isinstance(address, tuple) or not address:
        return True
    host = address[0]
    if isinstance(host, str) and host in _LOCAL_HOSTNAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        # A hostname that isn't localhost — treat as remote (block it).
        return False


def _guard_connect(self, address, *args, **kwargs):
    if _enabled and not _is_local(address):
        raise AirgapBlocked(f"airgap mode: blocked outbound connection to {address!r}")
    return _ORIG_CONNECT(self, address, *args, **kwargs)


def _guard_connect_ex(self, address, *args, **kwargs):
    if _enabled and not _is_local(address):
        raise AirgapBlocked(f"airgap mode: blocked outbound connection to {address!r}")
    return _ORIG_CONNECT_EX(self, address, *args, **kwargs)


def _guard_create_connection(address, *args, **kwargs):
    if _enabled and not _is_local(address):
        raise AirgapBlocked(f"airgap mode: blocked outbound connection to {address!r}")
    return _ORIG_CREATE_CONNECTION(address, *args, **kwargs)


def enable() -> None:
    global _enabled
    socket.socket.connect = _guard_connect
    socket.socket.connect_ex = _guard_connect_ex
    socket.create_connection = _guard_create_connection
    _enabled = True


def disable() -> None:
    global _enabled
    _enabled = False
    socket.socket.connect = _ORIG_CONNECT
    socket.socket.connect_ex = _ORIG_CONNECT_EX
    socket.create_connection = _ORIG_CREATE_CONNECTION


def is_enabled() -> bool:
    return _enabled
