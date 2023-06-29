import os
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.feather as feather
from pyarrow import csv
from pyarrow import json

from ds_core.handlers.abstract_handlers import AbstractSourceHandler, AbstractPersistHandler
from ds_core.handlers.abstract_handlers import ConnectorContract

__author__ = 'Darryl Oatridge'


class PyarrowSourceHandler(AbstractSourceHandler):
    """ PyArrow read only Source Handler. """

    def __init__(self, connector_contract: ConnectorContract):
        """ initialise the Handler passing the connector_contract dictionary """
        super().__init__(connector_contract)

    def supported_types(self) -> list:
        """ The source types supported with this module"""
        return ['parquet', 'feather', 'csv', 'json']

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
            return pq.read_table(address, **load_params)
        # feathers
        if file_type.lower() in ['feather']:
            return feather.read_table(address, **load_params)
        # csv
        if file_type.lower() in ['gzip', 'zip', 'tar', 'csv', 'tsv', 'txt']:
            return csv.read_csv(address, **load_params)
        # json
        if file_type.lower() in ['json']:
            return json.read_json(address, **load_params)
        raise LookupError('The source format {} is not currently supported'.format(file_type))

    def exists(self) -> bool:
        return True

    def has_changed(self) -> bool:
        return True

    def reset_changed(self, changed: bool = False):
        pass

class PyarrowPersistHandler(PyarrowSourceHandler, AbstractPersistHandler):
    """ PyArrow read/write Persist Handler. """

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
        # feather
        if file_type.lower() in ['feather']:
            feather.write_feather(canonical, _address, **write_params)
            return True
        # csv
        if file_type.lower() in ['csv', 'tsv', 'txt']:
            csv.write_csv(canonical, _address, **write_params)
            return True
        # not found
        raise LookupError('The file format {} is not currently supported for write'.format(file_type))

    def remove_canonical(self) -> bool:
        return False
