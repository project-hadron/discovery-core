import ast
import threading
import uuid
from datetime import datetime
from typing import Any
import pyarrow as pa
import ds_core
from ds_core.handlers.abstract_handlers import AbstractPersistHandler
from ds_core.properties.decorator_patterns import singleton



class PropertyManager(object):
    """

    A thread safe singleton in-memory, NoSQL, multi-tenant class that allows for the management of key/value pairs
    to be stored and retrieved. The persisted values are stored in files specified when persisted

    The value's are stored as a tree structure with the key being a dot separated string value up the tree.
    For example key 'root.directories.base_dir' returns [str]: 'filepath' .
    Where the underlying Dictionary looks like { root: { directories: { base_dir : 'filepath' }}}.

    The key can reference any part of the tree and will return the object at that point.
    From the example above key 'root' would return [dict]: { directories: { base_dir : 'filepath' }}.

    The key must start from the base key and work up, this allows namespace to avoid repeated key values.
    """

    __properties = dict({})
    __lock = threading.Lock()

    @singleton
    def __new__(cls):
        return super().__new__(cls)

    @classmethod
    def is_key(cls, key: Any) -> bool:
        """identifies if a key exists or not.

        :param key: the key of the value
            The key should be a dot separated string of keys from root up the tree
        :return:
            True if the key exists in the properties
            False if the key doesn't exist in the properties
        """
        if key is None or not key:
            return False
        find_dict = cls.__properties
        is_path, _, is_key = key.rpartition('.')
        if is_path:
            for part in is_path.split('.'):
                if isinstance(find_dict, dict):
                    find_dict = find_dict.get(part, {})
                else:
                    break
        if is_key in find_dict:
            return True
        return False

    @classmethod
    def get(cls, key: Any, default: Any=None) -> [object, str, dict, tuple, list, int, float]:
        """ gets a property value for the dot separated key.

        :param key: the key of the value
            The key should be a dot separated string of keys from root up the tree
        :param default: (optional) a default value to return if no value is found

        :return:
            an object found in the key can be any structure found under that key
            if the key is not found, None is returned
            If the key is None then the complete properties dictionary is returned
            will be the full tree under the requested key, be it a value, tuple, list or dictionary
        """
        if key is None or not key:
            return default
        rtn_val = cls.__properties
        for part in key.split('.'):
            if isinstance(rtn_val, dict):
                rtn_val = rtn_val.get(part)
                if rtn_val is None:
                    return default
            else:
                return default
        with cls.__lock:
            return rtn_val

    @classmethod
    def get_all(cls) -> dict:
        """ gets all the properties

        :returns:
            a deep copy of the  of key/value pairs
        """
        with cls.__lock:
            return cls.__properties.copy()

    @classmethod
    def set(cls, key: Any, value: Any) -> None:
        """ sets a key value pair. The value can be Union(Str, Dict, Tuple, Array)

        :param key: the key string
        :param value: the value of the key
        """
        if key is None or not key or not isinstance(key, str):
            raise ValueError("The key must be a valid str")
        keys = key.split('.')
        _prop_branch = cls.__properties
        _last_key = None
        _last_prop_branch = None
        # from base of the key work up to find where the section doesn't exist
        for _, k in list(enumerate(keys)):
            if k not in _prop_branch:
                break
            _last_prop_branch = _prop_branch
            _last_key = k
            _prop_branch = _prop_branch[k]
        tmp_dict = {}
        # now from the top of the key work back, creating the sections tree
        k = None
        for _, k in reversed(list(enumerate(keys))):
            if isinstance(value, dict):
                tmp_dict = {k: value}
            else:
                tmp_dict[k] = value
            if k is _last_key:
                break
            value = tmp_dict
        if not isinstance(value, dict):
            if isinstance(_last_prop_branch[k], list):
                if isinstance(value, list):
                    _last_prop_branch[k] += value
                else:
                    _last_prop_branch[k].append(value)
            else:
                _last_prop_branch[k] = value
            return
        if _last_prop_branch is None:
            _prop_branch.update(value)
        else:
            cls._add_value(k, value, _last_prop_branch)
        return

    @classmethod
    def remove(cls, key: Any) -> bool:
        """removes a key/value from the in-memory configuration dictionary based on the key

        :param key: the key of the key/value to be removed
            The key should be a dot separated string of keys from root up the tree

        :return:
            True if the key was removed
            False if the key was not found
        """
        del_dict = cls.__properties
        del_path, _, del_key = key.rpartition('.')
        if del_path:
            for part in del_path.split('.'):
                if isinstance(del_dict, dict):
                    del_dict = del_dict.get(part)
                else:
                    return False
        if del_dict is None or del_key not in del_dict:
            return False
        with cls.__lock:
            _ = del_dict.pop(del_key, None)
        return True

    @classmethod
    def load(cls, handler: AbstractPersistHandler, key: str=None, replace: bool=False,
             ignore_key_error: bool=None) -> bool:
        """ loads the properties from the configuration file. allows for multiple configuration
        files to be merged into the properties dictionary, or properties to be refreshed in real time.

        :param handler: the handler to load the configuration from.
        :param key: An optional root key subset of the configuration values (dot format e.g. root.level1).
        :param replace: if the file is to be added to or replaced
        :param ignore_key_error: when providing a key, if the key is not found continue without loading or error
        :return: True if the file was found, opened and loaded, False if an exception was thrown.
        """
        if handler is None or not isinstance(handler, AbstractPersistHandler):
            raise ValueError("The handler must be a concrete implementation of AbstractPersistHandler")
        # extract the data
        tbl = handler.load_canonical()
        arr = tbl.column('meta').combine_chunks()
        cfg_dict = ast.literal_eval(arr.to_pylist()[0])
        # construct the dict
        if replace:
            with cls.__lock:
                cls.__properties.clear()
        # Don't copy over the file meta data
        _ = cfg_dict.pop('config_meta')
        if isinstance(key, str):
            subset = cfg_dict
            for k in key.split('.'):
                if isinstance(subset, dict) and k in subset:
                    subset = subset.get(k, {})
                else:
                    if isinstance(ignore_key_error, bool) and ignore_key_error:
                        return False
                    raise KeyError(f"The key '{key}' could not be found in the properties canonical when loading.")
            cls.set(key, subset)
        elif replace:
            cls.__properties = cfg_dict
        else:
            for _key, _value in cfg_dict.items():
                # only replace sections that have changed
                cls.set(_key, _value)
        return True

    @classmethod
    def dump(cls, handler: AbstractPersistHandler, key: Any=None):
        """ Dumps the current in-memory configuration to a persistence store.
        Note that this replaces existing content if the file exists. This is particularly
        important is only persisting a single root key.

        The use of the root key option allows for the breakdown of persisted files into
        multiple files for easier management.

        :param handler: the handler to persist the configuration.
        :param key: An optional root key subset of the configuration values.
        """
        if handler is None or not isinstance(handler, AbstractPersistHandler):
            raise ValueError("The handler must be a concrete implementation of AbstractPersistHandler")
        _time = str(datetime.now())
        if not cls.is_key('config_meta.uid') or not cls.is_key('config_meta.create'):
            cls.set('config_meta.uid', str(uuid.uuid4()))
            cls.set('config_meta.create', _time)
        cls.set('config_meta.modify', _time)
        cls.set('config_meta.release', ds_core.__version__)
        # check we want to persist
        if key is None:
            with cls.__lock:
                data = cls.__properties.copy()
        else:
            if not cls.is_key(key):
                raise KeyError("The base key {} does not exist".format(key))
            # from base of the key work up
            keys = key.split('.')
            _pointer = {}
            data = _pointer
            while len(keys) > 0:
                _k = keys.pop(0)
                _pointer[_k] = {}
                _pointer = _pointer[_k]
            _value = cls.get(key)
            if isinstance(_value, str):
                __pointer = _value
            else:
                _pointer.update(cls.get(key))
            data['config_meta'] = cls.get('config_meta')

        # now build the canonical
        a_meta = pa.array([str(data)], pa.string())
        handler.persist_canonical(pa.table([a_meta], names=['meta']))
        return

    @staticmethod
    def join(*names, sep: str=None) -> str:
        """Used to create a name string. Can also be used to join paths by passing sep=os.path.sep

        :param names: the names to join
        :param sep: the join separator. Default to '.'
        :return: the names joined with the separator
        """
        _sep = sep if sep is not None else '.'
        return _sep.join(map(str, names))

    @classmethod
    def _remove_all(cls):
        with cls.__lock:
            cls.__properties.clear()

    @classmethod
    def _add_value(cls, key, value, root):
        if key is None:
            return
        for k, v in value.items():
            if isinstance(v, dict) and k in root[key]:
                cls._add_value(k, v, root[key])
            else:
                with cls.__lock:
                    if k in root[key] and isinstance(root[key][k], dict):
                        root[key][k].update(v)
                    else:
                        if k not in root[key] and not isinstance(root[key], dict):
                            root[key] = {}
                        root[key][k] = v
        return
