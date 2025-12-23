"""Call classes package split from the original single module.

Important: `pjsua2` is an optional runtime dependency in CI/unit tests.
So we avoid importing `pjsua2`-dependent modules eagerly at package import time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .any_call import AnyCall as AnyCall
    from .out_call import OutCall as OutCall


def __getattr__(name: str) -> Any:
    if name == "AnyCall":
        from .any_call import AnyCall

        return AnyCall
    if name == "OutCall":
        from .out_call import OutCall

        return OutCall
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["AnyCall", "OutCall"]
