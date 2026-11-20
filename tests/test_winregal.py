import pytest
from conftest import make_oserror

from winregal import (
    KeyNotOpenException,
    RegKey,
    RegValue,
    UnknownHkeyException,
    WinregalException,
)
from winregal import winregal as mod

HKCU = mod.winreg.HKEY_CURRENT_USER


@pytest.fixture
def tree(reg):
    reg.add(HKCU, "", subkeys=["SOFTWARE"])
    reg.add(HKCU, "SOFTWARE", {"v": ("x", 1)}, ["App", "/odd"])
    reg.add(HKCU, "SOFTWARE\\App", {"n": (5, 4)}, ["Deep"])
    reg.add(HKCU, "SOFTWARE\\App\\Deep", {"d": ("deep", 1)})
    reg.add(HKCU, "SOFTWARE\\/odd", {"o": ("slash", 1)})
    reg.add(HKCU, "SOFTWARE\\x:y", {})
    return reg


def test_exceptions_are_oserror():
    assert issubclass(WinregalException, OSError)
    assert issubclass(KeyNotOpenException, WinregalException)
    assert issubclass(UnknownHkeyException, WinregalException)


def test_path_with_hive_name_case_insensitive():
    k = RegKey("hkey_current_user\\SOFTWARE\\App")
    assert (k.hkey, k.hkey_name) == (HKCU, "HKEY_CURRENT_USER")
    assert (k.path, k.name) == ("SOFTWARE\\App", "App")


def test_bare_hive_opens_root():
    k = RegKey("HKEY_CURRENT_USER")
    assert k.path == "" and k.name == ""
    assert repr(k) == "RegKey(HKEY_CURRENT_USER\\)"


def test_explicit_hkey_strips_leading_separator():
    assert RegKey("\\SOFTWARE\\App", HKCU).path == "SOFTWARE\\App"


@pytest.mark.parametrize("bad", ["KEY_READ\\x", "REG_SZ\\x", "NOPE\\x", ""])
def test_unknown_hive_in_path(bad):
    with pytest.raises(UnknownHkeyException):
        RegKey(bad)


def test_unknown_explicit_hkey():
    with pytest.raises(UnknownHkeyException):
        RegKey("SOFTWARE", 12345)


def test_not_open_errors(reg):
    k = RegKey("HKEY_CURRENT_USER\\SOFTWARE")
    with pytest.raises(KeyNotOpenException):
        k.get_sub_key("a")
    with pytest.raises(KeyNotOpenException):
        k.get_value("v")
    with pytest.raises(KeyNotOpenException):
        list(k.enum_keys())
    with pytest.raises(KeyNotOpenException):
        list(k.enum_values())
    with pytest.raises(KeyNotOpenException):
        k["v"]


def test_context_manager_opens_and_closes(tree):
    k = RegKey("HKEY_CURRENT_USER\\SOFTWARE")
    with k:
        assert len(tree.open_handles) == 1
    assert not tree.open_handles and len(tree.closed) == 1
    with pytest.raises(KeyNotOpenException):
        k.get_value("v")


def test_closed_even_on_exception(tree):
    with pytest.raises(RuntimeError):
        with RegKey("HKEY_CURRENT_USER\\SOFTWARE"):
            raise RuntimeError
    assert not tree.open_handles


def test_missing_key_raises_and_does_not_leak(tree):
    with pytest.raises(OSError):
        with RegKey("HKEY_CURRENT_USER\\Nope"):
            pass


def test_double_enter_rejected_and_handle_kept(tree):
    k = RegKey("HKEY_CURRENT_USER\\SOFTWARE")
    with k:
        with pytest.raises(WinregalException):
            k.__enter__()
        assert k.get_value("v").data == "x"
    assert not tree.open_handles


def test_exit_idempotent(tree):
    k = RegKey("HKEY_CURRENT_USER\\SOFTWARE")
    k.__exit__(None, None, None)  # never entered
    with k:
        pass
    k.__exit__(None, None, None)
    assert len(tree.closed) == 1


def test_get_value(tree):
    with RegKey("HKEY_CURRENT_USER\\SOFTWARE") as k:
        assert k.get_value("v") == RegValue("v", "x", 1)
        with pytest.raises(OSError):
            k.get_value("missing")


def test_getitem_value_then_subkey_fallback(tree):
    with RegKey("HKEY_CURRENT_USER\\SOFTWARE") as k:
        assert k["v"].data == "x"
        sub = k["App"]
        assert isinstance(sub, RegKey) and sub.path == "SOFTWARE\\App"


