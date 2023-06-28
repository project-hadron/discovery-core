Project Hadron Foundation Package
#################################

.. class:: no-web no-pdf

.. contents::

.. section-numbering::

What is Project Hadron
======================

Project Hadron provides a clear separation of concerns between components and their actions and data
and its content, whilst maintaining the original intentions of the data scientist, that can be passed
to a production team. It offers trust between the data scientists teams and product teams. It brings
with it transparency and traceability, dealing with bias, fairness, and knowledge. The resulting
outcome provides the product engineers with adaptability, robustness, and reuse; fitting seamlessly
into a microservices solution that can be language agnostic.

Project Hadron is designed using Microservices. Microservices - also known as the microservice
architecture - is an architectural pattern that structures an application as a collection of
component services that are:

* Highly maintainable and testable
* Loosely coupled
* Independently deployable
* Highly reusable
* Resilient
* Technically independent

Component services are built for business capabilities and each service performs a single function.
Because they are independently run, each service can be updated, deployed, and scaled to meet demand
for specific functions of an application. Project Hadron microservices enable the rapid, frequent
and reliable delivery of large, complex applications. It also enables an organization to evolve its
technology stack and experiment with innovative ideas.

At the heart of Project Hadron is a multi-tenant, NoSQL, singleton, in memory data store that has
minimal code and functionality and has been custom built specifically for Hadron tasks in  mind.
Abstracted from this is the component store which allows us to build a reusable set of methods
that define each tenanted component that sits separately from the store itself. In addition, a
dynamic key value class provides labeling so that each tenant is not tied to a fixed set of
reference values unless by specificity. Each of the classes, the data store, the component
property manager, and the key value pairs that make up the component are all independent,
giving complete flexibility and minimum code footprint to the build process of new components.

This is what gives us the Domain Contract for each tenant which sits at the heart of what makes
the contracts reusable, translatable, transferable and brings the data scientist closer to the
production engineer along with building a production ready component solution.

Installation
============

package install
---------------

The best way to install this package is directly from the Python Package Index repository using pip

.. code-block:: bash

    $ pip install aistac-foundation

if you want to upgrade your current version then using pip

.. code-block:: bash

    $ pip install --upgrade aistac-foundation

Package Overview
================

AbstractComponent
-----------------

The ``AbstractComponent`` class is a foundation class for the component build. It provides an encapsulated view of
the Property Management and Parameterised Intent

Abstract AI Single Task Application Component (AI-STAC) component class provides all the basic building blocks
of a components build including property management, augmented knowledge notes and parameterised intent pipeline.

For convenience there are three Factory Initialisation methods available``from_env(...)``, ``from_memory(...)`` and
``from_uri(...)`` the first two being abstract methods. The thrid factory method initialises the concrete
PropertyManager and IntentModel classes and use the parent ``_init_properties(...)`` methods to set the properties
connector. When creating the concrete class the ``from_uri(...)`` should be implemented. The following method can be
used as a template replacing ``ExamplePropertyManager`` and ``ExampleIntentModel`` with your oen concrete
implementations

.. code-block:: python

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


AbstractPropertyManager
-----------------------
The ``AbstractPropertiesManager`` facilitates the management of all the contract properties  including that of the
connector handlers, parameterised intent and Augmented Knowledge

Abstract AI Single Task Application Component (AI-STAC) class that creates a super class for all properties
managers

The Class initialisation is abstracted and is the only abstracted method. A concrete implementation of the
overloaded ``__init__`` manages the ``root_key`` and ``knowledge_key`` for this construct. The ``root_key`` adds a key
property reference to the root of the properties and can be referenced directly with ``<name>_key``. Likewise
the ``knowledge_key`` adds a catalog key to the restricted catalog keys.

More complex ``root_key`` constructs, where a grouping of keys might be desirable, passing a dictionary of name
value pairs as part of the list allows a root base to group related next level keys. For example

