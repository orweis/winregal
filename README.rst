WinRegal
========
| "Use the Windows Registry like a king"
| A Modern Python wrapper for the Windows Registry (wrapping winreg)
| Python Windows Registry Module
| Access Registry like a dict


Install
-------
pip install winregal

Usage
-----
Use winregal.RegKey along with the 'with' statement to access any key of your choice.
winregal handles key opening and closing for you and makes iteration really simple.


Get a Key hierarchy with all values as a dictionary
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Example : Print Putty sessions

.. code:: python

    In[2]: from winregal import RegKey
    In[3]: with RegKey("HKEY_CURRENT_USER\SOFTWARE\SimonTatham\PuTTY\Sessions") as key:
    ...     print(key.to_dict())
    ...
    {'Server1: {'UserName': u'user', 'HostName': u'192.168.48.131', ... },
     'Server2': {'UserName': u'user', 'HostName': u'192.168.48.132', ... }}


Iterate over Key hierarchy handling only values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Example : Print most recently run commands(RunMru)

.. code:: python

    In[1]: with RegKey("HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU") as key:
    ...     for item in key:
    ...         if isinstance(item, RegValue):
    ...             print(item.name, item.data)
    ...
    ('a', u'cmd\\1')
    ('b', u'winword\\1')
    ('c', u'notepad\\1')
    ('d', u'control\\1')
    ('e', u'regedit\\1')
    ('f', u'calc\\1')
    ('j', u'notepad++\\1')


Directly access a value / key
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    In[10]: with RegKey("HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU") as key:
    ...     print(key['a'].data)
    ...
    cmd\1


Next in module Development
--------------------------
- Support ConnectRegistry (via RegKey.__init__)
- Wrap Edit/Save/Delete operations: e.g. CreateKey, DeleteKey, DeleteValue, SetValue, SaveKey

Contact me (py@bitweis.com) if you need these anytime soon.
