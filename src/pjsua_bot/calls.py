"""Compatibility shim for call classes.

This module preserves the old import path `pjsua_bot.calls` while the
implementations live under the package `pjsua_bot.calls`.
"""

from .calls.any_call import AnyCall
from .calls.out_call import OutCall

__all__ = ["AnyCall", "OutCall"]
