"""Run only on Windows: exercises the real registry under a throwaway HKCU key."""

import sys
import uuid

import pytest

pytestmark = [
    pytest.mark.windows,
    pytest.mark.skipif(sys.platform != "win32", reason="requires the Windows registry"),
]

BASE = r"Software\winregal-test-" + uuid.uuid4().hex


@pytest.fixture
def real_key():
    import winreg

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, BASE + r"\child") as k:
            winreg.SetValueEx(k, "num", 0, winreg.REG_DWORD, 7)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, BASE) as k:
            winreg.SetValueEx(k, "s", 0, winreg.REG_SZ, "hi")
        yield
    finally:
        for path in (BASE + r"\child", BASE):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
            except OSError:
                pass


def test_real_roundtrip(real_key):
    from winregal import RegKey

    with RegKey("HKEY_CURRENT_USER\\" + BASE) as key:
        assert key.to_dict() == {"s": "hi", "child": {"num": 7}}
        assert key["s"].data == "hi"
        assert key["child"].path.endswith("\\child")
    with RegKey("HKEY_CURRENT_USER") as root:
        # Registry key names are case-insensitive; some images store "SOFTWARE".
        assert "software" in [name.lower() for name in root.enum_keys()]
