"""Test setup: a fake ``winreg`` is installed when the real one is unavailable (non-Windows)."""

import sys
import types

import pytest

try:
    import winreg  # noqa: F401
except ImportError:
    fake = types.ModuleType("winreg")
    for _i, _n in enumerate(
        [
            "HKEY_CLASSES_ROOT",
            "HKEY_CURRENT_USER",
            "HKEY_LOCAL_MACHINE",
            "HKEY_USERS",
            "HKEY_PERFORMANCE_DATA",
            "HKEY_CURRENT_CONFIG",
            "HKEY_DYN_DATA",
        ]
    ):
        setattr(fake, _n, 0x80000000 + _i)
    fake.REG_SZ = 1
    fake.REG_DWORD = 4
    sys.modules["winreg"] = fake

from winregal import winregal as mod  # noqa: E402


def make_oserror(winerror):
    err = OSError(winerror, "fake error")
    err.winerror = winerror
    return err


class FakeRegistry:
    """In-memory registry. Keys: (hkey, path) -> {"values": {...}, "keys": [...]}"""

    def __init__(self):
        self.tree = {}
        self.open_handles = {}
        self.closed = []
        self.fail_enum_keys_with = None
        self._next = 1

    def add(self, hkey, path, values=None, subkeys=()):
        self.tree[(hkey, path)] = {"values": dict(values or {}), "keys": list(subkeys)}

    # winreg API
    def OpenKey(self, hkey, path):
        if (hkey, path) not in self.tree:
            raise make_oserror(2)
        handle = self._next
        self._next += 1
        self.open_handles[handle] = (hkey, path)
        return handle

    def CloseKey(self, handle):
        self.open_handles.pop(handle)
        self.closed.append(handle)

    def QueryValueEx(self, handle, name):
        node = self.tree[self.open_handles[handle]]
        if name not in node["values"]:
            raise make_oserror(2)
        return node["values"][name]

    def EnumKey(self, handle, i):
        if self.fail_enum_keys_with is not None:
            raise make_oserror(self.fail_enum_keys_with)
        keys = self.tree[self.open_handles[handle]]["keys"]
        if i >= len(keys):
            raise make_oserror(259)
        return keys[i]

    def EnumValue(self, handle, i):
        values = list(self.tree[self.open_handles[handle]]["values"].items())
        if i >= len(values):
            raise make_oserror(259)
        name, (data, typ) = values[i]
        return (name, data, typ)


@pytest.fixture
def reg(monkeypatch):
    r = FakeRegistry()
    for fn in ("OpenKey", "CloseKey", "QueryValueEx", "EnumKey", "EnumValue"):
        monkeypatch.setattr(mod.winreg, fn, getattr(r, fn), raising=False)
    return r
