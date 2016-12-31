"""
WinRegal Use the Windows Registry like a king.
:author: Or Weis 2016
"""
try:
    # Try Python 2.7
    import _winreg as winreg
    number_type = long
except ImportError:
    # Try Python 3
    import winreg
    number_type = int
    
import os


class RegValue(object):
    def __init__(self, name, data, data_type):
        """
        Object representing a Registry value
        :param name: the name of the value under its parent key
        :param data: the actual content of the value
        :param data_type: the registry value type (one of the winreg.REG_* values)
        """
        self.name = name
        self.data = data
        self.type = data_type

    def __repr__(self):
        return "RegValue(%s)" % self.__dict__


class WinregalException(WindowsError):
    pass


class KeyNotOpenException(WinregalException):
    """
    Raised when trying to operate on a RegKey, outside of its 'with' block.
    """
    pass


class UnknownHkeyException(WinregalException):
    pass


class RegKey(object):
    HKEY_MAP = {
        winreg.HKEY_CURRENT_USER: "HKEY_CURRENT_USER",
        winreg.HKEY_CLASSES_ROOT: "HKEY_CLASSES_ROOT",
        winreg.HKEY_CURRENT_CONFIG: "HKEY_CURRENT_CONFIG",
        winreg.HKEY_DYN_DATA: "HKEY_DYN_DATA",
        winreg.HKEY_LOCAL_MACHINE: "HKEY_LOCAL_MACHINE",
        winreg.HKEY_PERFORMANCE_DATA: "HKEY_PERFORMANCE_DATA",
        winreg.HKEY_USERS: "HKEY_USERS",
    }

    def __init__(self, path, hkey=None, deep=False):
        """
        Access a Windows registry key path.
        :param str path: The path to the key, may begin with one of HKEY_* strings (see RegKey.HKEY_MAP)
                     in this case pass None for the optional hkey parameter.
                     Example: "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        :param number,None hkey: optional one of the RegKey.HEKEY_MAP.keys()
        :param bool deep: should iterations on sub-keys be recursive
                         (affects self.__iter__, and default for get_sub_key)
        Usage examples:
            k = RegKey("HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run")
                is the same as:
            k = RegKey("\SOFTWARE\Microsoft\Windows\CurrentVersion\Run", winreg.HKEY_LOCAL_MACHINE)
        Note:
            _winreg has been renamed winreg in Python3
        """
        # No HKEY_* given expect it in the path
        # This way we support the string provided by Winreg's 'Copy Key Name'
        if hkey is None:
            split_path = path.split(os.path.sep)
            self._hkey_name = split_path[0].upper()
            path = os.path.join(*split_path[1:])
            hkey = getattr(winreg, self._hkey_name, None)
            if not isinstance(hkey, number_type):
                raise UnknownHkeyException("Couldn't find HKEY name %s" % self._hkey_name)
        else:
            self._hkey_name = self.HKEY_MAP[hkey]
        self._path = path
        self._hkey = hkey
        self._key = None
        self._deep = deep

    @property
    def path(self):
        return self._path

    @property
    def name(self):
        return os.path.split(self.path)[-1]

    @property
    def hkey(self):
        return self._hkey

    @property
    def hkey_name(self):
        return self._hkey_name

    def __enter__(self):
        """
        Open the key for usage within the Context block
        :return: self
        """
        try:
            self._key = winreg.OpenKey(self._hkey, self._path)
            return self
        except WindowsError:
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        winreg.CloseKey(self._key)
        self._key = None

    def get_sub_key(self, sub_path, deep=None):
        """
        :param sub_path: path of the underlying sub-key to access
        :param bool deep: should the opened key be set to recursive iterations. If omitted current keys setting is used
        :return RegKey: The sought key
        """
        if deep is None:
            deep = self._deep
        if self._key is None:
            raise KeyNotOpenException()
        path = os.path.join(self._path, sub_path)
        return RegKey(path, self._hkey, deep=deep)

    def get_value(self, name):
        """
        :param str name: path of the sub value to access
        :return RegValue: sought value
        """
        if self._key is None:
            raise KeyNotOpenException()
        data, data_type = winreg.QueryValueEx(self._key, name)
        return RegValue(name, data, data_type)

    def __getitem__(self, item):
        """
        Convenience wrapper over self.get_value() and self.get_sub_key()
        :param item: the path to the sub item
        :return RegKey, RegValue: the underlying sought key or value
        """
        try:
            return self.get_value(item)
        except KeyNotOpenException:
            raise
        # No value by that name, let's try for a key
        except WindowsError:
            return self.get_sub_key(item)

    def __repr__(self):
        return "RegKey(%s\%s)" % (self.hkey_name, self.path)

    def enum_keys(self):
        """
        Iterate over all keys under this key. Keys are yielded as partial path strings
        :return: an Iterator
        """
        if self._key is None:
            raise KeyNotOpenException()
        i = 0
        while True:
            try:
                yield winreg.EnumKey(self._key, i)
                i += 1
            except WindowsError:
                return

    def enum_values(self):
        """
        Iterate over all values under this key. Values are yielded as a tuple (name, data, data_type)
        :return: an Iterator
        """
        if self._key is None:
            raise KeyNotOpenException()
        i = 0
        while True:
            try:
                yield winreg.EnumValue(self._key, i)
                i += 1
            except WindowsError:
                return

    def __iter__(self):
        """
        Iterate over all Keys and values under this Key
        Recursive if deep is set to True
        """
        for value_tuple in self.enum_values():
            yield RegValue(*value_tuple)
        for key_path in self.enum_keys():
            key = self.get_sub_key(key_path)
            yield key
            if self._deep:
                with key:
                    for item in key:
                        yield item

    def to_dict(self, keep_type=False):
        """
        Recursively traverse registry keys and translate to a python dictionary
        :param bool keep_type: should values be saved as a RegValue(including type) object,
         or should only their data be saved, default is data only.
        :return: a dict representing the registry key hierarchy
        """
        res = {}
        for value_tuple in self.enum_values():
            value = RegValue(*value_tuple)
            if keep_type:
                res[value.name] = value
            else:
                res[value.name] = value.data
        for key_path in self.enum_keys():
            key = self.get_sub_key(key_path, deep=False)
            with key:
                res[key.name] = key.to_dict()
        return res

