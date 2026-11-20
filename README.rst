WinRegal
========

|ci|

    "Use the Windows Registry like a king"

A modern, read-only Python wrapper for the Windows Registry (wrapping ``winreg``).
Walk keys and values with a ``with`` statement and plain iteration, or dump a whole
key hierarchy to a ``dict``.

.. |ci| image:: https://github.com/orweis/winregal/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/orweis/winregal/actions/workflows/ci.yml

Requirements
------------
- Python 3.9 or newer
- Windows (the module imports ``winreg``, which exists only on Windows)

Install
-------
.. code:: bash

    pip install winregal

Usage
-----
Use ``winregal.RegKey`` with the ``with`` statement to access any key. Keys are
opened and closed for you. All paths use backslashes, and may start with a hive name
(``HKEY_CURRENT_USER``, ``HKEY_LOCAL_MACHINE``, ...) exactly as regedit's "Copy Key Name"
produces them. A bare hive name opens the hive root.

Get a key hierarchy as a dictionary
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Example: print PuTTY sessions

.. code:: python

    from winregal import RegKey

    with RegKey(r"HKEY_CURRENT_USER\SOFTWARE\SimonTatham\PuTTY\Sessions") as key:
        print(key.to_dict())

    # {'Server1': {'UserName': 'user', 'HostName': '192.168.48.131', ...},
    #  'Server2': {'UserName': 'user', 'HostName': '192.168.48.132', ...}}

``to_dict(keep_type=True)`` keeps ``RegValue`` objects (name, data, registry type) instead
of bare data. ``to_dict(max_depth=n)`` limits sub-key nesting. A value and a sub-key with the
same name collide; the sub-key wins.

Iterate over a key's values and sub-keys
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Example: print most recently run commands (RunMRU)

.. code:: python

    from winregal import RegKey, RegValue

    with RegKey(r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU") as key:
        for item in key:
            if isinstance(item, RegValue):
                print(item.name, item.data)

    # a cmd\1
    # b winword\1

Iteration yields values first, then sub-keys (``RegKey`` objects). Pass ``deep=True`` to
``RegKey`` to also recurse into sub-keys.

Directly access a value or key
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. code:: python

    with RegKey(r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU") as key:
        print(key["a"].data)   # cmd\1

``key[name]`` returns the ``RegValue`` called *name* or, if none exists, the sub-key *name*
(an unopened ``RegKey``; enter it with ``with``). Sub-key names are always relative to the
key: leading backslashes are ignored and they can never escape the parent.

Errors
~~~~~~
All exceptions derive from ``WinregalException`` (an ``OSError``):
``KeyNotOpenException`` (used outside the ``with`` block), ``UnknownHkeyException``
(bad hive name or handle). Registry errors such as access denied propagate as ``OSError``.

Development
-----------
.. code:: bash

    pip install -e ".[test]"
    pytest

The unit tests run on any OS against a fake in-memory ``winreg``. Tests marked ``windows``
use the real registry (under a throwaway ``HKCU\Software\winregal-test`` key) and run only
on Windows. See ``CHANGELOG.md`` for release history.

Migrating from 1.x to 2.0
-------------------------
- Python 2 and Python < 3.9 are no longer supported.
- Enumeration (``enum_keys``, ``enum_values``, ``to_dict``, iteration) now raises on real
  errors such as access denied; previously they silently stopped and returned partial data.
- ``key[name]`` falls back to a sub-key only when no value exists; other errors propagate.
- A ``sub_path`` starting with ``\`` (or ``/``, or ``C:``) is now treated as relative to the
  key; previously it could escape to another key of the hive. ``/`` and ``:`` are ordinary
  name characters, as in the registry itself.
- ``RegKey("HKEY_CURRENT_USER")`` (hive only) now works; ``RegKey(path, unknown_hkey)`` and
  hive names that are not real hives raise ``UnknownHkeyException``.
- ``to_dict(keep_type=True)`` now applies to nested keys too.
- Re-entering an already-open ``RegKey`` raises ``WinregalException``.
- ``WinregalException`` derives from ``OSError`` instead of ``WindowsError`` (the same class on Windows).
- ``RegValue.__repr__`` changed and ``RegValue`` now compares by value.

Roadmap
-------
Not implemented yet: ``ConnectRegistry`` support and write operations (``CreateKey``,
``DeleteKey``, ``DeleteValue``, ``SetValue``, ``SaveKey``).
Contact me (py@bitweis.com) if you need these anytime soon.
