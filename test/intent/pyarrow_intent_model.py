import inspect
import threading
import pyarrow as pa
from ds_core.components.core_commons import CoreCommons
from ds_core.intent.abstract_intent import AbstractIntentModel
from test.properties.pyarrow_property_manager import PyarrowPropertyManager

__author__ = 'Darryl Oatridge'



class PyarrowIntentModel(AbstractIntentModel):
    """a pure python implementation of an Intent as a working example of the Intent Abstraction"""

    def __init__(self, property_manager: PyarrowPropertyManager, default_save_intent: bool=None,
                 default_intent_level: bool=None, order_next_available: bool=None, default_replace_intent: bool=None):
        """initialisation of the Intent class.

        :param property_manager: the property manager class that references the intent contract.
        :param default_save_intent: (optional) The default action for saving intent in the property manager
        :param default_intent_level: (optional) the default level intent should be saved at
        :param order_next_available: (optional) if the default behaviour for the order should be next available order
        :param default_replace_intent: (optional) the default replace existing intent behaviour
        """
        default_save_intent = default_save_intent if isinstance(default_save_intent, bool) else True
        default_replace_intent = default_replace_intent if isinstance(default_replace_intent, bool) else True
        default_intent_level = default_intent_level if isinstance(default_intent_level, (str, int, float)) else 'A'
        default_intent_order = -1 if isinstance(order_next_available, bool) and order_next_available else 0
        intent_param_exclude = ['data', 'inplace']
        intent_type_additions = []
        super().__init__(property_manager=property_manager, default_save_intent=default_save_intent,
                         intent_param_exclude=intent_param_exclude, default_intent_level=default_intent_level,
                         default_intent_order=default_intent_order, default_replace_intent=default_replace_intent,
                         intent_type_additions=intent_type_additions)

    def run_intent_pipeline(self, canonical: dict, intent_levels: [int, str, list]=None, inplace: bool=False, **kwargs):
        """ Collectively runs all parameterised intent taken from the property manager against the code base as
        defined by the intent_contract.

        It is expected that all intent methods have the 'canonical' as the first parameter of the method signature
        and will contain 'inplace' and 'save_intent' as parameters.

        :param canonical: this is the iterative value all intent are applied to and returned.
        :param intent_levels: (optional) an single or list of levels to run, if list, run in order given
        :param inplace: (optional) change data in place or to return a deep copy. default False
        :param kwargs: additional kwargs to add to the parameterised intent, these will replace any that already exist
        :return Canonical with parameterised intent applied or None if inplace is True
        """
        inplace = inplace if isinstance(inplace, bool) else False

        # test if there is any intent to run
        if self._pm.has_intent() and not inplace:
            # create the copy and use this for all the operations
            if not inplace:
                with threading.Lock():
                    canonical = canonical.copy()
            # get the list of levels to run
            if isinstance(intent_levels, (int, str, list)):
                intent_levels = self._pm.list_formatter(intent_levels)
            else:
                intent_levels = sorted(self._pm.get_intent().keys())
            for level in intent_levels:
                level_key = self._pm.join(self._pm.KEY.intent_key, level)
                for order in sorted(self._pm.get(level_key, {})):
                    for method, params in self._pm.get(self._pm.join(level_key, order), {}).items():
                        params.update(params.pop('kwargs', {}))
                        # add method kwargs to the params
                        if isinstance(kwargs, dict):
                            params.update(kwargs)
                        # remove intent_creator
                        _ = params.pop('intent_creator', 'default')
                        # add excluded parameters to the params
                        params.update({'inplace': False, 'save_intent': False})
                        canonical = eval(f"self.{method}(canonical, **{params})", globals(), locals())
        if not inplace:
            return canonical

    def to_select(self, data: pa.Table, headers: [str, list]=None, drop: bool=False, d_type: [str, list]=None,
                  exclude: bool=False, regex: [str, list]=None, re_ignore_case: bool=True, save_intent: bool=None,
                  intent_level: [int, str]=None, intent_order: int=None, replace_intent: bool=None,
                  remove_duplicates: bool=None) -> pa.Table:
        """ converts columns to object type

        :param data: the Canonical data to get the column headers from
        :param headers: a list of headers to drop or filter on type
        :param drop: to drop or not drop the headers
        :param d_type: the column types to include or exclude. Default None else int, float, bool, object, 'number'
        :param exclude: to exclude or include the dtypes
        :param regex: a regular expression to search the headers
        :param re_ignore_case: true if the regex should ignore case. Default is False
        :param save_intent (optional) if the intent contract should be saved to the property manager
        :param intent_level: (optional) the level name that groups intent by a reference name
        :param intent_order: (optional) the order in which each intent should run.
                        If None: default's to -1
                        if -1: added to a level above any current instance of the intent section, level 0 if not found
                        if int: added to the level specified, overwriting any that already exist
        :param replace_intent: (optional) if the intent method exists at the level, or default level
                        True - replaces the current intent method with the new
                        False - leaves it untouched, disregarding the new intent
        :param remove_duplicates: (optional) removes any duplicate intent in any level that is identical
        :return: if inplace, returns a formatted cleaner contract for this method, else a deep copy Canonical,.
       """
        # intent persist options
        self._set_intend_signature(self._intent_builder(method=inspect.currentframe().f_code.co_name, params=locals()),
                                   intent_level=intent_level, intent_order=intent_order, replace_intent=replace_intent,
                                   remove_duplicates=remove_duplicates, save_intent=save_intent)
        selection = CoreCommons.filter_columns(data, headers=headers, drop=drop, regex=regex)

        return selection
