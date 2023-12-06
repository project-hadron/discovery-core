import importlib.util
import os
import re
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlparse, urlunparse, urlencode
from abc import ABC, abstractmethod
from typing import Any

__author__ = 'Darryl Oatridge'


class ConnectorContract(object):
    """ a container class for Connector Contract"""
    raw_uri: str = None
    raw_module_name: str = None
    raw_handler: str = None
    raw_kwargs: dict = None
    raw_version: str = None

    def __init__(self, uri: str,  module_name: str, handler: str, version: str=None, **kwargs):
        """ initialisation of the Connector Contract. Though not required, the URI can be considered as a
        URL of the form 'scheme://netloc/path;parameters?query#fragment' Following the syntax specifications
        in RFC 1808. This allows the use of the helper method `parse_uri` and static method `parse_params`

        :param uri: A Uniform Resource Identifier that unambiguously identifies a particular resource
        :param module_name: the module or package name where the handler can be found
        :param handler: the handler for retrieving the resource
        :param version: a version number to pass to the connector
        :param kwargs: (optional) key word arguments to be passed to the handler.
        """
        if not isinstance(uri, str) or len(uri) == 0:
            raise ValueError("The uri must be a valid string")
        self.raw_uri = uri
        self.raw_module_name = module_name
        self.raw_handler = handler
        self.raw_version = version if isinstance(version, str) else "0.0.1"
        self.raw_kwargs = kwargs if isinstance(kwargs, dict) else {}

    @property
    def uri(self) -> str:
        _parsed = self._format_uri(uri_raw=self.raw_uri, version=self.version)
        return self.parse_environ(_parsed)

    @property
    def module_name(self) -> str:
        return self.parse_environ(self.raw_module_name)

    @property
    def handler(self) -> str:
        return self.parse_environ(self.raw_handler)

    @property
    def kwargs(self) -> dict:
        """copy of the private kwargs dictionary"""
        _kwargs = self.raw_kwargs.copy() if isinstance(self.raw_kwargs, dict) else {}
        return self.parse_environ(_kwargs)

    @property
    def version(self) -> str:
        return self.parse_environ(self.raw_version)

    @property
    def path(self) -> str:
        return urlparse(self.uri).path

    @property
    def address(self) -> str:
        return self.parse_address(uri=self.uri, with_credentials=True, with_port=True)

    @property
    def query(self) -> dict:
        """copy of the private query dictionary"""
        _query = dict(parse_qsl(urlparse(self.uri).query))
        if isinstance(_query, dict):
            return _query.copy()
        return {}

    @property
    def schema(self) -> str:
        return urlparse(self.uri).scheme

    @property
    def netloc(self) -> str:
        return urlparse(self.uri).netloc

    @property
    def username(self) -> str:
        return urlparse(self.uri).username

    @property
    def password(self) -> str:
        return urlparse(self.uri).password

    @property
    def hostname(self) -> str:
        return urlparse(self.uri).hostname

    @property
    def port(self) -> int:
        return urlparse(self.uri).port

    @property
    def fragment(self) -> str:
        return urlparse(self.uri).fragment

    @property
    def params(self) -> list:
        """copy of the private params list"""
        _params = urlparse(self.uri).params
        return _params.split(sep=';').copy() if len(_params) > 0 else list()

    def get_key_value(self, key: str, default: Any=None) -> Any:
        """ returns the value for the key in the kwargs or query dictionaries.
        If the key is found in both then the query value is returned

        :param key: the key to look for
        :param default: a default value to return if not found
        :return: the value of the key or the default value if key is not found
        """
        value = self.raw_kwargs.get(key, default)
        return self.query.get(key, value)

    @staticmethod
    def _format_uri(uri_raw: str, version: str):
        """The URI with any modifications"""
        pattern = r'\${([A-Za-z_0-9\-]+)}'
        uri_tags = re.findall(pattern, uri_raw)
        if len(uri_tags) == 0:
            return uri_raw
        tags_dict = ConnectorContract._uri_tag_dict(version)
        pattern = r'\${([A-Za-z_0-9\-]+)}'
        return re.sub(pattern, lambda m: tags_dict.get(m.group(1), "${" + m.group(1) + "}"), uri_raw)

    @staticmethod
    def _uri_tag_dict(version: str) -> dict:
        """returns a dictionary of URI tags and their substitute"""
        return {'VERSION': f"_{version}",
                'TO_DAYS': datetime.now().strftime("_%Y%m%d"),
                'TO_HOURS': datetime.now().strftime("_%Y%m%d%H"),
                'TO_MINUTES': datetime.now().strftime("_%Y%m%d%H%M"),
                'TO_SECONDS': datetime.now().strftime("_%Y%m%d%H%M%S"),
                'TO_NS': datetime.now().strftime("_%Y%m%d%H%M%S%f")}

    @staticmethod
    def uri_tags() -> list:
        """returns the list of valid uri substitute tags"""
        return list(ConnectorContract._uri_tag_dict(version='').keys())

    @staticmethod
    def parse_environ(parse: [str, dict]):
        """parse a string replacing environment variables in the path"""
        pattern = r'\${([A-Za-z_0-9\-]+)}'
        if isinstance(parse, str):
            for label in re.findall(pattern, parse):
                if label not in os.environ.keys():
                    raise EnvironmentError(f"when parsing the connector attribute '{parse}' The environment "
                                           f"variable '{label}' was referenced but not set in the environment")
            return re.sub(pattern, lambda m: os.getenv(m.group(1), parse), parse)
        if isinstance(parse, dict):
            for key, value in parse.items():
                for label in re.findall(pattern, f"{key}{value}"):
                    if label not in os.environ.keys():
                        raise EnvironmentError(f"when parsing key '{key}', value '{value}' The environment "
                                               f"variable '{label}' was referenced but not set in the environment")

                key = re.sub(pattern, lambda m: os.getenv(m.group(1), key), key) if isinstance(key, str) else key
                value = re.sub(pattern,
                               lambda m: os.getenv(m.group(1), value), value) if isinstance(value, str) else value
                parse.update({key: value})
        return parse

    @staticmethod
    def parse_address_elements(uri: str, with_credentials: bool=None, with_port: bool=None) -> tuple:
        """ utility method to extract the address elements (schema, netloc, path) from a URI.
        Optionally the credentials and/or port can be excluded from the netloc

        :param uri: the URI to parse
        :param with_credentials: (optional) if to include the credentials. Default is True
        :param with_port: (optional) if to include the port. Default is True
        :return: a tuple of (schema, netloc, path)
        """
        _address = ConnectorContract.parse_address(uri=uri, with_credentials=with_credentials, with_port=with_port)
        parse_address = urlparse(_address)
        return tuple([parse_address.scheme, parse_address.netloc, parse_address.path])

    @staticmethod
    def parse_query(uri: str) -> dict:
        """ utility method to extract the query element from a URI

        :param uri: the URI to parse
        :return:
        """
        parse_url = urlparse(uri)
        _query = dict(parse_qsl(parse_url.query))
        return _query

    @staticmethod
    def parse_address(uri: str, with_credentials: bool=None, with_port: bool=None) -> str:
        """ utility method to extract the address from a URI, removing params, query and fragment. optionally
        the credentials and port can be excluded

        :param uri: the URI to parse
        :param with_credentials: (optional) if to include the credentials. Default is True
        :param with_port: (optional) if to include the port. Default is True
        :return: the full address string
        """
        with_credentials = with_credentials if isinstance(with_credentials, bool) else True
        with_port = with_port if isinstance(with_port, bool) else True
        if uri is None or not uri:
            raise ValueError("The uri must be a valid string with a length greater than 0")
        parse_url = urlparse(uri)
        _netloc = parse_url.hostname
        if with_credentials and isinstance(parse_url.username, str) and isinstance(parse_url.password, str):
            _credentials = ":".join([parse_url.username, parse_url.password])
            _netloc = '@'.join([_credentials, _netloc])
        if with_port and isinstance(parse_url.port, int):
            _netloc = ':'.join([_netloc, str(parse_url.port)])
        return urlunparse((parse_url.scheme, _netloc, parse_url.path, '', '', ''))

    @staticmethod
    def unparse_address(scheme: str, netloc: str, path: str, params: str=None, query: str=None, fragment: str=None):
        """ returns reconstructed URI from the parsed elements"""
        params = params if isinstance(params, str) else ''
        query = query if isinstance(query, str) else ''
        fragment = fragment if isinstance(fragment, str) else ''
        return urlunparse((scheme, netloc, path, params, query, fragment))

    @staticmethod
    def encode_query(**kwargs):
        """given kwargs, synthesize a query string"""
        return urlencode(kwargs)

    def to_dict(self) -> dict:
        """Returns a dictionary representation of the Connector Contract"""
        uri_dict = {'address': self.address, 'schema': self.schema, 'netloc': self.netloc, 'path': self.path,
                    'params': self.params, 'query': self.query, 'fragment': self.fragment}
        for attr in ['username', 'password', 'hostname', 'port']:
            attr_value = eval('self.{}'.format(attr))
            if attr_value is not None:
                uri_dict.update({attr: attr_value})
        rtn_dict = {'uri': self.uri, 'uri_parsed': uri_dict, 'module_name': self.module_name,
                    'handler': self.handler, 'version': self.version, 'kwargs': self.kwargs}
        return rtn_dict

    def to_raw_dict(self) -> dict:
        """Returns a dictionary representation of the Connector Contract"""
        rtn_dict = {'raw_uri': self.raw_uri, 'raw_module_name': self.raw_module_name, 'raw_handler': self.raw_handler,
                    'raw_version': self.raw_version, 'raw_kwargs': self.raw_kwargs}
        return rtn_dict

    @staticmethod
    def parse_ini(config_name: str=None, section: str=None):
        config_name = config_name if isinstance(config_name, str) else '~/.commons.ini'
        config_name = Path(os.path.expanduser(config_name)).as_posix()
        if not os.path.exists(config_name):
            raise ValueError(f"The configuration file '{config_name}' does not exist or could not be opened.")
        section = section if isinstance(section, str) else 'default'
        # create a parser
        parser = ConfigParser()
        # read config file
        parser.read(config_name)
        # get section
        config = {}
        if parser.has_section(section):
            params = parser.items(section)
            for param in params:
                config[param[0]] = param[1]
        else:
            raise ValueError(f"Section '{section}' could not be found in the configuration file '{config_name}'")
        return config

    def __len__(self):
        return self.to_raw_dict().__len__()

    def __str__(self):
        return self.to_dict().__str__()

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.to_raw_dict().__str__()}"

    def __eq__(self, other):
        return self.to_raw_dict().__eq__(other.to_raw_dict())

    def __setattr__(self, key, value):
        if self.to_raw_dict().get(key, None) is None:
            super().__setattr__(key, value)
        else:
            raise AttributeError("The attribute '{}' is immutable once set and can not be changed".format(key))

    def __delattr__(self, item):
        raise AttributeError("{} is an immutable class and attributes can't be removed".format(self.__class__.__name__))