.. code-block:: python

    root_key = [{base: [primary, secondary}]

would add ``base.primary_key`` and ``base.secondary_key`` to the list of keys.

Here is a default example of an initialisation method:

.. code-block:: python

        def __init__(self, task_name: str):
            # set additional keys
            root_keys = []
            knowledge_keys = []
            super().__init__(task_name=task_name, root_keys=root_keys, knowledge_keys=knowledge_keys)


The property manager is not responsible for persisting the properties but provides the methods to load and persist
its in memory structure. To initialise the load and persist a ConnectorContract must be set up.

The following is a code snippet of setting a ConnectorContract and loading its content

.. code-block:: python

            self.set_property_connector(connector_contract=connector_contract)
            if self.get_connector_handler(self.CONNECTOR_PM_CONTRACT).exists():
                self.load_properties(replace=replace)

When using the property manager it will not automatically persist its properties and must be explicitely managed in
the component class. This removes the persist decision making away from the property manager. To persist the
properties use the method call ``persist_properties()``


AbstractIntentModel
-------------------
The ``AbstractIntentModel`` facilitates the Parameterised Intent, giving the base methods to record and replay intent.

Abstract AI Single Task Application Component (AI-STAC) Class for Parameterised Intent containing parameterised
intent registration methods ``_intent_builder(...)`` and ``_set_intend_signature(...)``.

it is creating a construct initialisation to allow for the control and definition of an ``intent_param_exclude``
list, ``default_save_intent`` boolean and a ``default_intent_level`` value.

As an example of an initialisation method

.. code-block:: python

    def __init__(self, property_manager: AbstractPropertyManager, default_save_intent: bool=None,
                 default_intent_level: bool=None, order_next_available: bool=None, default_replace_intent: bool=None):
        # set all the defaults
        default_save_intent = default_save_intent if isinstance(default_save_intent, bool) else True
        default_replace_intent = default_replace_intent if isinstance(default_replace_intent, bool) else True
        default_intent_level = default_intent_level if isinstance(default_intent_level, (str, int, float)) else 0
        default_intent_order = -1 if isinstance(order_next_available, bool) and order_next_available else 0
        intent_param_exclude = ['data', 'inplace']
        intent_type_additions = []
        super().__init__(property_manager=property_manager, default_save_intent=default_save_intent,
                         intent_param_exclude=intent_param_exclude, default_intent_level=default_intent_level,
                         default_intent_order=default_intent_order, default_replace_intent=default_replace_intent,
                         intent_type_additions=intent_type_additions)

in order to define the run pattern for the component task ``run_intent_pipeline(...)`` is an abstracted method
that defines the run pipeline of the intent.

As an example of a run_pipeline that iteratively updates a canonical with each intent

.. code-block:: python

    def run_intent_pipeline(self, canonical, intent_levels: [int, str, list]=None, **kwargs):
        # test if there is any intent to run
        if self._pm.has_intent():
            # get the list of levels to run
            if isinstance(intent_levels, (int, str, list)):
                intent_levels = Commons.list_formatter(intent_levels)
            else:
                intent_levels = sorted(self._pm.get_intent().keys())
            for level in intent_levels:
                level_key = self._pm.join(self._pm.KEY.intent_key, level)
                for order in sorted(self._pm.get(level_key, {})):
                    for method, params in self._pm.get(self._pm.join(level_key, order), {}).items():
                        if method in self.__dir__():
                            # add method kwargs to the params
                            if isinstance(kwargs, dict):
                                params.update(kwargs)
                            # add excluded parameters to the params
                            params.update({'inplace': False, 'save_intent': False})
                            canonical = eval(f"self.{method}(canonical, **{params})", globals(), locals())
        return canonical

The code signature for an intent method would have the following construct

.. code-block:: python

    def <method>(self, <params>..., save_intent: bool=None, intent_level: [int, str]=None, intent_order: int=None,
                 replace_intent: bool=None, remove_duplicates: bool=None):
        # resolve intent persist options
        self._set_intend_signature(self._intent_builder(method=inspect.currentframe().f_code.co_name, params=locals()),
                                   intent_level=intent_level, intent_order=intent_order, replace_intent=replace_intent,
                                   remove_duplicates=remove_duplicates, save_intent=save_intent)
        # intend code block on the canonical
        ...


Reference
=========


Python version
--------------

Python 3.6 or less is not supported. Although Python 3.7 is supported, it is recommended to
install ``aistac-foundation`` against the latest Python 3.8.x or greater whenever possible.

GitHub Project
--------------
aistac-foundation: `<https://github.com/project-hadron/aistac-foundation>`_.

Change log
----------

See `CHANGELOG <https://github.com/project-hadron/aistac-foundation/blob/master/CHANGELOG.rst>`_.


Licence
-------

MIT License: `<https://opensource.org/license/mit/>`_.


Authors
-------

`Gigas64`_  (`@gigas64`_) created aistac-foundation.


.. _pip: https://pip.pypa.io/en/stable/installing/
.. _Github API: http://developer.github.com/v3/issues/comments/#create-a-comment
.. _Gigas64: http://opengrass.io
.. _@gigas64: https://twitter.com/gigas64

