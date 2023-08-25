import threading
import pyarrow as pa
from typing import Dict

from ds_core.properties.decorator_patterns import singleton
from ds_core.handlers.abstract_handlers import AbstractSourceHandler, AbstractPersistHandler
from ds_core.handlers.abstract_handlers import ConnectorContract

class EventManager(object):

    __event_catalog: Dict[str, pa.Table] = dict()
    __lock = threading.Lock()

    @singleton
    def __new__(cls):
        return super().__new__(cls)

    @classmethod
    def event_names(cls) -> list:
        return list(cls.__event_catalog.keys())

    @classmethod
    def is_event(cls, name: str):
        return name in cls.__event_catalog

    @classmethod
    def get(cls, name: str) -> pa.Table:
        if name in cls.__event_catalog:
            return cls.__event_catalog[name]

    @classmethod
    def set(cls, name: str, event: pa.Table):
        if name in cls.__event_catalog:
            raise ValueError(f"The event name '{name}' already exists in the event catalog and does not need to be added")
        with cls.__lock:
            cls.__event_catalog[name] = event

    @classmethod
    def update(cls, name: str, event: pa.Table):
        with cls.__lock:
            cls.__event_catalog.update({name: event})

    @classmethod
    def delete(cls, name: str):
        with cls.__lock:
            del cls.__event_catalog[name]


class EventSourceHandler(AbstractSourceHandler):
    """ PyArrow read only Source Handler. """

    def __init__(self, connector_contract: ConnectorContract):
        """ initialise the Handler passing the connector_contract dictionary """
        super().__init__(connector_contract)
        self.event_name = connector_contract.netloc
        self._file_state = 0
        self._changed_flag = True

    def supported_types(self) -> list:
        """ The source types supported with this module"""
        return ['EventBookController']

    def load_canonical(self, drop:bool=None, **kwargs) -> pa.Table:
        """ returns the canonical dataset based on the connector contract. """
        self.reset_changed()
        em = EventManager()
        rtn_tbl = em.get(self.event_name)
        if isinstance(drop, bool) and drop:
            em.delete(self.event_name)
        return rtn_tbl

    def exists(self) -> bool:
        """ Returns True is the file exists """
        return EventManager().is_event(self.event_name)

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
            return EventManager().update(_book_name, canonical)
        raise LookupError(f'The schema must be event, {_schema} given')

    def remove_canonical(self) -> bool:
        if not isinstance(self.connector_contract, ConnectorContract):
            return False
        return EventManager().delete(self.event_name)