class AbstractSourceHandler(ABC):

    def __init__(self, connector_contract: ConnectorContract):
        self._contract = connector_contract

    @property
    def connector_contract(self) -> ConnectorContract:
        return self._contract

    def set_connector_contract(self, source_contract: ConnectorContract):
        self._contract = source_contract

    @abstractmethod
    def supported_types(self) -> list:
        pass

    @abstractmethod
    def exists(self) -> bool:
        pass

    @abstractmethod
    def has_changed(self) -> bool:
        pass

    @abstractmethod
    def reset_changed(self, changed: bool=False):
        pass

    @abstractmethod
    def load_canonical(self, **kwargs) -> Any:
        pass


class AbstractPersistHandler(AbstractSourceHandler):

    @abstractmethod
    def persist_canonical(self, canonical: Any, **kwargs) -> bool:
        pass

    @abstractmethod
    def remove_canonical(self, **kwargs) -> bool:
        pass

    @abstractmethod
    def backup_canonical(self, canonical: Any, uri: str, **kwargs) -> bool:
        """ creates a backup of the canonical to an alternative uri

        :param canonical: the canonical to back up
        :param uri: an alternative uri to the one in the ConnectorContract
        :param kwargs: if given, these kwargs are used as a replacement of the connector kwargs
        :return: True if successful
        """
        pass


