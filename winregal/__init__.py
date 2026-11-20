"""WinRegal: a modern Python wrapper for the Windows registry <https://github.com/orweis/winregal>."""

from .winregal import (
    KeyNotOpenException,
    RegKey,
    RegValue,
    UnknownHkeyException,
    WinregalException,
)

__all__ = [
    "KeyNotOpenException",
    "RegKey",
    "RegValue",
    "UnknownHkeyException",
    "WinregalException",
]

__author__ = "Or Weis"
__title__ = "WinRegal"
__description__ = "A Modern Python wrapper for the Windows registry"
__uri__ = "https://github.com/orweis/winregal"
__email__ = "py@bitweis.com"
__version__ = "2.0.0"
__license__ = "MIT"
__copyright__ = "Copyright (c) 2016 Or Weis"
