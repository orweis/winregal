"""Run only on Windows: exercises the real registry under a throwaway HKCU key."""

import sys

import pytest

pytestmark = [
    pytest.mark.windows,
    pytest.mark.skipif(sys.platform != "win32", reason="requires the Windows registry"),
]

BASE = r"Software\winregal-test"


@pytest.fixture
def real_key():
    import winreg

    k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, BASE + r"\child")
    winreg.SetValueEx(k, "num", 0, winreg.REG_DWORD, 7)
    winreg.SetValueEx(winreg.CreateKey(winreg.HKEY_CURRENT_USER, BASE), "s", 0, winreg.REG_SZ, "hi")
    winreg.CloseKey(k)
    yield
    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, BASE + r"\child")
    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, BASE)


def test_real_roundtrip(real_key):
    from winregal import RegKey

    with RegKey("HKEY_CURRENT_USER\\" + BASE) as key:
        assert key.to_dict() == {"s": "hi", "child": {"num": 7}}
        assert key["s"].data == "hi"
        assert key["child"].path.endswith("winregal-test\\child")
    with RegKey("HKEY_CURRENT_USER") as root:
        assert "Software" in list(root.enum_keys())
