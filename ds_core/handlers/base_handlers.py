import io
import requests
import os
from contextlib import closing
import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import json
from pyarrow import csv
from ds_core.components.core_commons import CoreCommons as Commons
from ds_core.handlers.abstract_handlers import AbstractSourceHandler, AbstractPersistHandler
from ds_core.handlers.abstract_handlers import ConnectorContract, HandlerFactory

__author__ = 'Darryl Oatridge'


class BaseSourceHandler(AbstractSourceHandler):
    """ Base PyArrow read only Source Handler. """

    def __init__(self, connector_contract: ConnectorContract):
        """ initialise the Handler passing the connector_contract dictionary """
        super().__init__(connector_contract)
        self._file_state = 0
        self._changed_flag = True

    def supported_types(self) -> list:
        """ The source types supported with this module"""
        return ['parquet', 'csv', 'json', 'yaml']

    def load_canonical(self, **kwargs) -> pa.Table:
        """ returns the canonical dataset based on the connector contract. """
        if not isinstance(self.connector_contract, ConnectorContract):
            raise ValueError("The Connector Contract was not been set at initialisation or is corrupted")
        _cc = self.connector_contract
        load_params = kwargs
        load_params.update(_cc.kwargs)  # Update with any kwargs in the Connector Contract
        if load_params.pop('use_full_uri', False):
            file_type = load_params.pop('file_type', 'csv')
            address = _cc.uri
        else:
            load_params.update(_cc.query)  # Update kwargs with those in the uri query
            _, _, _ext = _cc.address.rpartition('.')
            address = _cc.address
            file_type = load_params.pop('file_type', _ext if len(_ext) > 0 else 'csv')
        self.reset_changed()
        # parquet
        if file_type.lower() in ['parquet', 'pqt', 'pq']:
            if _cc.schema.startswith('http'):
                address = io.BytesIO(requests.get(address).content)
            return pq.read_table(address, **load_params)
        # csv
        if file_type.lower() in ['csv', 'gz', 'bz2']:
            _kwargs = {**_cc.query, **_cc.kwargs, **load_params}
            parse_options = _kwargs.get('parse_options', {}).get('parse_options', {})
            parse_options = self.parse_options(**parse_options)
            read_options = _kwargs.get('read_options', {}).get('read_options', {})
            read_options = self.read_options(**read_options)
            if _cc.schema.startswith('http'):
                address = io.BytesIO(requests.get(address).content)
            return csv.read_csv(address, parse_options=parse_options, read_options=read_options)
        # json
        if file_type.lower() in ['json']:
            data =  self._json_load(path_file=address, **load_params)
            if isinstance(data, dict):
                data = [data]
            data = pa.Table.from_pylist(data)
            return Commons.table_flatten(data)
        if file_type.lower() in ['yml', 'yaml']:
            data = self._yaml_load(path_file=address, **load_params)
            return pa.Table.from_pydict(data)
        raise LookupError('The source format {} is not currently supported'.format(file_type))

    def exists(self) -> bool:
        """ Returns True is the file exists """
        if not isinstance(self.connector_contract, ConnectorContract):
            raise ValueError("The Connector Contract has not been set")
        _cc = self.connector_contract
        if _cc.schema.startswith('http'):
            r = requests.get(_cc.address)
            if r.status_code == 200:
                return True
        if os.path.exists(_cc.address):
            return True
        return False

    def has_changed(self) -> bool:
        """ returns the status of the change_flag indicating if the file has changed since last load or reset"""
        if not self.exists():
            return False
        # maintain the change flag
        _cc = self.connector_contract
        if _cc.schema.startswith('http') or _cc.schema.startswith('git'):
            if not isinstance(self.connector_contract, ConnectorContract):
                raise ValueError("The Pandas Connector Contract has not been set")
            module_name = 'requests'
            _address = _cc.address.replace("git://", "https://")
            if HandlerFactory.check_module(module_name=module_name):
                module = HandlerFactory.get_module(module_name=module_name)
                state = module.head(_address).headers.get('last-modified', 0)
            else:
                raise ModuleNotFoundError(f"The required module {module_name} has not been installed. Please pip "
                                          f"install the appropriate package in order to complete this action")
        else:
            state = os.stat(_cc.address).st_mtime_ns
        if state != self._file_state:
            self._changed_flag = True
            self._file_state = state
        return self._changed_flag

    def reset_changed(self, changed: bool = False):
        """ manual reset to say the file has been seen. This is automatically called if the file is loaded"""
        changed = changed if isinstance(changed, bool) else False
        self._changed_flag = changed

    @staticmethod
    def _json_load(path_file: str, **kwargs) -> [dict, pa.Table]:
        """ loads a json file """
        if path_file.startswith('http'):
            username = kwargs.get('username', None)
            password = kwargs.get('password', None)
            auth = (username, password) if username and password else None
            r = requests.get(path_file, auth=auth)
            return r.json()
        with closing(open(path_file, mode='r')) as f:
            return json.load(f, **kwargs)

    @staticmethod
    def _yaml_load(path_file, **kwargs) -> dict:
        """ loads the YAML file"""
        module_name = 'yaml'
        if HandlerFactory.check_module(module_name=module_name):
            module = HandlerFactory.get_module(module_name=module_name)
        else:
            raise ModuleNotFoundError(f"The required module {module_name} has not been installed. "
                                      f"Please pip install the appropriate package in order to complete this action")
        encoding = kwargs.pop('encoding', 'utf-8')
        try:
            with closing(open(path_file, mode='r', encoding=encoding)) as yml_file:
                rtn_dict = module.safe_load(yml_file)
        except IOError as e:
            raise IOError(f"The yaml file {path_file} failed to open with: {e}")
        if not isinstance(rtn_dict, dict) or not rtn_dict:
            raise TypeError(f"The yaml file {path_file} could not be loaded as a dict type")
        return rtn_dict

    @staticmethod
    def read_options(**kwargs) -> csv.ReadOptions:
        if kwargs is None or not kwargs:
            return None
        return csv.ReadOptions(**kwargs)

    @staticmethod
    def parse_options(**kwargs) -> csv.ParseOptions:
        if kwargs is None or not kwargs:
            return None
        return csv.ParseOptions(**kwargs)