class HandlerFactory(object):

    @staticmethod
    def check_module(module_name: str) -> bool:
        module_spec = importlib.util.find_spec(module_name)
        if module_spec is None:
            return False
        return True

    @staticmethod
    def check_handler(module_name: str, handler: str):
        try:
            module_spec = importlib.util.find_spec(module_name)
        except ModuleNotFoundError:
            return False
        if module_spec is None:
            return False
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        if handler not in dir(module):
            return False
        return True

    @staticmethod
    def get_module(module_name: str):
        module_spec = importlib.util.find_spec(module_name)
        if module_spec is None:
            raise ModuleNotFoundError(f"The module '{module_name}' could not be found")
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        return module

    @staticmethod
    def instantiate(connector_contract: ConnectorContract) -> [AbstractSourceHandler, AbstractPersistHandler]:
        module_name = connector_contract.module_name
        handler = connector_contract.handler

        # check module
        module_spec = importlib.util.find_spec(module_name)
        if module_spec is None:
            raise ModuleNotFoundError(f"The module '{module_name}' could not be found")

        # check handler
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        if handler not in dir(module):
            raise ImportError(f"The handler '{handler}' could not be found in the module '{module_name}'")

        # create instance of handler
        local_kwargs = locals().get('kwargs') if 'kwargs' in locals() else dict()
        local_kwargs['module'] = module
        local_kwargs['connector_contract'] = connector_contract
        instance = eval(f'module.{handler}(connector_contract)', globals(), local_kwargs)
        if not isinstance(instance, (AbstractSourceHandler, AbstractPersistHandler)):
            raise TypeError(f"The handler '{handler}' in package {module_name} could not be instanciated as a handler")
        return instance
