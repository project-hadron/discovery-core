import threading
import pyarrow as pa
from typing import Dict

from ds_core.properties.decorator_patterns import singleton
from ds_core.handlers.abstract_handlers import AbstractSourceHandler, AbstractPersistHandler
from ds_core.handlers.abstract_handlers import ConnectorContract

class EventManager(object):

    __event_catalog: Dict[str, pa.Table]

    def __init__(self):
        self.__event_catalog = dict()
        self.__lock = threading.Lock()

    def event_names(self) -> list:
        return list(self.__event_catalog.keys())

    def is_event(self, name: str):
        return name in self.__event_catalog

    def get(self, name: str) -> pa.Table:
        if name in self.__event_catalog:
            return self.__event_catalog[name]

    def set(self, name: str, event: pa.Table):
        if name in self.__event_catalog:
            raise ValueError(f"The event name '{name}' already exists in the event catalog and does not need to be added")
        with self.__lock:
            self.__event_catalog[name] = event

    def update(self, name: str, event: pa.Table):
        with self.__lock:
            self.__event_catalog.update({name: event})

    def delete(self, name: str):
        with self.__lock:
            del self.__event_catalog[name]

    def reset(self):
        with self.__lock:
            self.__event_catalog = {}
        return self

    def to_pydict(self):
        rtn_dict = {}
        for event, tbl in self.__event_catalog.items():
            rtn_dict[event] = {} if tbl is None else tbl.to_pydict()
        return rtn_dict

    def __repr__(self):
        rtn_str = ""
        for event, tbl in self.__event_catalog.items():
            if tbl is None:
                rtn_str += f"\nEvent: {event} (0,0)\n\t-Empty-,"
            else:
                schema = tbl.schema.to_string().replace('\n', '\n\t')
                rtn_str += f"\nEvent: {event} ({tbl.num_rows},{tbl.num_columns})\n\t{schema},"
        return rtn_str

    def __str__(self):
        rtn_str = "EventBooks: ["
        for event, tbl in self.__event_catalog.items():
            if tbl is None:
                rtn_str += f"\n\t{event}: ^(0, 0)> -Empty-,"
            else:
                rtn_str += f"\n\t{event}: ^{tbl.shape}> {tbl.column_names},"
        return rtn_str + '\n]'


class EventSourceHandler(AbstractSourceHandler):
    """ PyArrow read only Source Handler. """

    _event_manager = EventManager()

    @singleton
    def __new__(cls, connector_contract: ConnectorContract):
        return super().__new__(cls)

    def __init__(self, connector_contract: ConnectorContract):
        """ initialise the Handler passing the connector_contract dictionary """
        super().__init__(connector_contract)
        self._event_name = connector_contract.netloc
        self._file_state = 0
        self._changed_flag = True

    @property
    def event_manager(self):
        return self._event_manager

    @property
    def event_name(self):
        return self._event_name

    def supported_types(self) -> list:
        """ The source types supported with this module"""
        return ['EventBookController']

    def load_canonical(self, drop:bool=None, **kwargs) -> pa.Table:
        """ returns the canonical dataset based on the connector contract. """
        drop = drop if isinstance(drop, bool) else False
        self.reset_changed()
        if self._event_manager.is_event(self._event_name):
            rtn_tbl = self._event_manager.get(self._event_name)
            if isinstance(drop, bool) and drop:
                self._event_manager.delete(self._event_name)
            return rtn_tbl
        raise ValueError(f"The event '{self._event_name}' does not exist")

    def exists(self) -> bool:
        """ Returns True is the file exists """
        return self._event_manager.is_event(self._event_name)

    def has_changed(self) -> bool:
        """ returns the status of the change_flag indicating if the file has changed since last load or reset"""
        return self.has_changed()

    def reset_changed(self, changed: bool=None):
        """ manual reset to say the file has been seen. This is automatically called if the file is loaded"""
        changed = changed if isinstance(changed, bool) else False
        self._changed_flag = changed


class EventPersistHandler(EventSourceHandler, AbstractPersistHandler):
    """ Event read/write Persist Handler. """

    def persist_canonical(self, canonical: pa.Table, **kwargs) -> bool:
        """ persists the canonical dataset """
        if not isinstance(self.connector_contract, ConnectorContract):
            return False
        _uri = self.connector_contract.uri
        return self.backup_canonical(uri=_uri, canonical=canonical, **kwargs)

    def backup_canonical(self, canonical: pa.Table, uri: str, **kwargs) -> bool:
        """ creates a backup of the canonical to an alternative URI """
        _schema, _book_name, _ = ConnectorContract.parse_address_elements(uri=uri)
        if _schema == 'event':
            self.reset_changed(True)
            return self._event_manager.update(_book_name, canonical)
        raise LookupError(f'The schema must be event, {_schema} given')

    def remove_canonical(self) -> bool:
        if not isinstance(self.connector_contract, ConnectorContract):
            return False
        return self._event_manager.delete(self._event_name)
