"""WinRegal: use the Windows Registry like a king.

A modern, read-only Python wrapper around :mod:`winreg`.
"""

from __future__ import annotations

import winreg
from collections.abc import Iterator
from typing import Any

#: Windows error code signalling the end of an enumeration.
ERROR_NO_MORE_ITEMS = 259
#: Windows error code for "file (key or value) not found".
ERROR_FILE_NOT_FOUND = 2

_SEP = "\\"


def _hkey_map() -> dict[int, str]:
    names = (
        "HKEY_CURRENT_USER",
        "HKEY_CLASSES_ROOT",
        "HKEY_CURRENT_CONFIG",
        "HKEY_DYN_DATA",
        "HKEY_LOCAL_MACHINE",
        "HKEY_PERFORMANCE_DATA",
        "HKEY_USERS",
    )
    return {getattr(winreg, n): n for n in names if hasattr(winreg, n)}


def _join(base: str, sub_path: str) -> str:
    """Join registry path parts with backslashes only.

    Unlike ``os.path.join`` a leading separator in ``sub_path`` never discards
    ``base``, and ``/`` or ``:`` are ordinary characters (valid in key names).
    """
    parts = [p for p in (base.strip(_SEP), sub_path.strip(_SEP)) if p]
    return _SEP.join(parts)


def _is_not_found(exc: OSError) -> bool:
    return getattr(exc, "winerror", None) == ERROR_FILE_NOT_FOUND or isinstance(
        exc, FileNotFoundError
    )


class RegValue:
    """A registry value.

    :param name: the name of the value under its parent key
    :param data: the actual content of the value
    :param data_type: the registry value type (one of the ``winreg.REG_*`` values)
    """

    def __init__(self, name: str, data: Any, data_type: int) -> None:
        self.name = name
        self.data = data
        self.type = data_type

    def __repr__(self) -> str:
        return f"RegValue(name={self.name!r}, data={self.data!r}, type={self.type!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RegValue):
            return NotImplemented
        return (self.name, self.data, self.type) == (other.name, other.data, other.type)

    __hash__ = None  # type: ignore[assignment]  # mutable, compares by value


class WinregalException(OSError):
    """Base class of all WinRegal errors (``WindowsError`` on Windows is ``OSError``)."""


class KeyNotOpenException(WinregalException):
    """Raised when operating on a RegKey outside of its 'with' block."""


class UnknownHkeyException(WinregalException):
    """Raised when a hive (HKEY_*) name or handle is not recognised."""


