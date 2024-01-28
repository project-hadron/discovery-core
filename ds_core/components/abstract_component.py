import os
import platform
from abc import ABC, abstractmethod
from typing import Any

from ds_core.components.core_commons import CoreCommons

from ds_core.intent.abstract_intent import AbstractIntentModel
from ds_core.properties.abstract_properties import AbstractPropertyManager
from ds_core.handlers.abstract_handlers import ConnectorContract, HandlerFactory
from ds_core.handlers.abstract_handlers import AbstractPersistHandler, AbstractSourceHandler

__author__ = 'Darryl Oatridge'


class AbstractComponent(ABC):
    """ Abstract AI Single Task Application Component (AI-STAC) component class provides all the basic building blocks
    of a components build including property management, augmented knowledge notes and parameterised intent pipeline.

    For convenience there are two Factory Initialisation methods available `from_env(...)` and `from_uri(...)` the
    second being an abstract method. This factory method initialises the concrete PropertyManager and IntentModel
    classes and should use the parent `_init_properties(...)` methods to set the properties connector.

    As an example concrete implementation of these methods:

    .. code-block:: py3

        @classmethod
        def from_uri(cls, task_name: str, uri_pm_path: str, username: str, uri_pm_repo: str=None,
                     pm_file_type: str=None, pm_module: str=None, pm_handler: str=None, pm_kwargs: dict=None,
                     default_save=None, reset_templates: bool=None, template_path: str=None, template_module: str=None,
                     template_source_handler: str=None, template_persist_handler: str=None, align_connectors: bool=None,
                     default_save_intent: bool=None, default_intent_level: bool=None, order_next_available: bool=None,
                     default_replace_intent: bool=None, has_contract: bool=None):
            pm_file_type = pm_file_type if isinstance(pm_file_type, str) else 'json'
            pm_module = pm_module if isinstance(pm_module, str) else cls.DEFAULT_MODULE
            pm_handler = pm_handler if isinstance(pm_handler, str) else cls.DEFAULT_PERSIST_HANDLER
            _pm = ExamplePropertyManager(task_name=task_name, username=username)
            _intent_model = ExampleIntentModel(property_manager=_pm, default_save_intent=default_save_intent,
                                               default_intent_level=default_intent_level,
                                               order_next_available=order_next_available,
                                               default_replace_intent=default_replace_intent)
            super()._init_properties(property_manager=_pm, uri_pm_path=uri_pm_path, default_save=default_save,
                                     uri_pm_repo=uri_pm_repo, pm_file_type=pm_file_type, pm_module=pm_module,
                                     pm_handler=pm_handler, pm_kwargs=pm_kwargs, has_contract=has_contract)
            return cls(property_manager=_pm, intent_model=_intent_model, default_save=default_save,
                       reset_templates=reset_templates, template_path=template_path, template_module=template_module,
                       template_source_handler=template_source_handler, template_persist_handler=template_persist_handler,
                       align_connectors=align_connectors)

    """

    # primary connectors
    CONNECTOR_SOURCE = 'primary_source'
    CONNECTOR_PERSIST = 'primary_persist'
    # report connectors
    REPORT_SCHEMA = 'primary_schema'
    REPORT_INTENT = 'intent'
    REPORT_NOTES = 'notes'
    REPORT_CONNECTORS = 'connectors'
    REPORT_RUNBOOK = 'runbook'
    REPORT_ENVIRON = 'environ'
    # default connectors module and handlers
    DEFAULT_MODULE = 'ds_capability.handlers.pyarrow_handlers'
    DEFAULT_SOURCE_HANDLER = 'PyarrowSourceHandler'
    DEFAULT_PERSIST_HANDLER = 'PyarrowPersistHandler'

    def __init__(self, property_manager: Any, intent_model: Any, default_save: bool=None, reset_templates: bool=None,
                 template_path: str = None, template_module: str = None, template_source_handler: str = None,
                 template_persist_handler: str = None, align_connectors: bool=None):
        """ initialisation of the abstract components providing both the property manager and the components
        parameterizable intent model. The optional parameters allow default references to be overridden by a
        concrete implementations of the abstract.
        The default module and handlers replace the root default static values for DEFAULT_MODULE,
        DEFAULT_SOURCE_HANDLER, DEFAULT_PERSIST_HANDLER and provide implementation specific default references but are
        also used in methods where the module and handlers are optional parameters.
        The default save allows a component to be run in memory or persisted as a default behaviour.

        :param property_manager: The contract property manager instance for this components
        :param intent_model: the model codebase containing the parameterizable intent
        :param default_save: (optional) The default behaviour of persisting the contracts:
                    - if True: all contract properties are persisted
                    - if False: The connector contracts are kept in memory (useful for restricted file systems)

        :param reset_templates: (optional) reset connector templates from environ variables. Default True
        :param template_path: (optional) a template path to use if the environment variable does not exist
        :param template_module: (optional) a template module to use if the environment variable does not exist
        :param template_source_handler: (optional) a template source handler to use if no environment variable
        :param template_persist_handler: (optional) a template persist handler to use if no environment variable
        :param align_connectors: (optional) resets aligned connectors to the template. default Default True
        """
        if not isinstance(property_manager, AbstractPropertyManager):
            raise ValueError("The contract_pm must be a concrete implementation of the AbstractPropertyManager")
        if not isinstance(intent_model, AbstractIntentModel):
            raise ValueError("The intent_model must be a concrete implementation of the AbstractIntent")
        # set instance references
        self._component_pm = property_manager
        self._intent_model = intent_model
        self._default_save = default_save if isinstance(default_save, bool) else True
        # align templates and connectors
        reset_templates = reset_templates if isinstance(reset_templates, bool) else True
        align_connectors = align_connectors if isinstance(align_connectors, bool) else True
        if reset_templates:
            # setup the templates values
            if os.access('./', os.W_OK | os.X_OK):
                _root = './'
            else:
                _root = os.environ['AppData'] if platform.system().lower().startswith("Windows") else '/tmp'
            _default_path = os.getenv('HADRON_DEFAULT_PATH') \
                if 'HADRON_DEFAULT_PATH' in os.environ else os.path.join(_root, 'hadron', 'data')
            _schema, _, _ = ConnectorContract.parse_address_elements(uri=_default_path)
            _default_module, _default_source, _default_persist = self._from_handler(_schema)
            template_path = template_path if isinstance(template_path, str) else _default_path
            template_module = template_module if isinstance(template_module, str) else _default_module
            template_source_handler = template_source_handler \
                if isinstance(template_source_handler, str) else _default_source
            template_persist_handler = template_persist_handler \
                if isinstance(template_persist_handler, str) else _default_persist
            if align_connectors:
                # remove existing
                if self.pm.has_connector(self.pm.TEMPLATE_SOURCE):
                    self.remove_connector_contract( self.pm.TEMPLATE_SOURCE)
                if self.pm.has_connector(self.pm.TEMPLATE_PERSIST):
                    self.remove_connector_contract( self.pm.TEMPLATE_PERSIST)
                # reset the template Connector Contracts
                scc = ConnectorContract(uri=template_path, module_name=template_module, handler=template_source_handler)
                self.add_connector_contract(connector_name=self.pm.TEMPLATE_SOURCE, connector_contract=scc)
                pcc = ConnectorContract(uri=template_path, module_name=template_module, handler=template_persist_handler)
                self.add_connector_contract(connector_name=self.pm.TEMPLATE_PERSIST, connector_contract=pcc)
                # reset the connector
                self.reset_template_connectors()
        # just make sure everything is persisted
        self.pm_persist()
        return

    @classmethod
    @abstractmethod
    def from_uri(cls, task_name: str, uri_pm_path: str, creator: str, uri_pm_repo: str=None, pm_file_type: str=None,
                 pm_module: str=None, pm_handler: str=None, pm_kwargs: dict=None, default_save=None,
                 reset_templates: bool=None, template_path: str=None, template_module: str=None,
                 template_source_handler: str=None, template_persist_handler: str=None, align_connectors: bool=None,
                 default_save_intent: bool=None, default_intent_level: bool=None, order_next_available: bool=None,
                 default_replace_intent: bool=None, has_contract: bool=None):
        """ Class Factory Method to instantiates the components application. The Factory Method handles the
        instantiation of the Properties Manager, the Intent Model and the persistence of the uploaded properties.
        See class inline docs for an example method

         :param task_name: The reference name that uniquely identifies a task or subset of the property manager
         :param uri_pm_path: A URI that identifies the resource path for the property manager.
         :param creator: A user name for this task activity.
         :param uri_pm_repo: (optional) A repository URI to initially load the property manager but not save to.
         :param pm_file_type: (optional) defines a specific file type for the property manager
         :param pm_module: (optional) the module or package name where the handler can be found
         :param pm_handler: (optional) the handler for retrieving the resource
         :param pm_kwargs: (optional) a dictionary of kwargs to pass to the property manager
         :param default_save: (optional) if the configuration should be persisted. default to 'True'
         :param reset_templates: (optional) reset connector templates from environ variables. Default True
         :param template_path: (optional) a template path to use if the environment variable does not exist
         :param template_module: (optional) a template module to use if the environment variable does not exist
         :param template_source_handler: (optional) a template source handler to use if no environment variable
         :param template_persist_handler: (optional) a template persist handler to use if no environment variable
         :param align_connectors: (optional) resets aligned connectors to the template. default Default True
         :param default_save_intent: (optional) The default action for saving intent in the property manager
         :param default_intent_level: (optional) the default level intent should be saved at
         :param order_next_available: (optional) if the default behaviour for the order should be next available order
         :param default_replace_intent: (optional) the default replace existing intent behaviour
         :param has_contract: (optional) indicates the instance should have a property manager domain contract
         :return: the initialised class instance
         """
        return cls

    @classmethod
    def _init_properties(cls, property_manager: AbstractPropertyManager, uri_pm_path: str, default_save: bool=None,
                         uri_pm_repo: str=None, pm_file_type: str=None, pm_module: str=None, pm_handler: str=None,
                         has_contract: bool=None, pm_kwargs: dict=None):
        """ initialisation and set up of the property connector contract into the property manager instance.
        This should be used as part of the component initialisation

        :param property_manager: the instance of the property manager
        :param uri_pm_path: the URI path to where property contract are help.
        :param default_save: (optional) if the configuration should be persisted. default to 'True'
        :param uri_pm_repo: The read only repo link that points to the raw data path to the contracts repo directory
        :param pm_file_type: (optional) defines a specific file type for the property manager
        :param pm_module: (optional) the module or package name where the handler can be found
        :param pm_handler: (optional) the handler for retrieving the resource
        :param has_contract: (optional) indicates the instance should have a property manager domain contract
        :param pm_kwargs: (optional) a dictionary of kwargs to pass to the property manager
        :return: a tuple of the selected pm_module_name, pm_handler and pm_file_type
        """
        if not isinstance(uri_pm_path, str) or len(uri_pm_path) == 0:
            raise ValueError("The URI must be a valid string representation of a URI")
        _schema, _netloc, _path = ConnectorContract.parse_address_elements(uri=uri_pm_path)
        _file_type = pm_file_type if isinstance(pm_file_type, str) else 'json'
        has_contract = has_contract if isinstance(has_contract, bool) else True
        default_save = default_save if isinstance(default_save, bool) else True
        if isinstance(pm_module, str) and isinstance(pm_handler, str):
            _module_name = pm_module
            _handler = pm_handler
        else:
            _module_name, _, _handler = cls._from_handler(schema=_schema)
            _address = ConnectorContract.parse_address(uri=uri_pm_path)
        _path = os.path.join(_path, property_manager.pm_file_pattern(file_type=_file_type))
        _prop_uri = ConnectorContract.unparse_address(scheme=_schema, netloc=_netloc, path=_path)
        _query_kw = ConnectorContract.parse_query(uri=uri_pm_path)
        kwargs = pm_kwargs if isinstance(pm_kwargs, dict) else {}
        kwargs.update(_query_kw)
        _connector = ConnectorContract(uri=_prop_uri, module_name=_module_name, handler=_handler,
                                       version=property_manager.version, **kwargs)
        # make a copy to set as the ongoing connector if repo is used
        _pm_connector = _connector
        property_manager.set_property_connector(connector_contract=_pm_connector)
        if isinstance(uri_pm_repo, str):
            _r_schema, _r_netloc, _r_path = ConnectorContract.parse_address_elements(uri=uri_pm_repo)
            _r_path = os.path.join(_r_path, property_manager.pm_file_pattern(file_type=_file_type))
            _r_prop_uri = ConnectorContract.unparse_address(scheme=_r_schema, netloc=_r_netloc, path=_r_path)
            _r_query_kw = ConnectorContract.parse_query(uri=uri_pm_repo)
            _connector = ConnectorContract(uri=_r_prop_uri, module_name=_module_name, handler=_handler,
                                           version=property_manager.version, **_r_query_kw)
        if HandlerFactory.instantiate(_connector).exists():
            if not has_contract:
                # if set to not have a contract then reset this contract
                property_manager.reset_all()
                property_manager.persist_properties(connector_contract=_pm_connector, only_branch=True)
                # reset to overwrite anything loaded
                property_manager.set_property_connector(connector_contract=_pm_connector)
            else:
                # set to the temporary property manager
                property_manager.set_property_connector(connector_contract=_connector)
                try:
                    property_manager.load_properties()
                except [KeyError, IOError]:
                    raise ConnectionError("Unable to retrieve the persisted properties, file might be corrupted "
                                          "or of a different format")
                # reset to overwrite anything loaded
                property_manager.set_property_connector(connector_contract=_pm_connector)
        elif has_contract and not HandlerFactory.instantiate(_connector).exists():
            raise FileNotFoundError(f"The property manager domain contact '{_connector.uri}' could not be found."
                                    f" If this is a new contract, set 'has_contract' to False")
        if default_save:
            property_manager.persist_properties(connector_contract=_pm_connector)
        return _module_name, _handler, _file_type

    @classmethod
    def from_memory(cls, has_contract: bool=None, default_save_intent: bool=None, default_intent_level: bool=None,
                    order_next_available: bool=None, default_replace_intent: bool=None, **kwargs):
        """ Class Factory Method that creates a light touch in memory instance that leaves no residue when closed.
        This factory method can load a reference contract from a remote repo as a foundation.

         :param default_save_intent: (optional) The default action for saving intent in the property manager
         :param default_intent_level: (optional) the default level intent should be saved at
         :param order_next_available: (optional) if the default behaviour for the order should be next available order
         :param default_replace_intent: (optional) the default replace existing intent behaviour
         :param has_contract: (optional) indicates the instance should have a property manager domain contract
         :param kwargs: to pass to the property ConnectorContract as its kwargs
         :return: the initialised class instance
        """
        # create a unique task name
        has_contract = has_contract if isinstance(has_contract, bool) else False
        default_save_intent = default_save_intent if isinstance(default_save_intent, bool) else False
        return cls.from_env(task_name='temporary_in_memory_instance', default_save=False, has_contract=has_contract,
                            default_save_intent=default_save_intent, default_intent_level=default_intent_level,
                            order_next_available=order_next_available, default_replace_intent=default_replace_intent,
                            **kwargs)

    @classmethod
    def from_env(cls, task_name: str, default_save=None, reset_templates: bool=None, align_connectors: bool=None,
                 default_save_intent: bool=None, default_intent_level: bool=None, order_next_available: bool=None,
                 default_replace_intent: bool=None, uri_pm_repo: str=None, has_contract: bool=None, **kwargs):
        """ Class Factory Method that builds the connector handlers taking the property contract path from
        the ``os.environ['HADRON_PM_PATH']`` or, if not found, uses the system default,
            - for Linux and IOS '/tmp/components/contracts
            - for Windows ``os.environ['AppData']\\components\\contracts``

        The following environment variables can be set:
            - HADRON_PM_PATH: the property contract path, if not found, uses the system default
            - HADRON_PM_REPO: the property contract should be initially loaded from a read only repo site such as github
            - HADRON_PM_TYPE: a file type for the property manager. If not found sets as 'json'
            - HADRON_PM_MODULE: a default module package, if not set uses component default
            - HADRON_PM_HANDLER: a default handler. if not set uses component default

        This method calls to the Factory Method ``from_uri(...)`` returning the initialised class instance

        :param task_name: The reference name that uniquely identifies a task or subset of the property manager
        :param default_save: (optional) if the configuration should be persisted
        :param reset_templates: (optional) reset connector templates from environ variables. Default True
        :param align_connectors: (optional) resets aligned connectors to the template. default Default True
        :param default_save_intent: (optional) The default action for saving intent in the property manager
        :param default_intent_level: (optional) the default level intent should be saved at
        :param order_next_available: (optional) if the default behaviour for the order should be next available order
        :param default_replace_intent: (optional) the default replace existing intent behaviour
        :param uri_pm_repo: The read only repo link that points to the raw data path to the contracts repo directory
        :param has_contract: (optional) indicates the instance should have a property manager domain contract
        :param kwargs: to pass to the property ConnectorContract as its kwargs
        :return: the initialised class instance
        """
        pm_file_type = os.environ.get('HADRON_PM_TYPE', 'json')
        pm_uri = os.environ.get('HADRON_PM_PATH', None)
        if isinstance(uri_pm_repo, str):
            pm_repo = uri_pm_repo
            default_save = False
        else:
            pm_repo = os.environ.get('HADRON_PM_REPO', None)
        if pm_uri is None:
            if os.access('.', os.W_OK | os.X_OK):
                pm_uri = os.path.join('.', 'hadron', 'contracts')
            elif platform.system().lower().startswith("Windows"):
                pm_uri = os.path.join(os.environ['AppData'], 'hadron', 'contracts')
            else:
                pm_uri = os.path.join('/tmp', 'hadron', 'contracts')
        creator = os.environ.get('HADRON_CREATOR', os.environ.get('USER', 'Unknown'))
        pm_module = os.environ.get('HADRON_PM_MODULE', None)
        pm_handler = os.environ.get('HADRON_PM_HANDLER', None)
        pm_kwargs = kwargs if isinstance(kwargs, dict) and len(kwargs) > 0 else None
        return cls.from_uri(task_name=task_name, uri_pm_path=pm_uri, uri_pm_repo=pm_repo, creator=creator,
                            has_contract=has_contract, pm_file_type=pm_file_type, pm_module=pm_module,
                            pm_handler=pm_handler, pm_kwargs=pm_kwargs, default_save=default_save,
                            reset_templates=reset_templates, align_connectors=align_connectors,
                            default_save_intent=default_save_intent, default_intent_level=default_intent_level,
                            order_next_available=order_next_available, default_replace_intent=default_replace_intent)

    @classmethod
    def _from_handler(cls, schema: str) -> (str, str, str):
        """ Class Factory Method that builds the connector handlers for the schema."""
        schema = schema if isinstance(schema, str) else ""
        for _package in ['ds_core', 'ds_capability']:
            _module_name = f'{_package}.handlers.{schema.lower()}_handlers'
            _source_handler = f'{schema.title()}SourceHandler'
            _persist_handler = f'{schema.title()}PersistHandler'
            if HandlerFactory.check_handler(_module_name, _persist_handler):
                return _module_name, _source_handler, _persist_handler
        return cls.DEFAULT_MODULE, cls.DEFAULT_SOURCE_HANDLER, cls.DEFAULT_PERSIST_HANDLER

    @classmethod
    def scratch_pad(cls):
        """ A class method to use the Components intent methods as a scratch pad"""
        return cls.from_memory().intent_model

    """
        PROPERTY MANAGER SECTION
    """

    def _get_environ(self, level: str, is_source: bool=None, default: str=None):
        """ returns the preference environ value based on type and if source or persist

        :param level: the level of environ, options are 'path', 'module' or  'handler'
        :param is_source: if this is for source or persist, default is persist
        :return: returns the default value if not found
        """
        if level not in ['path', 'module', 'handler']:
            raise ValueError(f"The type '{level}' is not supported, options are 'path', 'module' or 'handler'")
        handle = 'SOURCE' if isinstance(is_source, bool) and is_source else 'PERSIST'
        manager = f'HADRON_{self.pm.manager_name()}'.upper()
        task = f'HADRON_{self.pm.manager_name()}_{self.pm.task_name}'.upper()
        # task and manager
        result = os.environ.get(f"{task}_{handle}_{level}".upper(),
                                os.environ.get(f"{task}_{level}".upper(),
                                               os.environ.get(f"{manager}_{handle}_{level}".upper(),
                                                              os.environ.get(f"{manager}_{level}".upper(), None))))
        # now try the defaults
        if result is None:
            result = os.environ.get(f"HADRON_DEFAULT_{handle}_{level}".upper(),
                                    os.environ.get(f"HADRON_DEFAULT_{level}".upper(), None))
        return default if result is None else result

    def report_environ(self):
        """returns a report on the foundation environment variables"""
        report = dict()
        pm_cc = self.pm.get_connector_contract(self.pm.CONNECTOR_PM_CONTRACT)
        cc = self.pm.get_connector_contract(self.CONNECTOR_PERSIST)
        pm_cc_path = os.path.dirname(os.path.abspath(pm_cc.path))
        cc_path = os.path.dirname(os.path.abspath(cc.path))
        report.update({'HADRON_DEFAULT_PATH': os.environ.get('HADRON_DEFAULT_PATH', cc_path)})
        report.update({'HADRON_DEFAULT_MODULE': os.environ.get('HADRON_DEFAULT_MODULE', cc.module_name)})
        report.update({'HADRON_DEFAULT_HANDLER': os.environ.get('HADRON_DEFAULT_HANDLER', cc.handler)})
        report.update({'HADRON_PM_PATH': os.environ.get('HADRON_PM_PATH', pm_cc_path)})
        report.update({'HADRON_PM_REPO': os.environ.get('HADRON_PM_REPO', 'not used')})
        report.update({'HADRON_PM_TYPE': os.environ.get('HADRON_PM_TYPE', 'default')})
        report.update({'HADRON_PM_MODULE': os.environ.get('HADRON_PM_MODULE', pm_cc.module_name)})
        report.update({'HADRON_PM_HANDLER': os.environ.get('HADRON_PM_HANDLER', pm_cc.handler)})
        report.update({'HADRON_CREATOR': os.environ.get('HADRON_CREATOR', 'account default')})
        for key in os.environ.keys():
            if key.startswith('HADRON_'):
                report.update({key: os.environ.get(key, 'not used')})
        return report

    @property
    def intent_model(self):
        """The intent model instance"""
        return self._intent_model

    @property
    def pm(self):
        """The properties manager instance"""
        return self._component_pm

    def pm_persist(self, save=None):
        """Saves the current configuration to file"""
        if not isinstance(save, bool):
            save = self._default_save
        if save and self.pm.has_connector(self.pm.CONNECTOR_PM_CONTRACT):
            self.pm.persist_properties(only_branch=True)
        return

    @property
    def pm_name(self) -> str:
        """The contract name of this transition instance"""
        return self._component_pm.contract_name

    def pm_reset(self, save: bool=None):
        """ resets the contract back to a default. This does not remove the Property Manager Connector Contract or
        any snapshots

        :param save: override of the default save action set at initialisation.
        """
        if not isinstance(save, bool):
            save = self._default_save
        source_template = self.pm.get_connector_contract(connector_name=self.pm.TEMPLATE_SOURCE)
        persist_template = self.pm.get_connector_contract(connector_name=self.pm.TEMPLATE_PERSIST)
        self.pm.reset_all()
        self.add_connector_contract(connector_name=self.pm.TEMPLATE_SOURCE, connector_contract=source_template)
        self.add_connector_contract(connector_name=self.pm.TEMPLATE_PERSIST, connector_contract=persist_template)
        self.pm_persist(save)
        return

    def pm_transfer(self, transfer_connector: [str, ConnectorContract]):
        """ Takes a copy of the pm contract and saves it to a new location defined by the connector contract.
        This can be used to publish a property manager to a new location, change its format or as a backup

        :param transfer_connector: the name of an existing connector contract or a ConnectorContract
        """
        if not isinstance(transfer_connector, (str, ConnectorContract)):
            raise TypeError("The transfer_connector must be either a name of a connector or a ConnectorContract")
        connector_contract = transfer_connector
        if isinstance(transfer_connector, str):
            connector_contract = self.pm.get_connector_contract(transfer_connector)
        self.pm.persist_properties(connector_contract=connector_contract)
        return

    """
        CONNECTOR CONTRACTS SECTION
    """
    def add_connector_uri(self, connector_name: str, uri: str, save: bool=None, template_aligned: bool=None, **kwargs):
        """ Sets the contract giving the full uri path. This is a shortcut of set_source_contract(...), not
        requiring a ConnectorContract to be set up and using the default module and handler values.

        :param connector_name: the name or label to identify and reference the connector
        :param uri: a fully qualified uri of the source data
        :param template_aligned: the connector aligns with the template so changes to the template
        :param save: (optional) if True, save to file. Default is True
        """
        if not isinstance(uri, str) or len(uri) == 0:
            raise ValueError("The URI must be a valid string representation of a URI")
        template_aligned = template_aligned if isinstance(template_aligned, bool) else False
        _schema, _netloc, _path = ConnectorContract.parse_address_elements(uri=uri)
        _module_name, _, _handler = self._from_handler(schema=_schema)
        connector_contract = ConnectorContract(uri=uri, module_name=_module_name, handler=_handler,
                                               version=self.pm.version, **kwargs)
        self.add_connector_contract(connector_name=connector_name, connector_contract=connector_contract,
                                    template_aligned=template_aligned, save=save)
        return self

    def add_connector_contract(self, connector_name: str, connector_contract: ConnectorContract,
                               template_aligned: bool=None, save: bool=None):
        """ Sets a named connector contract

        :param connector_name: the name or label to identify and reference the connector
        :param connector_contract: a Connector Contract for the properties persistence
        :param template_aligned: the connector aligns with the template so changes to the template
        :param save: override of the default save action set at initialisation.
        :return: if load is True, returns a Pandas.DataFrame else None
        """
        if self.pm.has_connector(connector_name):
            self.pm.remove_connector_contract(connector_name)
        self.pm.set_connector_contract(connector_name=connector_name, connector_contract=connector_contract,
                                       aligned=template_aligned)
        self.pm_persist(save)
        return self

    def add_connector_source(self, connector_name: str, uri_file: str, save: bool=None, **kwargs):
        """ Adds a connector using settings from the self.pm.TEMPLATE_SOURCE template connector.

        :param connector_name: the name or label to identify and reference the connector
        :param uri_file: the name of the file to append to the end of the default path
        :param save: override of the default save action set at initialisation.
        :param kwargs: any kwargs to add to the default connector
        :return:
        """
        self.add_connector_from_template(connector_name=connector_name, uri_file=uri_file,
                                         template_name=self.pm.TEMPLATE_SOURCE, save=save, **kwargs)
        return self

    def add_connector_persist(self, connector_name: str, uri_file: str, save: bool=None, **kwargs):
        """ Adds a connector using settings from the self.pm.TEMPLATE_PERSIST template connector.
        self.pm.TEMPLATE_PERSIST are added at initialisation

        :param connector_name: the name or label to identify and reference the connector
        :param uri_file: the name of the file to append to the end of the default path
        :param save: override of the default save action set at initialisation.
        :param kwargs: any kwargs to add to the default connector
        :return:
        """
        self.add_connector_from_template(connector_name=connector_name, uri_file=uri_file,
                                         template_name=self.pm.TEMPLATE_PERSIST, save=save, **kwargs)
        return self

    def add_connector_from_template(self, connector_name: str, uri_file: str, template_name: str,  save: bool=None,
                                    **kwargs):
        """ Adds a connector using settings from a template connector. By default, a self.TEMPLATE_SOURCE and
        self.TEMPLATE_PERSIST are added at initialisation

        :param connector_name: the name or label to identify and reference the connector
        :param uri_file: the name of the file to append to the end of the default path
        :param template_name: optional template name
        :param save: override of the default save action set at initialisation.
        :param kwargs: any kwargs to add to the default connector
        :return:
        """
        if not self.pm.has_connector(connector_name=template_name):
            raise ValueError(f"The template connector '{template_name}' could not be found")
        template = self.pm.get_connector_contract(connector_name=template_name)
        uri = os.path.join(template.raw_uri, uri_file)
        if not isinstance(kwargs, dict):
            kwargs = {}
        template.raw_kwargs.update(kwargs)
        cc = ConnectorContract(uri=uri, module_name=template.raw_module_name, handler=template.raw_handler,
                               version=self.pm.version, **kwargs)
        self.add_connector_contract(connector_name=connector_name, connector_contract=cc, template_aligned=True,
                                    save=save)
        return self

    def reset_template_connectors(self, save: bool=None):
        """ resets connector contracts with template path and handler where they are template aligned.
        (see `set_connector_aligned`)

        :param save: override of the default save action set at initialisation.
        """
        connector_names =  self.pm.connector_contract_list
        for name in connector_names:
            if name in [self.pm.TEMPLATE_SOURCE, self.pm.TEMPLATE_PERSIST]:
                continue
            if self.pm.has_connector(name):
                if self.pm.is_connector_contract_aligned(name):
                    instance = HandlerFactory.instantiate(self.pm.get_connector_contract(connector_name=name))
                    if isinstance(instance, AbstractPersistHandler):
                        if self.pm.has_connector(self.pm.TEMPLATE_PERSIST):
                            persist_template = self.pm.get_connector_contract(self.pm.TEMPLATE_PERSIST)
                            self.pm.modify_connector_aligned(connector_name=name, template_contract=persist_template)
                    elif isinstance(instance, AbstractSourceHandler):
                        if self.pm.has_connector(self.pm.TEMPLATE_SOURCE):
                            source_template = self.pm.get_connector_contract(self.pm.TEMPLATE_SOURCE)
                            self.pm.modify_connector_aligned(connector_name=name, template_contract=source_template)
        self.pm_persist(save)
        return

    def remove_connector_contract(self, connector_name: str, save: bool=None):
        """removes a named connector contract

        :param connector_name: the name or label to identify and reference the connector
        :param save: override of the default save action set at initialisation.
        """
        if not isinstance(save, bool):
            save = self._default_save
        self.pm.remove_connector_contract(connector_name)
        self.pm_persist(save)
        return

    def set_connector_version(self, connector_names: [str, list], version: str, save: bool=None):
        """ modifies the uri of a connector contract and resets

        :param connector_names: a name or list of names of connector contract to modify
        :param version: the new version number
        :param save: override of the default save action set at initialisation.
        """
        if not isinstance(save, bool):
            save = self._default_save
        for name in self.pm.list_formatter(connector_names):
            self.pm.set_connector_version(connector_name=name, version=version)
        self.pm_persist(save)
        return

    def set_connector_aligned(self, connector_names: [str, list], aligned: bool, save: bool=None):
        """ modifies the uri of a connector contract and resets

        :param connector_names: a name or list of names of connector contract to modify
        :param aligned: if the connector contract is aligned to the template connector contract
        :param save: override of the default save action set at initialisation.
        """
        if not isinstance(save, bool):
            save = self._default_save
        for name in self.pm.list_formatter(connector_names):
            self.pm.set_connector_aligned(connector_name=name, aligned=aligned)
        self.pm_persist(save)
        return self

    def set_source(self, uri_file: str, save: bool=None, **kwargs):
        """sets the source contract CONNECTOR_SOURCE using the TEMPLATE_SOURCE connector contract,

        :param uri_file: the uri_file is appended to the template path
        :param save: (optional) if True, save to file. Default is True
        """
        self.add_connector_from_template(connector_name=self.CONNECTOR_SOURCE, uri_file=uri_file,
                                         template_name=self.pm.TEMPLATE_SOURCE, save=save, **kwargs)
        return self

    def set_source_uri(self, uri: str, save: bool=None, template_aligned: bool=None, **kwargs):
        """ Sets the source contract giving the full uri path. This is a shortcut of set_source_contract(...), not
        requiring a ConnectorContract to be set up and using the default module and handler values.

        :param uri: a fully qualified uri of the source data
        :param template_aligned: the connector aligns with the template so changes to the template
        :param save: (optional) if True, save to file. Default is True
        """
        template_aligned = template_aligned if isinstance(template_aligned, bool) else False
        self.add_connector_uri(connector_name=self.CONNECTOR_SOURCE, save=save, uri=uri,
                               template_aligned=template_aligned, **kwargs)
        return self

    def set_source_contract(self, connector_contract: ConnectorContract, template_aligned: bool=None, save: bool=None):
        """ Sets the source contract using the class CONNECTOR_SOURCE constant

        :param connector_contract: a Connector Contract for the source data
        :param template_aligned: the connector aligns with the template so changes to the template
        :param save: (optional) if True, save to file. Default is True
        """
        template_aligned = template_aligned if isinstance(template_aligned, bool) else False
        self.add_connector_contract(connector_name=self.CONNECTOR_SOURCE, connector_contract=connector_contract,
                                    template_aligned=template_aligned, save=save)
        return self

    def get_persist_contract(self) -> ConnectorContract:
        """ gets the persist connector contract that can be used as the next chain source. If
            the uri contains environment variables it is NOT parsed at load
        """
        return self.pm.get_connector_contract(self.CONNECTOR_PERSIST)

    def get_persist_uri(self) -> str:
        """ gets the persist connector contract uri that be used as the next chain source. If
            the uri contains environment variables it is parsed
        """
        return self.pm.get_connector_contract(self.CONNECTOR_PERSIST).raw_uri

    def set_persist(self, uri_file: str=None, save: bool=None, **kwargs):
        """sets the persist contract CONNECTOR_PERSIST using the TEMPLATE_PERSIST connector contract

        :param uri_file: (optional) the uri_file is appended to the template path
        :param save: (optional) if True, save to file. Default is True
        """
        file_pattern = self.pm.file_pattern(name=self.CONNECTOR_PERSIST)
        uri_file = uri_file if isinstance(uri_file, str) else file_pattern
        self.add_connector_from_template(connector_name=self.CONNECTOR_PERSIST, uri_file=uri_file,
                                         template_name=self.pm.TEMPLATE_PERSIST, save=save, **kwargs)
        return self

    def set_persist_uri(self, uri: str, save: bool=None, template_aligned: bool=None, **kwargs):
        """ Sets the persist contract giving the full uri path. This is a shortcut of set_persist_contract(...), not
        requiring a ConnectorContract to be set up and using the default module and handler values.

        :param uri: a fully qualified uri of the persist data
        :param template_aligned: the connector aligns with the template so changes to the template
        :param save: (optional) if True, save to file. Default is True
        """
        template_aligned = template_aligned if isinstance(template_aligned, bool) else False
        self.add_connector_uri(connector_name=self.CONNECTOR_PERSIST, save=save, uri=uri,
                               template_aligned=template_aligned, **kwargs)
        return self

    def set_persist_contract(self, connector_contract: ConnectorContract, save: bool=None):
        """ Sets the persist contract.

        :param connector_contract: a Connector Contract for the persisted data
        :param save: (optional) if True, save to file. Default is True
        """
        self.add_connector_contract(connector_name=self.CONNECTOR_PERSIST, connector_contract=connector_contract,
                                    save=save)
        return self

    def set_report_persist(self, reports: [str, list], project: str=None, path: [str, list]=None, prefix: str=None,
                           suffix: str=None, file_type: str=None, versioned: bool=None, stamped: str=None,
                           save: bool=None, **kwargs) -> list:
        """sets the report persist using the TEMPLATE_PERSIST connector contract, there are preset constants that
        should be used. These constance can be in the form <class>.REPORT_<NAME> or <instance>.REPORT_<NAME>
        where <NAME> is the name of the report and can be found in this class. Examples of reports might be:

        .. code-block:: py3

            Transition.REPORT_SCHEMA
            [self.REPORT_NOTES, self.REPORT_SCHEMA]
            [builder.REPORT_NOTES, {'report': builder.REPORT_SCHEMA, 'uri_file': '<file_name>'}]
            [{'report': Wrangle.REPORT_NOTES, 'file_type': 'json'}]
            [{'report': self.REPORT_SCHEMA, 'file_type': 'csv', 'versioned': True, 'stamped': 'days'}]

        if a report is presented as dict, the method signature parameters will be overwritten by the report values.
        This allows globally parameter to apply generally but allow single reports to be modified at a granular level.

        to ensure dict reports have the correct keys the util method 'report2dict(...)' can be used.

        :param reports: (optional) the name(s) of the report connector to set (see class REPORT_* constants)
        :param project: (optional) an alternative project string that replaces 'hadron'
        :param path: (optional) a file path that precedes the prefix and file pattern. uses os.path.join so takes a list
        :param prefix: (optional) a prefix to put at the front of the file pattern to replace the default
        :param suffix: (optional) a suffix to put at the end of the file pattern and extension
        :param file_type: (optional) a global file extension to the default 'json' format
        :param versioned: (optional) if all reports should include a version
        :param stamped: (optional) A string of the timestamp options ['days', 'hours', 'minutes', 'seconds', 'ns']
        :param save: (optional) if True, save to file. Default is True
        :param kwargs: (optional) additional parameters to send as kwargs for the Connect Contract
        :return: a list of connector names created from the reports
        """
        if not isinstance(reports, (str, list)):
            raise TypeError(f"The report names must be either a name reference, or a list of str and/or dict. "
                            f"'{type(reports)}' type was passed")
        rtn_reports = []
        for _report in self.pm.list_formatter(reports):
            if not isinstance(_report, (str, dict)):
                raise TypeError(f"The report type {type(_report)} is an unsupported type. Must be string or dict")
            if isinstance(_report, str):
                _report = {'report': _report}
            if not _report.get('report', None):
                raise ValueError(f"The report {_report} must have a 'report' key representing the ref report name")
            name = _report.get('report')
            # if the contact exists then replace it
            if self.pm.has_connector(connector_name=name):
                self.remove_connector_contract(connector_name=name, save=save)
            prefix = _report.get('prefix', prefix)
            suffix = _report.get('suffix', suffix)
            file_type = _report.get('file_type', file_type if isinstance(file_type, str) else 'json')
            versioned = _report.get('versioned', versioned if isinstance(versioned, str) else True)
            stamped = _report.get('stamped', stamped if isinstance(stamped, str) else False)
            file_pattern = self.pm.file_pattern(name=name, project=project, path=path, prefix=prefix, suffix=suffix,
                                                file_type=file_type, versioned=versioned, stamped=stamped)
            uri_file = _report.get('uri_file', file_pattern)
            self.add_connector_from_template(connector_name=name, uri_file=uri_file,
                                             template_name=self.pm.TEMPLATE_PERSIST, save=save, **kwargs)
            rtn_reports.append(name)
        return rtn_reports

    """
        INTENT SECTION
    """
    def add_run_book(self, run_levels: [str, list], book_name: str=None, save: bool=None):
        """ sets a named run book, the run levels are a list of levels and the order they are run in

        :param run_levels: the name or list of levels to be run
        :param book_name: (optional) the name of the run_book. defaults to 'primary_run_book'
        :param save: (optional) override of the default save action set at initialisation.
       """
        book_name = book_name if isinstance(book_name, str) else self.pm.PRIMARY_RUN_BOOK
        self.pm.set_run_book(book_name=book_name, run_levels=run_levels)
        self.pm_persist(save)

    def add_run_book_level(self, run_level: str, book_name: str=None, save: bool=None):
        """ adds a single runlevel to the end of a run_book. If the name already exists it will be replaced

        :param run_level: the run_level to add.
        :param book_name: (optional) the name of the run_book. defaults to 'primary_run_book'
        :param save: (optional) override of the default save action set at initialisation.
       """
        book_name = book_name if isinstance(book_name, str) else self.pm.PRIMARY_RUN_BOOK
        if self.pm.has_run_book(book_name=book_name):
            run_levels = self.pm.get_run_book(book_name=book_name)
            while run_level in run_levels:
                run_levels.remove(run_level)
            run_levels.append(run_level)
        else:
            run_levels = run_level
        self.pm.set_run_book(book_name=book_name, run_levels=run_levels)
        self.pm_persist(save)

    def remove_run_book(self, book_name: str=None, save: bool=None) -> bool:
        """ removes named run book. If no runbook is given then all run books are removed

        :param book_name: (optional) the name of the run_book. defaults to primary_run_book'
        :param save: (optional) override of the default save action set at initialisation.
        :return: True if removed, False if not
        """
        if isinstance(book_name, str):
            result = self.pm.remove_run_book(book_name=book_name)
        else:
            run_books = self.pm.get(self.pm.KEY.run_book_key, {})
            if isinstance(run_books, dict):
                for book in tuple(run_books.keys()):
                    self.pm.remove_run_book(book_name=book)
            result = True
        self.pm_persist(save)
        return result

    def remove_intent(self, intent_param: [str, dict]=None, level: [int, str]=None, save: bool=None):
        """ removes part or all the intent contract.
            - If no params all intent is removed
            - if only intent then all references in all params of that named intent will be removed
            - if only level then that level is removed
            - if both level and intent then that specific intent on that level is removed

        :param intent_param: (optional) removes the method contract
        :param level: (optional) removes the level contract
        :param save: (optional) override of the default save action set at initialisation.
        :return: True if removed, False if not
        """
        if isinstance(intent_param, (str, dict)) or isinstance(level, (int, str)):
            result = self.pm.remove_intent(intent_param=intent_param, level=level)
        else:
            for intent in tuple(self.pm.get_intent().keys()):
                self.pm.remove_intent(level=intent)
            result = True
        self.pm_persist(save)
        return result

    def add_intent_description(self, action: [int, str], text: str, save: bool=None):
        """ sets description associated with an intent action

        :param action: the action to add the comment to
        :param text: the description text
        :param save: (optional) override of the default save action set at initialisation.
        """
        self.pm.set_intent_description(level=action, text=text)
        self.pm_persist(save)
        return

    """
        CANONICAL SECTION
    """
    def load_canonical(self, connector_name: str, reset_changed: bool=None, has_changed: bool=None,
                       return_empty: bool=None, **kwargs) -> Any:
        """returns the canonical of the referenced connector

        :param connector_name: the name or label to identify and reference the connector
        :param reset_changed: (optional) resets the has_changed boolean to True
        :param has_changed: (optional) tests if the underline canonical has changed since last load else error returned
        :param return_empty: (optional) if has_changed is set, returns an empty canonical if set to True
        :param kwargs: arguments to be passed to the handler on load
        """
        if self.pm.has_connector(connector_name):
            has_changed = has_changed if isinstance(has_changed, bool) else False
            reset_changed = reset_changed if isinstance(reset_changed, bool) else False
            handler = self.pm.get_connector_handler(connector_name)
            if has_changed and handler.exists() == False:
                if isinstance(return_empty, bool) and return_empty:
                    return {}
                raise ConnectionAbortedError("The connector name {} has been aborted as the canonical to load "
                                             "does not exist".format(connector_name))
            if has_changed and handler.has_changed() == False:
                if isinstance(return_empty, bool) and return_empty:
                    return {}
                raise ConnectionAbortedError("The connector name {} has been aborted as the canonical to load "
                                             "has not changed".format(connector_name))
            canonical = handler.load_canonical(**kwargs)
            handler.reset_changed(changed=reset_changed)
            return canonical
        raise ConnectionError("The connector name {} can't be found.".format(connector_name))

    def persist_canonical(self, connector_name: str, canonical: Any, **kwargs):
        """persists the canonical to the referenced connector. same as save_canonical

        :param connector_name: the name or label to identify and reference the connector
        :param canonical: the canonical data to persist
        :param kwargs: arguments to be passed to the handler on persist
        """
        if self.pm.has_connector(connector_name):
            handler = self.pm.get_connector_handler(connector_name)
            handler.persist_canonical(canonical, **kwargs)
            return
        raise ConnectionError("The connector name {} can't be found.".format(connector_name))

    def save_canonical(self, connector_name: str, canonical: Any, **kwargs):
        """saves the canonical to the referenced connector. Same as persist_canonical

        :param connector_name: the name or label to identify and reference the connector
        :param canonical: the canonical data to persist
        :param kwargs: arguments to be passed to the handler on persist
        """
        self.persist_canonical(connector_name=connector_name, canonical=canonical, **kwargs)
        return

    def backup_canonical(self, connector_name: str, canonical: Any, uri: str, **kwargs):
        """persists the canonical to the referenced connector as a backup using the URI to
        replace the current Connector Contract URI.

        :param connector_name: the name or label to identify and reference the connector
        :param canonical: the canonical data to persist
        :param uri: an alternative uri to the one in the ConnectorContract
        :param kwargs: arguments to be passed to the handler on persist
        """
        if self.pm.has_connector(connector_name):
            _handler = self.pm.get_connector_handler(connector_name)
            _cc = self.pm.get_connector_contract(connector_name)
            _address = _cc.parse_address(uri=_cc.uri)
            _path, _, _ext = _address.rpartition('.')
            _handler.backup_canonical(canonical=canonical, uri=uri, **kwargs)
            return
        raise ConnectionError("The connector name {} was not found.".format(connector_name))

    def remove_canonical(self, connector_name: str, **kwargs):
        """removes the current persisted canonical.

        :param connector_name: the name or label to identify and reference the connector
        :param kwargs: arguments to be passed to the handler on remove
        """
        if self.pm.has_connector(connector_name):
            handler = self.pm.get_connector_handler(connector_name)
            handler.remove_canonical(**kwargs)
            return
        raise ConnectionError("The connector name {} was not found.".format(connector_name))

    """
        COMPONENT INFO SECTION FOR STATUS, DESCRIPTION AND VERSIONS
    """
    def set_version(self, version: str, save=None):
        """ sets the version
        :param version: the version to be set
        :param save: override of the default save action set at initialisation.
        """
        if not isinstance(save, bool):
            save = self._default_save
        self.pm.set_version(version=version)
        self.pm_persist(save)
        return

    def set_status(self, status: str, save=None):
        """ sets the status of this component task. Suggested status might be 'discovery', 'stable', 'production'
        :param status: the status to be set,
        :param save: override of the default save action set at initialisation.
        """
        if not isinstance(save, bool):
            save = self._default_save
        self.pm.set_status(status=status)
        self.pm_persist(save)
        return

    def set_description(self, description: str, save=None):
        """ sets the description of this component task
        :param description: a brief description of this component task
        :param save: override of the default save action set at initialisation.
        """
        if not isinstance(save, bool):
            save = self._default_save
        self.pm.set_description(description=description)
        self.pm_persist(save)
        return

    """
        SNAPSHOT SECTION
    """
    def create_snapshot(self, suffix: str=None, version: str=None, save: bool=None):
        """ creates a snapshot of contracts configuration. The name format will be <contract_name>_#<suffix>.

        :param suffix: (optional) adds the suffix to the end of the contract name. if None then date & time used
        :param version: (optional) changes the version number of the current contract
        :param save: override of the default save action set at initialisation.
        :return: a list of current contract snapshots
        """
        if not isinstance(save, bool):
            save = self._default_save
        result = self.pm.set_snapshot(suffix)
        if version is not None:
            self.set_version(version=version)
        self.pm_persist(save)
        return result

    def recover_snapshot(self, snapshot_name: str, overwrite: bool=None, save: bool=None) -> bool:
        """ recovers a snapshot back to the current. The snapshot must be from this root contract.
        by default the original root contract will be overwritten unless the overwrite is set to False.
        if overwrite is False a timestamped snapshot is created

        :param snapshot_name:the name of the snapshot (use self.contract_snapshots to get list of names)
        :param overwrite: (optional) if the original contract should be overwritten. Default to True
        :param save: override of the default save action set at initialisation.
        :return: True if the contract was recovered, else False
        """
        if not isinstance(save, bool):
            save = self._default_save
        result = self.pm.recover_snapshot(snapshot_name=snapshot_name, overwrite=overwrite)
        self.pm_persist(save)
        return result

    def delete_snapshot(self, snapshot_name: str, save: bool=None):
        """ deletes a snapshot

        :param snapshot_name: the name of the snapshot
        :param save: override of the default save action set at initialisation.
        :return: True if successful, False is not found or not deleted
        """
        if not isinstance(save, bool):
            save = self._default_save
        self.pm.remove_snapshot(snapshot_name=snapshot_name)
        self.pm_persist(save)
        return

    """
        NOTES SECTION
    """
    @property
    def notes_catalog(self) -> list:
        """returns the list of allowed catalog names"""
        return self.pm.knowledge_catalog

    def add_notes(self, catalog: str, label: [str, list], text: str, constraints: list=None,
                  save=None):
        """ adds a note to the augmented knowledge.
                if no label is given then a journal date of 'year-month' is provided
                if no catalog is given then the default catalogue name is given

        :param catalog: a catalog name
        :param label: a sub key label or list of labels to separate different information strands
        :param text: the text to add
        :param constraints: (optional) a list of allowed label values, if None then any value allowed
        :param save: if True, save to file. Default is True
        """
        if not isinstance(save, bool):
            save = self._default_save
        self.pm.set_knowledge(catalog=catalog, label=label, text=text, constraints=constraints)
        self.pm_persist(save)

    def remove_notes(self, catalog: str, label: str=None, save=None):
        """ removes a all entries for a labeled note

        :param catalog: the type of note to delete, if left empty all notes removed
        :param label: (Optional) the name of the label to be removed
        :param save: (Optional) if True, save to file. Default is True
        :return: True is successful, False if not
        """
        if not isinstance(save, bool):
            save = self._default_save
        self.pm.remove_knowledge(catalog=catalog, label=label)
        self.pm_persist(save)

    def upload_notes(self, canonical: dict, catalog: str, label_key: str, text_key: str, constraints: list=None,
                     save=None):
        """ Allows bulk upload of notes.

        :param canonical: a dictionary of where the key is the label and value is the text
        :param catalog: (optional) the section these notes should be put in
        :param label_key: the dictionary key name for the labels
        :param text_key: the dictionary key name for the text
        :param constraints: (optional) the limited list of acceptable labels. If not in list then ignored
        :param save: if True, save to file. Default is True
        """
        if label_key not in canonical.keys():
            raise ValueError(f"The label_key '{label_key}' is not a key of the canonical")
        if text_key not in canonical.keys():
            raise ValueError(f"The text_key '{text_key}' is not a key of the canonical")
        self.pm.bulk_upload_knowledge(canonical, catalog=catalog, label_key=label_key, text_key=text_key,
                                      constraints=constraints)
        self.pm_persist(save)

    @staticmethod
    def report2dict(report: str, file_type: str=None, versioned: bool=None, stamped: str=None, prefix: str=None,
                    suffix: str=None, path: [str, list]=None) -> dict:
        """ a utility method to help build analytics conditions by aligning method parameters with dictionary format.

        :param report: The name of the report
        :param file_type: (optional) an alternative file extension to the default 'json' format
        :param versioned: (optional) if the component version should be included as part of the pattern
        :param stamped: (optional) A string of the timestamp options ['days', 'hours', 'minutes', 'seconds', 'ns']
        :param prefix: (optional) a prefix to put at the front of the file pattern to replace the default
        :param suffix: (optional) a suffix to put at the end of the file pattern and extension
        :param path: (optional) a file path that precedes the prefix and file pattern. uses os.path.join so takes a list
        :return: a dictionary for an individual element
        """
        return CoreCommons.param2dict(**locals())
