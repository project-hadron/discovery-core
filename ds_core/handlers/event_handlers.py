import pyarrow as pa
from typing import Dict

from ds_core.components.core_commons import CoreCommons
from ds_core.properties.decorator_patterns import singleton
from ds_core.handlers.abstract_handlers import AbstractSourceHandler, AbstractPersistHandler
from ds_core.handlers.abstract_handlers import ConnectorContract


class EventController(object):

    __book_catalog: Dict[str, pa.Table] = dict()

    @singleton
    def __new__(cls):
        return super().__new__(cls)

    @property
    def event_book_names(self) -> list:
        """Returns the list of event book references in the catalog"""
        return list(self.__book_catalog.keys())

    def is_event_book(self, book_name: str) -> bool:
        """Checks if a book_name reference exists in the book catalog"""
        if book_name in self.event_book_names:
            return True
        return False

    def add_event_book(self, book_name: str, event: pa.Table):
        """Returns the event book instance for the given reference name"""
        if self.is_event_book(book_name=book_name):
            raise ValueError(f"The book name '{book_name}' already exists in the catalog and does not need to be added")
        self.__book_catalog[book_name] = event

    def update_event_book(self, book_name: str, event: pa.Table):
        """Returns the event book instance for the given reference name"""
        self.__book_catalog.update({book_name: event})
        return self.is_event_book(book_name)


    def remove_event_books(self, book_names: [str, list]) -> bool:
        """removes the event book"""
        book_names = CoreCommons.list_formatter(book_names)
        for book in book_names:
            if self.is_event_book(book):
                self.__book_catalog.pop(book)
        return True

    def get_event(self, book_name: str, drop:bool=None) -> pa.Table:
        if self.is_event_book(book_name=book_name):
            if isinstance(drop, bool) and drop:
                return self.__book_catalog.pop(book_name)
            return self.__book_catalog.get(book_name)
        raise ValueError(f"The book name '{book_name}' can not be found in the catalog")


class EventSourceHandler(AbstractSourceHandler):
    """ PyArrow read only Source Handler. """

    def __init__(self, connector_contract: ConnectorContract):
        """ initialise the Handler passing the connector_contract dictionary """
        super().__init__(connector_contract)
        self.book_name = connector_contract.netloc
        self.event_books = EventController()
        self._file_state = 0
        self._changed_flag = True

    def supported_types(self) -> list:
        """ The source types supported with this module"""
        return ['EventBookController']

    def load_canonical(self, drop:bool=None, **kwargs) -> pa.Table:
        """ returns the canonical dataset based on the connector contract. """
        self.reset_changed()
        return self.event_books.get_event(self.book_name, drop=drop)

    def exists(self) -> bool:
        """ Returns True is the file exists """
        self.event_books.is_event_book(self.book_name)

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
            return self.event_books.update_event_book(_book_name, canonical)
        raise LookupError(f'The schema must be event, {_schema} given')

    def remove_canonical(self) -> bool:
        if not isinstance(self.connector_contract, ConnectorContract):
            return False
        self.event_books.remove_event_books(self.book_name)
