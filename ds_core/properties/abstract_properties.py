import os
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Any
# handlers
from ds_core.components.core_commons import CoreCommons
from ds_core.properties.property_manager import PropertyManager
from ds_core.handlers.abstract_handlers import AbstractSourceHandler, AbstractPersistHandler
from ds_core.handlers.abstract_handlers import HandlerFactory, ConnectorContract

__author__ = 'Darryl Oatridge'


class AbstractProperty(object):

    def __init__(self, properties: Any=None, manager: str=None, contract: str=None):
        """ An abstract class to create key references

        :param properties: (optional) list of property methods to be available for this instance. suffixed with '_key'
        :param manager: (optional) the name of the property manager
        :param contract: (optional) the name of the contract within the property manager
        """
        prefix = None
        if manager is not None and isinstance(manager, str) and len(manager) > 0:
            self._add_property(name="manager_key", rtn_value=manager)
            if contract is not None and isinstance(contract, str) and len(contract) > 0:
                prefix = '.'.join([manager, contract])
                self._add_property(name="contract_key", rtn_value=prefix)
            else:
                prefix = manager
        if isinstance(properties, (dict, str)):
            properties = [properties]
        if isinstance(properties, list):
            self._validate_reserved(properties)
            self._create_properties(attributes=properties, prefix=prefix)

    def keys(self) -> list:
        """ returns the list of property key methods """
        def key_value(inst, prefix):
            _key_methods = []
            for method in inst.__dir__():
                if method.endswith('key'):
                    _key_methods.append(method) if prefix is None else _key_methods.append("{}.{}".format(prefix,
                                                                                                          method))
                elif not method.startswith('_') and isinstance(inst.__getattribute__(method), AbstractProperty):
                    k = key_value(inst.__getattribute__(method), method)
                    _key_methods += k
            return _key_methods

        return key_value(self, None)

    @staticmethod
    def _validate_reserved(to_check: list):
        """Checks if any base key is reserved"""
        check_list = []
        for item in to_check:
            if isinstance(item, str):
                check_list.append(item)
            elif isinstance(item, list):
                check_list += item
            elif isinstance(item, dict):
                check_list = list(item.keys())
        if 'manager' in check_list or 'contract' in check_list:
            raise KeyError("The reserved words 'manager' and 'contract' can not be used as base property references")

    def _create_properties(self, attributes: Any, prefix: str=None, path: Any=None):
        """ create a set of method calls based on an attributes structure

        :param attributes: a dictionary or list like structure to build the methods from
        :param prefix: (optional) a prefix value to place before the key return value
        :param path: (optional) the depth reference
        """
        prev_path = path
        attr_dict = {}
        if isinstance(attributes, str):
            attr_dict[attributes] = None
        elif isinstance(attributes, list):
            for i in attributes:
                if isinstance(i, dict):
                    attr_dict.update(i)
                else:
                    attr_dict[i] = None
        else:
            attr_dict = attributes
        _prefix = '' if prefix is None else "{}.".format(prefix)
        for k, v in attr_dict.items():
            path = k if prev_path is None or len(prev_path) == 0 else '.'.join([prev_path, k])
            if isinstance(v, (dict, list, str)):
                _next_level = AbstractProperty()
                self._add_property(name=k, rtn_value=_next_level)
                self._add_property(name="{}_key".format(k), rtn_value=path, prefix=_prefix)
                _next_level._create_properties(attributes=v, prefix=_prefix, path=path)
            else:
                self._add_property(name="{}_key".format(k), rtn_value=path, prefix=_prefix)
                self._add_property(name="{}_value".format(k), rtn_value=k)
        return

    def _add_property(self, name: str, rtn_value: Any, prefix: str=None):
        if prefix is not None and name.endswith("_key"):
            rtn_value = "{}{}".format(prefix, rtn_value)
        if isinstance(rtn_value, str):
            rtn_value = rtn_value.replace('..', '.')
        _method = self._make_method(rtn_value)
        setattr(self, name, _method)

    @staticmethod
    def _make_method(rtn_value: Any):
        @property
        def _method():
            return rtn_value

        return _method.fget()


