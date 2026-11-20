# Changelog

## 2.0.0 - Unreleased

### Breaking
- Dropped Python 2 and Python < 3.9; packaging moved to `pyproject.toml`.
- Enumeration/`to_dict`/iteration now raise on errors other than "no more items" (previously
  swallowed, returning partial data). `key[name]` only falls back to a sub-key when no value
  is found.
- Sub-paths are joined with explicit backslashes: leading separators no longer escape the
  parent key; `/` and `:` are ordinary characters.
- Re-entering an open `RegKey` raises `WinregalException`.
- `WinregalException` now derives from `OSError` (identical to `WindowsError` on Windows).
- `RegValue.__repr__` changed; `RegValue` compares by value (and is unhashable).

### Fixed
- Bare hive paths such as `RegKey("HKEY_CURRENT_USER")` no longer raise `TypeError`.
- Hive names are checked against the real HKEY_* list; unknown explicit `hkey` raises
  `UnknownHkeyException`.
- `to_dict(keep_type=True)` is applied to nested keys.
- `__exit__` is idempotent; no more `SyntaxWarning` for invalid escape sequences.
- Module imports on non-Windows when a `winreg` stand-in is provided (used by tests).

### Added
- `to_dict(max_depth=...)`, type hints and `py.typed`, pytest suite, GitHub Actions CI
  (Linux and Windows), migration notes in the README.

## 1.0.1
- Last release before this changelog.