def test_getitem_propagates_non_notfound_errors(tree, monkeypatch):
    def denied(handle, name):
        raise make_oserror(5)

    monkeypatch.setattr(mod.winreg, "QueryValueEx", denied)
    with RegKey("HKEY_CURRENT_USER\\SOFTWARE") as k:
        with pytest.raises(OSError) as ei:
            k["v"]
        assert ei.value.winerror == 5


def test_sub_key_cannot_escape_parent(tree):
    with RegKey("HKEY_CURRENT_USER\\SOFTWARE\\App") as k:
        for evil in ("\\Other", "/Other", "C:\\Other", "\\\\x"):
            assert k.get_sub_key(evil).path.startswith("SOFTWARE\\App\\")
        assert k.get_sub_key("\\Other\\").path == "SOFTWARE\\App\\Other"
        assert k.get_sub_key("/odd").path == "SOFTWARE\\App\\/odd"


def test_sub_key_inherits_and_overrides_deep(tree):
    with RegKey("HKEY_CURRENT_USER\\SOFTWARE", deep=True) as k:
        assert k.get_sub_key("App")._deep is True
        assert k.get_sub_key("App", deep=False)._deep is False


def test_name_with_slash_and_colon():
    assert RegKey("HKEY_CURRENT_USER\\SOFTWARE\\/odd").name == "/odd"
    assert RegKey("HKEY_CURRENT_USER\\SOFTWARE\\a:b").name == "a:b"


def test_enum_keys_and_values(tree):
    with RegKey("HKEY_CURRENT_USER\\SOFTWARE") as k:
        assert list(k.enum_keys()) == ["App", "/odd"]
        assert list(k.enum_values()) == [("v", "x", 1)]


@pytest.mark.parametrize("code", [5, 234, 1])
def test_enum_errors_not_swallowed(tree, code):
    tree.fail_enum_keys_with = code
    with RegKey("HKEY_CURRENT_USER\\SOFTWARE") as k:
        with pytest.raises(OSError):
            list(k.enum_keys())
        with pytest.raises(OSError):
            k.to_dict()


def test_enum_values_error_propagates(tree, monkeypatch):
    def boom(handle, i):
        raise make_oserror(5)

    monkeypatch.setattr(mod.winreg, "EnumValue", boom)
    with RegKey("HKEY_CURRENT_USER\\SOFTWARE") as k:
        with pytest.raises(OSError):
            list(k.enum_values())


def test_iter_shallow(tree):
    with RegKey("HKEY_CURRENT_USER\\SOFTWARE") as k:
        items = list(k)
    assert items[0] == RegValue("v", "x", 1)
    assert [i.path for i in items[1:]] == ["SOFTWARE\\App", "SOFTWARE\\/odd"]


def test_iter_deep_resolves_slash_named_subkey_under_parent(tree):
    with RegKey("HKEY_CURRENT_USER\\SOFTWARE", deep=True) as k:
        items = list(k)
    values = [i.data for i in items if isinstance(i, RegValue)]
    assert values == ["x", 5, "deep", "slash"]
    assert not tree.open_handles


def test_to_dict(tree):
    with RegKey("HKEY_CURRENT_USER\\SOFTWARE") as k:
        d = k.to_dict()
    assert d == {
        "v": "x",
        "App": {"n": 5, "Deep": {"d": "deep"}},
        "/odd": {"o": "slash"},
    }
    assert not tree.open_handles


def test_to_dict_keep_type_applies_recursively(tree):
    with RegKey("HKEY_CURRENT_USER\\SOFTWARE") as k:
        d = k.to_dict(keep_type=True)
    assert d["v"] == RegValue("v", "x", 1)
    assert d["App"]["Deep"]["d"] == RegValue("d", "deep", 1)


def test_to_dict_max_depth(tree):
    with RegKey("HKEY_CURRENT_USER\\SOFTWARE") as k:
        assert k.to_dict(max_depth=0) == {"v": "x"}
        assert k.to_dict(max_depth=1) == {"v": "x", "App": {"n": 5}, "/odd": {"o": "slash"}}


def test_to_dict_name_collision_subkey_wins(reg):
    reg.add(HKCU, "A", {"same": ("val", 1)}, ["same"])
    reg.add(HKCU, "A\\same", {"inner": (1, 4)})
    with RegKey("HKEY_CURRENT_USER\\A") as k:
        assert k.to_dict() == {"same": {"inner": 1}}


def test_regvalue_repr_eq():
    v = RegValue("n", 1, 4)
    assert repr(v) == "RegValue(name='n', data=1, type=4)"
    assert v == RegValue("n", 1, 4) and v != RegValue("n", 2, 4) and v != "x"