class AbstractPropertyManager(ABC):
    """ Abstract AI Single Task Application Component (AI-STAC) class that creates a super class for all properties
    managers

    The Class initialisation is abstracted and is the only abstracted method. A concrete implementation of the
    overloaded __init__ manages the ``root_key`` and ``knowledge_key`` for this construct. The ``root_key`` adds a key
    property reference to the root of the properties and can be referenced directly with ``<name>_key``. Likewise
    the ``knowledge_key`` adds a catalog key to the restricted catalog keys.

    More complex ``root_key`` constructs, where a grouping of keys might be desirable, passing a dictionary of name
    value pairs as part of the list allows a root base to group related next level keys. For example
    literal blocks::
    root_key = [{base: [primary, secondary}]

    would add ``base.primary_key`` and ``base.secondary_key`` to the list of keys.

    Here is a default example of an initialisation method:
    literal blocks::
        def __init__(self, task_name: str, root_keys: list, knowledge_keys: list, creator: str):
            # set additional keys
            root_keys = []
            knowledge_keys = []
            super().__init__(task_name=task_name, root_keys=root_keys, knowledge_keys=knowledge_keys, creator=creator)


    The property manager is not responsible for persisting the properties but provides the methods to load and persist
    its in memory structure. To initialise the load and persist a ConnectorContract must be set up.

    The following is a code snippet of setting a ConnectorContract and loading its content
    literal blocks::
            self.set_property_connector(connector_contract=connector_contract)
            if self.get_connector_handler(self.CONNECTOR_PM_CONTRACT).exists():
                self.load_properties(replace=replace)

    When using the property manager it will not automatically persist its properties and must be explicitly managed in
    the component class. This removes the persist decision making away from the property manager. To persist the
    properties use the method call ``persist_properties()``

    """
    CONNECTOR_PM_CONTRACT: str
    TEMPLATE_SOURCE = 'template_source'
    TEMPLATE_PERSIST = 'template_persist'
    PRIMARY_RUN_BOOK = 'primary_run_book'
    _KNOWLEDGE_ROOT = 'knowledge'
    _knowledge_catalog: list
    _connection_handler: dict
    _keys: AbstractProperty

    @abstractmethod
    def __init__(self, task_name: str, root_keys: list, knowledge_keys: list, creator: str):
        """initialises the properties manager.

        :param task_name: the name of the task name within the property manager
        :param root_keys: (optional) additional root keys used for property referencing. Called by 'self.KEY.<name>_key'
        :param knowledge_keys: (optional) replacement knowledge key called by 'self.KEY.knowledge.<name>_key'
        :param creator: (optional) a reference name of the creator of this instance of the task
        """
        if not isinstance(task_name, str) or len(task_name) == 0:
            raise ValueError('The contract must be a valid string')
        if not isinstance(creator, str) or len(creator) == 0:
            raise ValueError('The creator must be a valid string')
        # set globals
        self._task_name = task_name
        self._creator = creator
        self.CONNECTOR_PM_CONTRACT = "pm_{}_{}".format(self.manager_name(), str(task_name).lower())
        self._base_pm = PropertyManager()
        # set keys
        root_keys = root_keys if isinstance(root_keys, list) else []
        if isinstance(knowledge_keys, list) and len(knowledge_keys):
            self._knowledge_catalog = knowledge_keys
            self._knowledge_catalog.append('intent')
            self._knowledge_catalog.append('schema')
        else:
            self._knowledge_catalog = ['intent', 'schema']
        root_keys += ['description', 'version', 'status', 'connectors', 'intent', 'snapshot', 'run_book',
                      {'meta': ['module', 'class']}, {self._KNOWLEDGE_ROOT: self._knowledge_catalog}]
        self._keys = AbstractProperty(root_keys, manager=self.manager_name(), contract=self._task_name)
        if not self.is_key(self.KEY.contract_key):
            self.reset_all()
        self._connection_handler = {}
        self._create_abstract_properties()
        self._restricted_key = []
        for key in self.KEY.keys():
            self._restricted_key.append(eval(f"self.KEY.{key}"))

    @classmethod
    def manager_name(cls) -> str:
        """Class method to return the name of the manager and used to uniquely identify reference names."""
        return re.sub('(?!^)([A-Z]+)', r'_\1', str(cls.__name__).replace('PropertyManager', '')).lower()

    @property
    def task_name(self) -> str:
        """Property method to return the name of the task name set at initialisation. This is a reference name
        of the sub task for this manager.
        """
        return self._task_name

    @property
    def creator(self) -> str:
        """Property method to return the name of the user set at initialisation. This is a reference name for the
        user of this instance of the property task.
        """
        return self._creator

    def has_persisted_properties(self):
        """Test if the property manager has a persisted contract"""
        if self.has_connector(self.CONNECTOR_PM_CONTRACT):
            handler = self.get_connector_handler(self.CONNECTOR_PM_CONTRACT)
            return handler.exists()
        return False

    def set_property_connector(self, connector_contract: ConnectorContract):
        """ sets the connector contract where the properties can be persisted and recovered

        :param connector_contract: a Connector Contract for the properties persistence
        """
        self.remove(self.join(self.KEY.connectors_key, self.CONNECTOR_PM_CONTRACT))
        if self._connection_handler.get(self.CONNECTOR_PM_CONTRACT) is not None:
            self._connection_handler.pop(self.CONNECTOR_PM_CONTRACT)
        self.set_connector_contract(connector_name=self.CONNECTOR_PM_CONTRACT, connector_contract=connector_contract)
        return

    def persist_properties(self, connector_contract: ConnectorContract=None, only_branch: bool=None):
        """ persists properties to the set contract connector.

        :param connector_contract: an alternative connector contract to write the properties to.
                                   This can be used to transfer, backup or change filetype of the properties
        :param only_branch: As the file might have other properties in it from other managers or contracts, this
                            parameter defines if only the branch of properties should be loaded that belong to this
                            properties manager and contract only
                True: only loads properties from this branch of the properties tree
                False: loads all content from root
        """
        only_branch = only_branch if isinstance(only_branch, bool) else True
        if only_branch:
            _key = self.join(self.manager_name(),
                             self._task_name) if isinstance(self._task_name, str) else self.manager_name()
        else:
            _key = None
        if isinstance(connector_contract, ConnectorContract):
            if connector_contract.module_name is None or connector_contract.handler is None:
                raise ModuleNotFoundError("The module or handler for passed connector contract has not been set.")
            connector_handler = HandlerFactory.instantiate(connector_contract)
        else:
            connector_handler = self.get_connector_handler(connector_name=self.CONNECTOR_PM_CONTRACT)
        self._base_pm.dump(handler=connector_handler, key=_key)

    def load_properties(self, replace=False) -> bool:
        """ loads the properties from the contract connector

        :param replace: replaces everything that is currently in memory with the new properties
        :return: true if loaded successfully
        """
        connector_handler = self.get_connector_handler(connector_name=self.CONNECTOR_PM_CONTRACT)
        # only replace this contract not all things in the PM
        if replace:
            self.reset_all()
        _key = self.join(self.manager_name(),
                         self._task_name) if isinstance(self._task_name, str) else self.manager_name()
        return self._base_pm.load(handler=connector_handler, key=_key, replace=replace, ignore_key_error=True)

    def reset_all(self):
        """ Resets the properties to the default. This does not remove the property manager connector contract. """
        if self.is_key(self.join(self.KEY.connectors_key, self.CONNECTOR_PM_CONTRACT)):
            property_connector = self.get(self.join(self.KEY.connectors_key, self.CONNECTOR_PM_CONTRACT))
        else:
            property_connector = None
        self._base_pm.remove(self.KEY.contract_key)
        self._create_abstract_properties()
        # reset the property connector
        if property_connector is not None:
            self.set(self.join(self.KEY.connectors_key, self.CONNECTOR_PM_CONTRACT), property_connector)
            self.set_connector_version(connector_name=self.CONNECTOR_PM_CONTRACT, version=self.version)
        self._connection_handler = {}
        return

    @property
    def KEY(self):
        return self._keys

    @property
    def contract_name(self) -> str:
        """returns the contract name associated with this instance"""
        return self._task_name

    def is_key(self, key: str) -> bool:
        """test if the key exists"""
        return self._base_pm.is_key(key)

    def get(self, key: str, default: Any=None) -> [object, str, dict, tuple, list, int, float]:
        """gets a property value for the dot separated key"""
        return self._base_pm.get(key, default)

    def set(self, key: str, value: Any):
        """ sets the value for the dot separated key to the properties manager"""
        return self._base_pm.set(key, value)

    def remove(self, key: str):
        """ removes the dot separated key from the properties manager"""
        if key in self._restricted_key:
            raise PermissionError(f"The key passed is a root key and can not be removed")
        return self._base_pm.remove(key)

    def join(self, *names, sep=None) -> str:
        """Used to create a name string. Can also be used to join paths by passing sep=os.path.sep"""
        return self._base_pm.join(*names, sep=sep)

    def get_all(self) -> dict:
        """returns the full properties dictionary"""
        return self._base_pm.get_all()

    """
        TASK META DATA   
    """
    @property
    def description(self) -> str:
        """returns the summary description of the component task"""
        return self.get(self.KEY.description_key, "")

    def set_description(self, description: str):
        """ Sets a description of this component task for reference and identification"""
        self.set(self.KEY.description_key, description)
        return

    @property
    def status(self) -> str:
        """returns the status of the contract"""
        return str(self.get(self.KEY.status_key))

    def set_status(self, status: str):
        """ Sets the status of the contract status"""
        self.set(self.KEY.status_key, status)
        return

    @property
    def version(self) -> str:
        """returns the version of the contract"""
        return str(self.get(self.KEY.version_key))

    def set_version(self, version: str):
        """ Sets the version of the contract"""
        self.set(self.KEY.version_key, version)
        self._connection_handler = {}
        for connector_name in self.connector_contract_list:
            self.set_connector_version(connector_name=connector_name, version=self.version)
        return

    def reset_task_meta(self):
        """resets the contract info, removing any existing run books"""
        self.set_version('0.0.1')
        self.set_status('discovery')
        self.set_description('')

    def report_task_meta(self):
        """Reports on the current contract meta data such as names description version and status"""
        return {'contract': self.manager_name(), 'task': self.task_name, 'description': self.description,
                'status': self.status, 'version': self.version}

    def report_task(self):
        """Reports on the task as a whole returning a dictionary with the tasks primary reference values"""
        rtn_dict = self.get(self.KEY.contract_key)
        _ = rtn_dict.pop('meta', None)
        _ = rtn_dict.pop('snapshot', None)
        return rtn_dict

    """
        INTENT CODE and RUN BOOK SECTION   
    """
    def has_run_book(self, book_name: str=None) -> bool:
        """ test if the named run book exists

        :param book_name: (optional) the name of the run_book. defaults to 'primary_run_book'
        :return: True if the run book exists
        """
        book_name = book_name if isinstance(book_name, str) else self.PRIMARY_RUN_BOOK
        if self.is_key(self.join(self.KEY.run_book_key, book_name)):
            return True
        return False

    def set_run_book(self, run_levels: [str, list], book_name: str=None):
        """ records a run book of levels for the intent run pattern. This allows different run patterns
        to be passed to the run pipeline

        :param run_levels: a name or list of levels relating to this run book
        :param book_name: (optional) the name of the run_book. defaults to 'primary_run_book'
        """
        book_name = book_name if isinstance(book_name, str) else self.PRIMARY_RUN_BOOK
        if not isinstance(book_name, str) or len(book_name) == 0:
            raise ValueError("a reference book name must be provided")
        if not isinstance(run_levels, (str, list)) or len(run_levels) == 0:
            raise ValueError("The run book must be a list of levels")
        run_levels = self.list_formatter(run_levels)
        if self.is_key(self.join(self.KEY.run_book_key, book_name)):
            self.remove(self.join(self.KEY.run_book_key, book_name))
        self.set(self.join(self.KEY.run_book_key, book_name), run_levels)
        return

    def get_run_book(self, book_name: str=None) -> list:
        """ returns the named run book of levels

        :param book_name: (optional) the name of the run_book. defaults to 'primary_run_book'
        :return: a list of levels
        """
        book_name = book_name if isinstance(book_name, str) else self.PRIMARY_RUN_BOOK
        if self.is_key(self.join(self.KEY.run_book_key, book_name)):
            return self.get(self.join(self.KEY.run_book_key, book_name))
        raise LookupError("The book name '{}', does not exist.".format(book_name))

    def reset_run_books(self):
        """resets the run book, removing any existing run books"""
        self._base_pm.remove(self.KEY.run_book_key)
        self.set(self.KEY.run_book_key, {})

    def remove_run_book(self, book_name: str) -> bool:
        """ removes named run book

        :param book_name: the reference name of a run book
        """
        if self.is_key(self.join(self.KEY.run_book_key, book_name)):
            return self.remove(self.join(self.KEY.run_book_key, book_name))
        return False

    def report_run_book(self):
        """Reports on the current run books"""
        report = {'name': [], 'run_book': []}
        run_books = self.get(self.KEY.run_book_key, {})
        if isinstance(run_books, dict):
            for book, run_list in run_books.items():
                report['name'].append(book)
                report['run_book'].append(run_list)
        return report

    def get_intent(self, level: [int, str]=None, order: int=None, intent: str=None) -> dict:
        """Returns the parameterised intent contract in full or if level give and exists, returns the level contract"""
        if not isinstance(level, (str, int)) and (isinstance(order, int) or isinstance(intent, str)):
            raise ValueError("The parameter 'level' must be set if using 'order' or 'intent' for specific intent")
        if isinstance(level, (int, str)):
            # if just level, return the level
            if not isinstance(order, int) and not isinstance(intent, str):
                return self.get(self.join(self.KEY.intent_key, str(level)), {})
            # if no order then assume order to be zero
            order = order if isinstance(order, int) else 0
            if isinstance(intent, str):
                if self.is_key(self.join(self.KEY.intent_key, str(level), order, intent)):
                    body = self.get(self.join(self.KEY.intent_key, str(level), order, intent), {})
                    return {intent: body}
                return {}
            return self.get(self.join(self.KEY.intent_key, str(level), order), {})
        return self.get(self.KEY.intent_key, {})

    def has_intent(self, level: [int, str]=None) -> bool:
        """Test if the contract has intent, optionally a level can be tested"""
        if len(self.get_intent(level=level)) == 0:
            return False
        return True

    def set_intent(self, intent_param: dict, level: [int, str]=None, order: int=None, remove_all_duplicates: bool=None,
                   remove_level_duplicates: bool=None, replace_intent: bool=None):
        """ sets the intent section in the configuration file. Note: by default any identical intent, e.g.
        intent with the same intent (name) and the same parameter values, are removed from any level.

        :param intent_param: a dictionary type set of configuration representing a intent section contract
        :param level: (optional) the level of the intent,
        :param order: (optional) a subset of level defining an order for the intent. defaults to 0
                        If None: default's to -1
                        if -1: added to a level above any current instance of the intent section, level 0 if not found
                        if int or str: added to the level specified, overwriting any that already exist
        :param remove_all_duplicates: (optional) removes any duplicate intent in any level that is identical
        :param remove_level_duplicates: (optional) removes any duplicate intent in the single level that is identical
        :param replace_intent: (optional) if the intent method exists at the level and order,
                        True - replaces the current intent method with the new
                        False - leaves it untouched, disregarding the new intent
        """
        if not isinstance(intent_param, dict):
            raise ValueError("The intent section must be a dictionary. Ensure inplace=True in the passing method")
        if len(intent_param) == 0:
            return
        remove_level_duplicates = remove_level_duplicates if isinstance(remove_level_duplicates, bool) else True
        remove_all_duplicates = remove_all_duplicates if isinstance(remove_all_duplicates, bool) else False
        replace_intent = replace_intent if isinstance(replace_intent, bool) else True
        level = 'A' if not isinstance(level, (int, str)) else level
        order = -1 if not isinstance(order, int) else order
        # remove any repeats of this exact intent
        if remove_all_duplicates:
            self.remove_intent(intent_param=intent_param)
        elif remove_level_duplicates:
            self.remove_intent(level=level, intent_param=intent_param)
        for key, value in intent_param.items():
            if order == -1:
                if not self.get_intent():
                    self.set(self.join(self.KEY.intent_key, level, 0), {key: value})
                    continue
                order = 0
                while True:
                    if not self.is_key(self.join(self.KEY.intent_key, level, order)):
                        self.set(self.join(self.KEY.intent_key, level, order), {key: value})
                        break
                    order += 1
            else:
                if self.is_key(self.join(self.KEY.intent_key, level, order, key)):
                    if replace_intent:
                        self.remove(self.join(self.KEY.intent_key, level, order, key))
                        self.set(self.join(self.KEY.intent_key, level, order), {key: value})
                else:
                    self.set(self.join(self.KEY.intent_key, level, order), {key: value})
        return

    def reset_intents(self):
        """resets the intent root property, removing all parameterised intent"""
        self._base_pm.remove(self.KEY.intent_key)
        self.set(self.KEY.intent_key, {})
        return

    def remove_intent(self, intent_param: [str, dict]=None, level: [int, str]=None):
        """ removes part or all the intent contract.
                if only intent then all references in all levels of that named intent will be removed
                if only level then that level is removed
                if both level and intent then that specific intent on that level is removed

        :param intent_param: (optional) removes the method contract
        :param level: (optional) removes the level contract
        :return True if removed, False if not
        """
        if not isinstance(intent_param, (str, dict)) and not isinstance(level, (int, str)):
            raise ValueError("To remove an intent an 'intent name', 'level' or 'parameterised intent' must be passed")
        str_level = None if not isinstance(level, (int, str)) or str(level) == "-1" else str(level)

        # removes a intent from a level
        def _delete_intent(inst, _level: str, _intent: [str, dict]):
            clean_dict = {_intent: ''} if isinstance(_intent, str) else _intent
            for _method, _params in clean_dict.copy().items():
                for _order in tuple(inst.get(inst.join(inst.KEY.intent_key, _level), {}).keys()):
                    key_values = inst.get(inst.join(inst.KEY.intent_key, _level, _order, _method))
                    if key_values is None:
                        continue
                    if len(_params) > 0 and str(key_values) != str(_params):
                        continue
                    inst.remove(inst.join(inst.KEY.intent_key, _level, _order, _method))
                    if not inst.get(inst.join(inst.KEY.intent_key, _level, _order)):
                        inst.remove(inst.join(inst.KEY.intent_key, _level, _order))
                    if not inst.get(inst.join(inst.KEY.intent_key, _level)):
                        inst.remove(inst.join(inst.KEY.intent_key, _level))
            return

        if str_level and intent_param:
            _delete_intent(inst=self, _level=str_level, _intent=intent_param)
        elif str_level:
            self.remove(self.join(self.KEY.intent_key, str_level))
            self.remove_knowledge(catalog=self.KEY.knowledge.intent_value, label=str_level)
        elif intent_param:
            for key in sorted(self.get(self.KEY.intent_key).keys()):
                _delete_intent(inst=self, _level=key, _intent=intent_param)

    def set_intent_description(self, level: [int, str], text: str):
        """ sets description to the augmented knowledge 'intent' to a level

        :param level: the intent level to add the comment to
        :param text: the description text
        """
        if not self.has_intent(level=level):
            raise ValueError(f"The intent_level '{level}' can not be found to add a description too")
        if isinstance(text, str) and text:
            self.set_knowledge(catalog=self.KEY.knowledge.intent_value, label=level, text=text)
        return

    def report_intent_params(self, level: [int, str]) -> dict:
        """ creates a dictionary of a single intent level with each parameter displayed as a rows"""
        report = {'order': [], 'intent': [], 'parameter': [], 'value': []}
        levels = self.get_intent(level)
        for order in sorted(levels.keys()):
            for intent in sorted(levels.get(order, {}).keys()):
                for key, value in levels.get(order, {}).get(intent, {}).items():
                    if key in 'intent_creator':
                        continue
                    report['order'].append(order)
                    report['intent'].append(intent)
                    report['parameter'].append(key)
                    report['value'].append(value)
        return report

    def report_intent(self, levels: [int, str, list]=None, as_description: bool=None, level_label: str=None) -> dict:
        """ creates a dictionary report of the intent

        :param levels: (optional) a single or list of levels to filter on
        :param as_description: (optional) if the outcome should be a description report or a full report
        :param level_label: (optional) a label or name to give to the level header
        """
        as_description = as_description if isinstance(as_description, bool) else False
        level_label = level_label if isinstance(level_label, str) else 'level'
        if as_description:
            report = {level_label: [], 'description': []}
        else:
            report = {level_label: [], 'order': [], self.KEY.knowledge.intent_value: [], 'parameters': [],
                      'creator': []}
        if self.has_intent():
            if isinstance(levels, (int, str, list)):
                levels = self.list_formatter(levels)
            else:
                levels = sorted(self.get_intent().keys())
            for level in levels:
                if as_description:
                    report[level_label].append(level)
                    report['description'].append(", ".join(self.get_knowledge(catalog=self.KEY.knowledge.intent_value,
                                                                              label=level, as_list=True)))
                    continue
                for order in sorted(self.get(self.join(self.KEY.intent_key, level), {})):
                    for intent_param in sorted(self.get(self.join(self.KEY.intent_key, level, order), {})):
                        params = []
                        intent_key = self.join(self.KEY.intent_key, level, order, intent_param)
                        creator = self.get(intent_key, {}).pop('intent_creator', 'default')
                        for key, value in self.get(intent_key, {}).items():
                            if key in ['intent_creator']:
                                continue
                            params.append(f"{key}='{value}'" if isinstance(value, str) else f"{key}={value}")
                        report[level_label].append(level)
                        report['order'].append(order)
                        report['intent'].append(intent_param)
                        report['parameters'].append(params)
                        report['creator'].append(creator)
        return report

    """
        SNAPSHOTS CODE SECTION   
    """
    @property
    def snapshots(self):
        """returns all the contract snapshots of this contract name"""
        if isinstance(self.get(self.KEY.snapshot_key), dict):
            return list(self.get(self.KEY.snapshot_key).keys())
        return []

    def set_snapshot(self, suffix: str=None) -> str:
        """ creates a snapshot of the current contract configuration

        :param suffix: (optional) att the suffix to the end of the contract name. if None then date & time used
        :return the name of the snapshot
        """
        if suffix is None or not suffix:
            suffix = datetime.now().strftime("%Y-%m-%d_%H:%M")
        suffix = suffix.replace('.', '_')
        snap_dict = self.get(self.KEY.contract_key)
        if isinstance(snap_dict, dict) and snap_dict.get(self.KEY.snapshot_value) is not None:
            snap_dict.pop(self.KEY.snapshot_value)
        snap_name = "{}_#{}".format(self.contract_name, suffix)
        snap_key = self.join(self.KEY.snapshot_key, snap_name)
        self.set(snap_key, snap_dict)
        return snap_name

    def reset_snapshots(self):
        """resets the snapshots, removing any that currently exist"""
        self._base_pm.remove(self.KEY.snapshot_key)
        self.set(self.KEY.snapshot_key, {})
        return

    def recover_snapshot(self, snapshot_name: str, overwrite: bool=None) -> bool:
        """ recovers a snapshot back to the current. The snapshot must be from this root contract.
        by default the original root contract will be overwritten unless the overwrite is set to False.
        if overwrite is False a timestamped snapshot is created

        :param snapshot_name:the name of the snapshot (use self.contract_snapshots to get list of names)
        :param overwrite: (optional) if the original contract should be overwritten. Default to True
        :return: True if the contract was recovered, else False
        """
        overwrite = overwrite if isinstance(overwrite, bool) else True
        if snapshot_name is None or not isinstance(snapshot_name, str):
            return False
        _snapshot_key = self.join(self.KEY.snapshot_key, snapshot_name)
        if snapshot_name not in self.snapshots:
            return False
        if not overwrite:
            self.set_snapshot()
        recover_snapshot = self.get(_snapshot_key)
        all_snaps = self.get(self.KEY.snapshot_key)
        self.reset_all()
        self.set(self.KEY.contract_key, recover_snapshot)
        self.set(self.KEY.snapshot_key, all_snaps)

    def remove_snapshot(self, snapshot_name: str):
        """ deletes a snapshot

        :param snapshot_name: the name of the snapshot
        :return: True if successful, False is not found or not deleted
        """
        if snapshot_name is None or not isinstance(snapshot_name, str):
            return False
        _snapshot_key = self.join(self.KEY.snapshot_key, snapshot_name)
        if snapshot_name not in self.snapshots:
            return False
        return self.remove(_snapshot_key)

    """
        CONNECTOR CODE SECTION   
    """
    @property
    def connector_contract_list(self) -> List[str]:
        _contracts = self.get(self.KEY.connectors_key)
        if isinstance(_contracts, dict):
            return list(_contracts.keys())
        return []

    @property
    def connector_handler_list(self) -> List[str]:
        """returns a list of all current connector contract names"""
        if isinstance(self._connection_handler, dict):
            return list(self._connection_handler.keys())
        return []

    def is_connector_contract_aligned(self, connector_name: str) -> bool:
        base_key = self.join(self.KEY.connectors_key, connector_name)
        return self.get(self.join(base_key, 'aligned'), False)

    def get_connector_contract(self, connector_name: str) -> ConnectorContract:
        """returns a connector contract bean for the connector name"""
        if self.get(self.join(self.KEY.connectors_key, connector_name)) is None:
            raise LookupError("The connector '{}' has not been set in the property manager".format(connector_name))
        kwargs = self.get(self.join(self.KEY.connectors_key, connector_name, 'raw_kwargs'))
        if not isinstance(kwargs, dict):
            kwargs = {}
        _connector_key = self.join(self.KEY.connectors_key, connector_name)
        _path = ConnectorContract.parse_address(uri=self.get(self.join(_connector_key, 'raw_uri')))
        if str(_path).startswith('${'):
            _path = ConnectorContract.parse_environ(_path)
        _schema, _, _ = ConnectorContract.parse_address_elements(uri=_path)
        for _package in ['ds_discovery', 'ds_connectors']:
            _module_name = f'{_package}.handlers.{_schema.lower()}_handlers'
            _handler = f'{_schema.title()}PersistHandler'
            if HandlerFactory.check_handler(_module_name, _handler):
                self.set(self.join(_connector_key, 'raw_module_name'), _module_name)
                self.set(self.join(_connector_key, 'raw_handler'), _handler)
        return ConnectorContract(uri=self.get(self.join(_connector_key, 'raw_uri')),
                                 module_name=self.get(self.join(_connector_key, 'raw_module_name')),
                                 handler=self.get(self.join(_connector_key, 'raw_handler')),
                                 version=self.get(self.join(_connector_key, 'raw_version')),
                                 **kwargs)

    def set_connector_contract(self, connector_name: str, connector_contract: ConnectorContract, aligned: bool=None):
        """ sets the connector meta data referencing a uri, module and handler of the connector
        along with optional additional key word arguments expected by the underlying connector

        :param connector_name: a unique name reference of the connector contract
        :param connector_contract: a Connector Contract for the properties persistence
        :param aligned: if this connector contract is aligned to the template connector
        """
        if not isinstance(connector_contract, ConnectorContract):
            raise ValueError("The connector_contract must be a valid instance of the ConnectorContract class")
        aligned = aligned if isinstance(aligned, bool) else False
        if self.has_connector(connector_name):
            self.remove_connector_contract(connector_name)
        self._create_abstract_properties()
        base_key = self.join(self.KEY.connectors_key, connector_name)
        self.set(self.join(base_key, 'raw_uri'), connector_contract.raw_uri)
        self.set(self.join(base_key, 'raw_module_name'), connector_contract.raw_module_name)
        self.set(self.join(base_key, 'raw_handler'), connector_contract.raw_handler)
        self.set(self.join(base_key, 'raw_version'), connector_contract.raw_version)
        self.set(self.join(base_key, 'raw_kwargs'), connector_contract.raw_kwargs)
        self.set(self.join(base_key, 'aligned'), aligned)
        return

    def set_connector_aligned(self, connector_name: str, aligned: bool) -> bool:
        """ sets connector contract version number, removing the current handler so the new version is picked up

        :param connector_name: a unique name reference of the connector contract
        :param aligned: if the connector contract should be aligned to the template
        :return: True if set
        """
        if self.has_connector(connector_name):
            aligned = aligned if isinstance(aligned, bool) else False
            self.set(self.join(self.KEY.connectors_key, connector_name, 'aligned'), aligned)
            return True
        return False

    def set_connector_version(self, connector_name: str, version: str) -> bool:
        """ sets connector contract version number, removing the current handler so the new version is picked up

        :param connector_name: a unique name reference of the connector contract
        :param version: the version number to set
        :return: True if set
        """
        if self.has_connector(connector_name):
            self.remove_connector_handler(connector_name=connector_name)
            self.set(self.join(self.KEY.connectors_key, connector_name, 'raw_version'), version)
            return True
        return False

    def modify_connector_uri(self, connector_name: str, old_pattern: str, new_pattern: str) -> bool:
        """ modifies the named connector contract URI with a replacement pattern, resetting the handler

        :param connector_name: The name of the connector contract
        :param old_pattern: the old pattern to be find
        :param new_pattern: the new pattern to replace the old pattern
        :return: True if set
        """
        if self.has_connector(connector_name=connector_name):
            self.remove_connector_handler(connector_name=connector_name)
            old_uri = self.get(self.join(self.KEY.connectors_key, connector_name, 'raw_uri'))
            new_uri = old_uri.replace(old_pattern, new_pattern, 1)
            self.set(self.join(self.KEY.connectors_key, connector_name, 'raw_uri'), new_uri)
            return True
        return False

    def modify_connector_aligned(self, connector_name: str, template_contract: ConnectorContract) -> bool:
        """ modifies the named connector contract with a template contract. The template contract should only
        contain the uri path as the uri path 'head' or file is retained and joined with the template uri.

        :param connector_name: The name of the connector contract
        :param template_contract: the modifying template contract
        :return: True if set
        """
        if self.get(self.join(self.KEY.connectors_key, connector_name, 'aligned'), False):
            self.remove_connector_handler(connector_name=connector_name)
            raw_uri = self.get(self.join(self.KEY.connectors_key, connector_name, 'raw_uri'))
            if str(raw_uri).startswith('${'):
                raw_uri = ConnectorContract.parse_environ(raw_uri)
            _, file = os.path.split(raw_uri)
            raw_uri = os.path.join(template_contract.raw_uri, file)
            base_key = self.join(self.KEY.connectors_key, connector_name)
            self.set(self.join(base_key, 'raw_uri'), raw_uri)
            self.set(self.join(base_key, 'raw_module_name'), template_contract.raw_module_name)
            self.set(self.join(base_key, 'raw_handler'), template_contract.raw_handler)
            self.set(self.join(base_key, 'raw_version'), template_contract.raw_version)
            self.set(self.join(base_key, 'raw_kwargs'), template_contract.raw_kwargs)
            return True
        return False

    def get_connector_handler(self, connector_name: str) -> [AbstractSourceHandler, AbstractPersistHandler]:
        """returns the current connector handler for the connector name. If the connector handler instance doesn't exist
           then it is created from the handler parameters.
        """
        connector_contract = self.get_connector_contract(connector_name)
        if connector_contract.module_name is None or connector_contract.handler is None:
            raise ModuleNotFoundError("The module or handler for '{}' has not been set.".format(connector_name))
        if self._connection_handler.get(connector_name) is None:
            self._connection_handler[connector_name] = HandlerFactory.instantiate(connector_contract)
        return self._connection_handler.get(connector_name)

    def remove_connector_contract(self, connector_name: str):
        """Removes all connector properties"""
        if connector_name == self.CONNECTOR_PM_CONTRACT:
            raise ValueError("The connector contract name '{}' is a reserved name for the "
                             "PropertyManager connector and can not be removed".format(self.CONNECTOR_PM_CONTRACT))
        self.remove(self.join(self.KEY.connectors_key, connector_name))
        if self._connection_handler.get(connector_name) is not None:
            self._connection_handler.pop(connector_name)
        return

    def remove_connector_handler(self, connector_name: str):
        """removes the connector handler instance"""
        if self._connection_handler.get(connector_name) is not None:
            self._connection_handler.pop(connector_name)
        return

    def has_connector(self, connector_name: str) -> bool:
        """Test if the contract has intent"""
        if self.get(self.join(self.KEY.connectors_key, connector_name)) is None:
            return False
        return True

    def has_connector_handler(self, connector_name: str) -> bool:
        """checks if a connector contract has a minimum of uri, module and handler set"""
        for key in ['reconnectors_key', 'module_key', 'connectors_key']:
            if self.get(self.join(self.KEY.connectors_key, connector_name, key)) is None:
                return False
        return True

    def reset_connector_contracts(self):
        """resets all the connector contracts removing any existing except for the properties connector"""
        property_connector = None
        template_source_connector = None
        template_persist_connector = None
        if self.has_connector(self.CONNECTOR_PM_CONTRACT):
            property_connector = self.get_connector_contract(self.CONNECTOR_PM_CONTRACT)
        if self.has_connector(self.TEMPLATE_SOURCE):
            template_source_connector = self.get_connector_contract(self.TEMPLATE_SOURCE)
        if self.has_connector(self.TEMPLATE_PERSIST):
            template_persist_connector = self.get_connector_contract(self.TEMPLATE_PERSIST)
        self._base_pm.remove(self.KEY.connectors_key)
        self.set(self.KEY.connectors_key, {})
        if property_connector is not None:
            self.set_property_connector(property_connector)
        if template_source_connector is not None:
            self.set_connector_contract(self.TEMPLATE_SOURCE, template_source_connector)
        if template_persist_connector is not None:
            self.set_connector_contract(self.TEMPLATE_PERSIST, template_persist_connector)
        return

    def pm_file_pattern(self, project: str=None, file_type: str=None):
        """ returns the file pattern for the property manager

        :param project: (optional) an alternative project string that replaces 'hadron'
        :param file_type: (optional) an alternative file extension to the default 'parquet' format
        :return:
        """
        project = project if isinstance(project, str) else 'hadron'
        file_type = file_type if isinstance(file_type, str) else 'parquet'
        return f"{project}_pm_{self.manager_name()}_{self.task_name}.{file_type}"

    def file_pattern(self, name: str, project: str=None, path: [str, list]=None, prefix: str=None, suffix: str=None,
                     file_type: str=None, versioned: bool=None, stamped: str=None) -> str:
        """ returns a unique file pattern unique to this component task connector

        :param name: A unique name to place after the prefix
        :param project: (optional) an alternative project string that replaces 'hadron'
        :param path: (optional) a file path that precedes the prefix and file pattern. uses os.path.join so takes a list
        :param prefix: (optional) a prefix to put at the front of the file pattern to replace the default
        :param suffix: (optional) a suffix to put at the end of the file pattern and extension
        :param file_type: (optional) an alternative file extension to the default 'parquet' format
        :param versioned: (optional) if the component version should be included as part of the pattern
        :param stamped: (optional) A string of the timestamp options ['days', 'hours', 'minutes', 'seconds', 'ns']
        :return: a pattern unique to this component task connector
        """
        project = project.lower() if isinstance(project, str) else 'hadron'
        prefix = prefix if isinstance(prefix, str) else f"{project}_{self.manager_name()}_{self.task_name}_"
        suffix = suffix if isinstance(suffix, str) else ''
        file_type = file_type if isinstance(file_type, str) else 'parquet'

        _pattern = f"{prefix}{name}"
        if isinstance(path, (str, list)):
            path = self.list_formatter(path)
            _pattern = os.path.join(*path, _pattern)
        if isinstance(versioned, bool) and versioned:
            _pattern = "".join([_pattern, "${VERSION}"])
        if isinstance(stamped, str) and f"TO_{stamped.upper()}" in ConnectorContract.uri_tags():
            _pattern = "".join([_pattern, "${TO_", stamped.upper(), "}"])
        return f"{_pattern}.{file_type}{suffix}"

    def report_connectors(self, connector_filter: [str, list]=None, inc_pm: bool=None, inc_template: bool=None) -> dict:
        """ generates a report on the source contract

        :param connector_filter: (optional) filters on the connector name.
        :param inc_pm: (optional) include the property manager connector
        :param inc_template: (optional) include the template connectors
        :return: dict
        """
        inc_pm = inc_pm if isinstance(inc_pm, bool) else False
        inc_template = inc_template if isinstance(inc_template, bool) else False
        connector_filter = self.list_formatter(connector_filter)
        rtn_dict = {'connector_name': [], 'uri': [], 'module_name': [], 'handler': [], 'version': [], 'kwargs': [],
                    'query': [], 'aligned': []}
        for name_key in self.get(self.KEY.connectors_key).keys():
            if isinstance(connector_filter, list) and connector_filter and name_key not in connector_filter:
                continue
            if name_key.startswith('pm_transition') and not inc_pm:
                continue
            if name_key.startswith('template_') and not inc_template:
                continue
            connector_contract = self.get_connector_contract(name_key)
            if isinstance(connector_contract, ConnectorContract):
                kwargs = ''
                if isinstance(connector_contract.raw_kwargs, dict):
                    for k, v in connector_contract.raw_kwargs.items():
                        if len(kwargs) > 0:
                            kwargs += "  "
                        kwargs += f"{k}='{v}'"
                query = ''
                if isinstance(connector_contract.query, dict):
                    for k, v in connector_contract.query.items():
                        if len(query) > 0:
                            query += "  "
                        query += f"{k}='{v}'"
                rtn_dict['connector_name'].append(name_key)
                rtn_dict['uri'].append(connector_contract.raw_uri)
                rtn_dict['module_name'].append(connector_contract.raw_module_name)
                rtn_dict['handler'].append(connector_contract.raw_handler)
                rtn_dict['version'].append(connector_contract.version)
                rtn_dict['kwargs'].append(kwargs)
                rtn_dict['query'].append(query)
                rtn_dict['aligned'].append(self.get(self.join(self.KEY.connectors_key, name_key, 'aligned'), False))
        return rtn_dict

    """
        AUGMENTED KNOWLEDGE CODE SECTION   
    """
    @property
    def knowledge_catalog(self) -> list:
        """Returns the augmented knowledge catalog"""
        return self._knowledge_catalog

    def get_knowledge(self,  catalog: str, label: str=None, as_list: bool=None) -> [dict, list]:
        """returns a knowledge catalog with the option of filtering on label"""
        as_list = as_list if isinstance(as_list, bool) else False
        if catalog not in self.get(self.KEY.knowledge_key).keys():
            raise ValueError(f"The catalog name '{catalog}' is not recognised for this component."
                             f"Please select a catalog from '{self.knowledge_catalog}'")
        if not isinstance(label, (str, list)):
            rtn_dict = self.get(eval(f"self.KEY.{self._KNOWLEDGE_ROOT}.{catalog}_key"), {})
            return self.list_formatter(rtn_dict.keys()) if as_list else rtn_dict
        rtn_dict = self.get(self.join(eval(f"self.KEY.{self._KNOWLEDGE_ROOT}.{catalog}_key"), label), {})
        return self.list_formatter(rtn_dict.values()) if as_list else rtn_dict

    def has_knowledge(self, catalog: str=None, label: str=None) -> bool:
        """Test if the contract has a knowledge catalog"""
        if isinstance(catalog, str):
            catalog = self.list_formatter(catalog)
        else:
            catalog = self._knowledge_catalog
        for key in catalog:
            if isinstance(label, str):
                if self.is_key(self.join(eval(f"self.KEY.{self._KNOWLEDGE_ROOT}.{key}_key"), label)):
                    return True
            else:
                section = self.get(eval(f"self.KEY.{self._KNOWLEDGE_ROOT}.{key}_key"))
                if isinstance(section, dict) and len(section) > 0:
                    return True
        return False

    def set_knowledge(self, catalog: str, label: [str, list], text: str, constraints: list=None, replace: bool=False):
        """ adds knowledge to the augmented knowledge catalog

        :param catalog: (optional) the catalog this knowledge belongs to
        :param label: a sub key label to separate different knowledge strands
        :param text: the text to add to the augmented knowledge
        :param constraints: (optional)a list of allowed label values, if None then any value allowed
        :param replace: if this entry should replace any text that already exists
        """
        if text is None or not text or not isinstance(text, str):
            raise ValueError("The attribute text must be a valid string")
        if catalog not in self.get(self.KEY.knowledge_key).keys():
            raise ValueError(f"The catalog name '{catalog}' is not recognised for this component."
                             f"Please select a catalog from '{self.knowledge_catalog}'")
        label = self.list_formatter(label)
        for name in label:
            if isinstance(constraints, list) and len(constraints) > 0:
                if name not in constraints:
                    raise ValueError("The label '{}' is not in the selection list {}".format(name, constraints))
            _key = self.join(eval("self.KEY.{}.{}_key".format(self._KNOWLEDGE_ROOT, catalog)), name)
            if self.get(_key) is not None:
                if isinstance(self.get(_key), str) and text == self.get(_key):
                    return
                if isinstance(self.get(_key), list) and text in self.get(_key):
                    return
                if isinstance(self.get(_key), dict) and text in self.get(_key).values():
                    return
            if isinstance(replace, bool) and replace:
                self.remove_knowledge(catalog=catalog, label=name)
            entry = {str(datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')): text}
            self.set(_key, entry)
        return

    def bulk_upload_knowledge(self, data: dict, catalog: str, label_key: str, text_key: str, constraints: list=None):
        """ Allows bulk upload of augmented knowledge

        :param data: a dictionary of name value pairs of label and text
        :param catalog: the catalog this knowledge should be put in
        :param label_key: the dictionary key name for the labels
        :param text_key: the dictionary key name for the text
        :param constraints: (optional) the limited list of acceptable labels. If not in list then ignored
        """
        if catalog not in self.get(self.KEY.knowledge_key).keys():
            raise ValueError("The catalog {} is not recognised as a valid catalog".format(catalog))
        constraints = [] if not isinstance(constraints, list) else constraints
        if len(data.keys()) < 2:
            raise ValueError("The bulk upload data must have at least two keys for 'labels' and 'text'")
        labels_list = data.get(label_key, [])
        text_list = data.get(text_key, [])
        for index in range(len(labels_list)):
            label = labels_list[index]
            text = text_list[index]
            if len(constraints) > 0 and label not in constraints:
                continue
            self.set_knowledge(label=label, text=text, catalog=catalog)
        return

    def remove_knowledge(self, catalog: str, label: str=None):
        """ removes a all entries under knowledge catalog, with the optional subset of the catalog label

        :param catalog: the catalog to remove
        :param label: (optional) a sub key label to remove
        :return: True is successful, False if not
        """
        if catalog not in self.get(self.KEY.knowledge_key).keys():
            raise ValueError("The catalog {} is not recognised as a Augmented Type".format(catalog))
        _key = eval("self.KEY.{}.{}_key".format(self._KNOWLEDGE_ROOT, catalog))
        if isinstance(label, str):
            _key = self.join(_key, label)
        return self.remove(_key)

    def reset_knowledge(self):
        """resets all the augmented knowledge values"""
        self._base_pm.remove(self.KEY.knowledge_key)
        self.set(self.KEY.knowledge_key, {})
        self.set(self.KEY.knowledge.schema_key, {})

    @property
    def canonical_schemas(self):
        """return the list of current schemas"""
        return list(self.get(self.KEY.knowledge.schema_key, {}).keys())

    def has_canonical_schema(self, name: str) -> bool:
        """Test if the contract has intent"""
        if self.get(self.join(self.KEY.knowledge.schema_key, name)) is None:
            return False
        return True

    def get_canonical_schema(self, name: str):
        """ returns the stored data dictionary"""
        return self.get(self.join(self.KEY.knowledge.schema_key, name), {})

    def set_canonical_schema(self, name: str, schema: dict):
        """ add the dictionary """
        if self.is_key(self.join(self.KEY.knowledge.schema_key, name)):
            self.remove(self.join(self.KEY.knowledge.schema_key, name))
        return self.set(self.join(self.KEY.knowledge.schema_key, name), schema)

    def remove_canonical_schema(self, name: str):
        """ add the dictionary """
        return self.remove(self.join(self.KEY.knowledge.schema_key, name))

    def reset_canonical_schemas(self):
        """resets all the canonical Schemas, removing all current"""
        self._base_pm.remove(self.KEY.knowledge.schema_key)
        self.set(self.KEY.knowledge.schema_key, {})

    def knowledge_filter(self, catalog: [str, list]=None, label: [str, list]=None, exclude: bool=None,
                         regex: [str, list]=None, re_ignore_case: bool=None) -> dict:
        """ filters out notes based on the parameter values passed

        :param catalog: the catalog to filter on
        :param label: the label to filter on
        :param exclude: if to exclude the labels
        :param regex: a regular expression to filter on within the text
        :param re_ignore_case: if the regular expression should ignore case. Default is False
        :return: dictionary of the results
        """
        exclude = exclude if isinstance(exclude, bool) else False
        re_ignore_case = re_ignore_case if isinstance(re_ignore_case, bool) else False
        catalog = self.list_formatter(catalog)
        label = self.list_formatter(label)
        regex = self.list_formatter(regex)

        augmented_dict = self.get(self.KEY.knowledge_key)
        rtn_dict = augmented_dict

        if not isinstance(rtn_dict, dict):
            return {}

        # filter regex on attributes
        if regex is not None and regex:
            re_ignore_case = re.I if re_ignore_case else 0
            for exp in regex:
                for c in augmented_dict.keys():
                    if isinstance(augmented_dict.get(c), dict):
                        for li in augmented_dict.get(c).keys():
                            if isinstance(augmented_dict.get(c).get(li), dict):
                                for k, v in augmented_dict.get(c).get(li).items():
                                    if not re.search(exp, v, re_ignore_case):
                                        rtn_dict.get(c).get(li).pop(k)
                                        if len(rtn_dict.get(c).get(li)) == 0:
                                            rtn_dict.get(c).pop(li)
                            else:
                                rtn_dict.get(c).pop(li)
                        if isinstance(rtn_dict.get(c), dict) and len(rtn_dict.get(c)) == 0:
                            rtn_dict.pop(c)
                    else:
                        rtn_dict.pop(c)

        if catalog is not None and catalog:
            for c in tuple(augmented_dict.keys()):
                if c not in catalog:
                    rtn_dict.pop(c)

        # filter label keys
        if label is not None and label:
            for c in augmented_dict.keys():
                if isinstance(augmented_dict.get(c), dict):
                    for li in tuple(augmented_dict.get(c).keys()):
                        if exclude:
                            if li in label:
                                rtn_dict.get(c).pop(li)
                        elif li not in label and rtn_dict.get(c) is not None:
                            rtn_dict.get(c).pop(li)
                    if isinstance(rtn_dict.get(c), dict) and len(rtn_dict.get(c)) == 0:
                        rtn_dict.pop(c)

        return rtn_dict

    def report_notes(self, catalog: [str, list]=None, labels: [str, list]=None, regex: [str, list]=None,
                     re_ignore_case: bool=None, drop_dates: bool=None):
        """ generates a report on the notes

        :param catalog: (optional) the catalog to filter on
        :param labels: (optional) s label or list of labels to filter on
        :param regex: a regular expression on the notes
        :param re_ignore_case: if the regular expression should be case sensitive
        :param drop_dates: (optional) excludes the 'date' column from the report
        :return: a dictionary with key as the header and list of values
        """
        re_ignore_case = re_ignore_case if isinstance(re_ignore_case, bool) else False
        drop_dates = drop_dates if isinstance(drop_dates, bool) else False
        if isinstance(catalog, (str, list)):
            catalog = self.list_formatter(catalog)
        else:
            catalog = self.knowledge_catalog
        if isinstance(labels, (list, str)):
            labels = self.list_formatter(labels)
        for t in catalog:
            if t not in self.knowledge_catalog:
                raise ValueError("The note_type {} is not recognised as a Augmented Knowledge type".format(t))
        drop_dates = False if not isinstance(drop_dates, bool) else drop_dates
        report_data = self.knowledge_filter(catalog=catalog, label=labels, regex=regex,
                                            re_ignore_case=re_ignore_case)
        rtn_dict = {'section': [], 'label': [], 'text': []}
        if not drop_dates:
            rtn_dict.update({'date': []})
        for section in report_data.keys():
            # df = pd.DataFrame(columns=['section', 'label', 'date', 'text'])
            if report_data.get(section) is not None:
                for label, values in report_data.get(section).items():
                    if labels is not None and label not in labels:
                        continue
                    if isinstance(values, dict):
                        for date, text in values.items():
                            rtn_dict['section'].append(section)
                            rtn_dict['label'].append(label)
                            rtn_dict['text'].append(text)
                            if not drop_dates:
                                rtn_dict['date'].append(date.replace('T', ' ').rpartition(':'))
        return rtn_dict

    """
        PRIVATE & UTILITIES SECTION
    """
    def _create_abstract_properties(self):
        for method in self.KEY.__dir__():
            if method == 'meta_key':
                if not self.is_key(self.KEY.meta.module_key):
                    self.set(self.KEY.meta.module_key, self.__module__.split("."))
                if not self.is_key(self.KEY.meta.class_key):
                    self.set(self.KEY.meta.class_key, self.__class__.__name__)
            if method == 'version_key':
                if not self.is_key(self.KEY.version_key):
                    self.set(self.KEY.version_key, '0.0.1')
            if method == 'status_key':
                if not self.is_key(self.KEY.status_key):
                    self.set(self.KEY.status_key, 'discovery')
            if method == 'description_key':
                if not self.is_key(self.KEY.description_key):
                    self.set(self.KEY.description_key, "")
            elif str(method).endswith('_key'):
                key = eval("self.KEY.{}".format(method))
                if not self.is_key(key):
                    self.set(key, {})
        for catalog in self._knowledge_catalog:
            if not self.is_key(eval("self.KEY.{}.{}_key".format(self._KNOWLEDGE_ROOT, catalog))):
                self.set(eval("self.KEY.{}.{}_key".format(self._KNOWLEDGE_ROOT, catalog)), {})
        return

    @staticmethod
    def list_formatter(value) -> list:
        """ Useful utility method to convert any type of str, list, tuple or pd.Series into a list"""
        return CoreCommons.list_formatter(value=value)