class BasePersistHandler(BaseSourceHandler, AbstractPersistHandler):
    """ Base PyArrow read/write Persist Handler. """

    def persist_canonical(self, canonical: pa.Table, **kwargs) -> bool:
        """ persists the canonical dataset

        Extra Parameters in the ConnectorContract kwargs:
            - file_type: (optional) the type of the source file. if not set, inferred from the file extension
        """
        if not isinstance(self.connector_contract, ConnectorContract):
            return False
        _uri = self.connector_contract.uri
        return self.backup_canonical(uri=_uri, canonical=canonical, **kwargs)

    def backup_canonical(self, canonical: pa.Table, uri: str, **kwargs) -> bool:
        """ creates a backup of the canonical to an alternative URI

        Extra Parameters in the ConnectorContract kwargs:
            - file_type: (optional) the type of the source file. if not set, inferred from the file extension
            - write_params (optional) a dictionary of additional write parameters directly passed to 'write_' methods
        """
        if not isinstance(self.connector_contract, ConnectorContract):
            return False
        _cc = self.connector_contract
        _address = _cc.parse_address(uri=uri)
        persist_params = kwargs if isinstance(kwargs, dict) else _cc.kwargs
        persist_params.update(_cc.parse_query(uri=uri))
        _, _, _ext = _address.rpartition('.')
        if not self.connector_contract.schema.startswith('http'):
            _path, _ = os.path.split(_address)
            if len(_path) > 0 and not os.path.exists(_path):
                os.makedirs(_path)
        file_type = persist_params.pop('file_type', _ext if len(_ext) > 0 else 'parquet')
        write_params = persist_params.pop('write_params', {})
        # parquet
        if file_type.lower() in ['pq', 'pqt', 'parquet']:
            pq.write_table(canonical, _address, **write_params)
            return True
        # csv
        if file_type.lower() in ['csv', 'gz', 'bz2']:
            for n in canonical.column_names:
                c = canonical.column(n).combine_chunks()
                if pa.types.is_dictionary(c.type):
                    dc = c.dictionary_decode()
                    canonical = Commons.table_append(canonical, pa.table([dc], names=[n]))
                if pa.types.is_nested(c.type):
                    sc = pa.Array.from_pandas(pa.Array.to_pandas(c).astype(str))
                    canonical = Commons.table_append(canonical, pa.table([sc], names=[n]))
            csv.write_csv(canonical, _address, **write_params)
            return True
        # json
        if file_type.lower() in ['json']:
            cfg_dict = Commons.table_nest(canonical)
            with closing(open(_address, mode='w')) as f:
                json.dump(cfg_dict, f, cls=NpEncoder, **kwargs)
            return True
        # yaml
        if file_type.lower() in ['yml', 'yaml']:
            cfg_dict = canonical.to_pydict()
            self._yaml_dump(data=cfg_dict, path_file=_address, **write_params)
            return True
        # not found
        raise LookupError('The file format {} is not currently supported for write'.format(file_type))

    def remove_canonical(self) -> bool:
        if not isinstance(self.connector_contract, ConnectorContract):
            return False
        _cc = self.connector_contract
        if self.connector_contract.schema.startswith('http'):
            raise NotImplemented("Remove Canonical does not support {} schema based URIs".format(_cc.schema))
        if os.path.exists(_cc.address):
            os.remove(_cc.address)
            return True
        return False

    @staticmethod
    def _yaml_dump(data, path_file, **kwargs) -> None:
        """ dump YAML file

        :param data: the data to persist
        :param path_file: the name and path of the file
        :param default_flow_style: (optional) if to include the default YAML flow style
        """
        module_name = 'yaml'
        if HandlerFactory.check_module(module_name=module_name):
            module = HandlerFactory.get_module(module_name=module_name)
        else:
            raise ModuleNotFoundError(f"The required module {module_name} has not been installed. "
                                      f"Please pip install the appropriate package in order to complete this action")
        encoding = kwargs.pop('encoding', 'utf-8')
        default_flow_style = kwargs.pop('default_flow_style', False)
        # make sure the dump is clean
        try:
            with closing(open(path_file, mode='w', encoding=encoding)) as yml_file:
                module.safe_dump(data=data, stream=yml_file, default_flow_style=default_flow_style, **kwargs)
        except IOError as e:
            raise IOError(f"The yaml file {path_file} failed to open with: {e}")
        # check the file was created
        return


class NpEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.datetime64):
            return np.datetime_as_string(obj, unit='s')
        elif isinstance(obj, pd.Timestamp):
            return np.datetime_as_string(obj.to_datetime64(), unit='s')
        else:
            return super(NpEncoder, self).default(obj)