class RegKey:
    r"""Read-only access to a Windows registry key.

    :param str path: path to the key, may begin with one of the HKEY_* names
        (see ``RegKey.HKEY_MAP``); in that case leave ``hkey`` as None.
        A bare hive name (``"HKEY_CURRENT_USER"``) opens the hive root.
    :param hkey: optional, one of ``RegKey.HKEY_MAP`` keys
    :param bool deep: should iteration be recursive (affects ``__iter__`` and
        the default for ``get_sub_key``)

    Example::

        RegKey(r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run")
        RegKey(r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", winreg.HKEY_LOCAL_MACHINE)

    Not re-entrant: a RegKey object can be used in one ``with`` block at a time.
    """

    HKEY_MAP = _hkey_map()
    _NAME_TO_HKEY = {name: hkey for hkey, name in HKEY_MAP.items()}

    def __init__(self, path: str, hkey: int | None = None, deep: bool = False) -> None:
        # No hkey given: expect an HKEY_* name as the first path segment (this is
        # the format produced by regedit's "Copy Key Name").
        if hkey is None:
            first, _, rest = path.strip(_SEP).partition(_SEP)
            self._hkey_name = first.upper()
            hkey = self._NAME_TO_HKEY.get(self._hkey_name)
            if hkey is None:
                raise UnknownHkeyException(f"Couldn't find HKEY name {first}")
            path = rest
        else:
            try:
                self._hkey_name = self.HKEY_MAP[hkey]
            except (KeyError, TypeError):
                raise UnknownHkeyException(f"Unknown hkey {hkey!r}") from None
        self._path = path.strip(_SEP)
        self._hkey = hkey
        self._key: Any = None
        self._deep = deep

    @property
    def path(self) -> str:
        """Path of the key under its hive."""
        return self._path

    @property
    def name(self) -> str:
        """Last segment of the key path (empty for a hive root)."""
        return self._path.rsplit(_SEP, 1)[-1]

    @property
    def hkey(self) -> int:
        return self._hkey

    @property
    def hkey_name(self) -> str:
        return self._hkey_name

    def __enter__(self) -> RegKey:
        """Open the key for use within the context block."""
        if self._key is not None:
            raise WinregalException(f"RegKey {self!r} is already open")
        self._key = winreg.OpenKey(self._hkey, self._path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        key, self._key = self._key, None
        if key is not None:
            winreg.CloseKey(key)

    def _require_open(self) -> Any:
        if self._key is None:
            raise KeyNotOpenException()
        return self._key

    def get_sub_key(self, sub_path: str, deep: bool | None = None) -> RegKey:
        """Return an (unopened) RegKey for ``sub_path`` relative to this key.

        Leading/trailing backslashes in ``sub_path`` are ignored: the result is
        always beneath this key.

        :param deep: recursive iteration for the new key; defaults to this key's setting
        """
        self._require_open()
        if deep is None:
            deep = self._deep
        return RegKey(_join(self._path, sub_path), self._hkey, deep=deep)

    def get_value(self, name: str) -> RegValue:
        """Return the value called ``name`` (raises OSError if missing)."""
        data, data_type = winreg.QueryValueEx(self._require_open(), name)
        return RegValue(name, data, data_type)

    def __getitem__(self, item: str) -> RegValue | RegKey:
        """Return the value called ``item``, or if there is none, the sub-key.

        Only a "not found" error falls back to the sub-key; any other error
        (e.g. access denied) propagates.
        """
        try:
            return self.get_value(item)
        except KeyNotOpenException:
            raise
        except OSError as e:
            if not _is_not_found(e):
                raise
        return self.get_sub_key(item)

    def __repr__(self) -> str:
        return f"RegKey({self.hkey_name}\\{self.path})"

    def enum_keys(self) -> Iterator[str]:
        """Yield the names of all sub-keys. Errors other than end-of-list propagate."""
        key = self._require_open()
        i = 0
        while True:
            try:
                name = winreg.EnumKey(key, i)
            except OSError as e:
                if getattr(e, "winerror", None) == ERROR_NO_MORE_ITEMS:
                    return
                raise
            yield name
            i += 1

    def enum_values(self) -> Iterator[tuple]:
        """Yield ``(name, data, data_type)`` per value. Errors other than end-of-list propagate."""
        key = self._require_open()
        i = 0
        while True:
            try:
                item = winreg.EnumValue(key, i)
            except OSError as e:
                if getattr(e, "winerror", None) == ERROR_NO_MORE_ITEMS:
                    return
                raise
            yield item
            i += 1

    def __iter__(self) -> Iterator[RegValue | RegKey]:
        """Iterate over values, then sub-keys (recursively if ``deep``)."""
        for value_tuple in self.enum_values():
            yield RegValue(*value_tuple)
        for key_path in self.enum_keys():
            key = self.get_sub_key(key_path)
            yield key
            if self._deep:
                with key:
                    yield from key

    def to_dict(self, keep_type: bool = False, max_depth: int | None = None) -> dict[str, Any]:
        """Recursively translate this key to a dict.

        :param keep_type: store RegValue objects (with type) instead of bare data
        :param max_depth: optional limit on sub-key nesting; deeper keys are omitted
            (None, the default, means unlimited)

        A value and a sub-key sharing a name collide; the sub-key wins.
        """
        res: dict[str, Any] = {}
        for value_tuple in self.enum_values():
            value = RegValue(*value_tuple)
            res[value.name] = value if keep_type else value.data
        if max_depth is not None and max_depth <= 0:
            return res
        next_depth = None if max_depth is None else max_depth - 1
        for key_path in self.enum_keys():
            key = self.get_sub_key(key_path, deep=False)
            with key:
                res[key_path] = key.to_dict(keep_type=keep_type, max_depth=next_depth)
        return res
