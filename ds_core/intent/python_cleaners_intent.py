import inspect
import threading
from datetime import datetime

from aistac.components.aistac_commons import AistacCommons
from aistac.intent.abstract_intent import AbstractIntentModel
from aistac.properties.abstract_properties import AbstractPropertyManager

__author__ = 'Darryl Oatridge'


class PythonCleanersIntentModel(AbstractIntentModel):
    """a pure python implementation of Cleaner Intent as a working example of the Intent Abstraction"""

    def __init__(self, property_manager: AbstractPropertyManager, default_save_intent: bool=None,
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

    def auto_clean_header(self, data: dict, case: str=None, rename_map: dict=None, replace_spaces: str=None,
                          inplace: bool=False, save_intent: bool=None, intent_level: [int, str]=None,
                          intent_order: int=None, replace_intent: bool=None, remove_duplicates: bool=None):
        """ clean the headers of a pandas DataFrame replacing space with underscore

        :param data: the data to drop duplicates from
        :param rename_map: a from: to dictionary of headers to rename
        :param case: changes the headers to lower, upper, title. if none of these then no change
        :param replace_spaces: character to replace spaces with. Default is '_' (underscore)
        :param inplace: if the passed data should be used or a deep copy
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
        :return: if inplace, returns a formatted cleaner contract for this method, else a deep copy data.
        """
        # intent persist options
        self._set_intend_signature(self._intent_builder(method=inspect.currentframe().f_code.co_name, params=locals()),
                                   intent_level=intent_level, intent_order=intent_order, replace_intent=replace_intent,
                                   remove_duplicates=remove_duplicates, save_intent=save_intent)
        # intent code
        replace_spaces = '_' if not isinstance(replace_spaces, str) else replace_spaces
        case = str.lower(case) if isinstance(case, str) and str.lower(case) in ['lower', 'upper', 'title'] else None
        if not inplace:
            with threading.Lock():
                data = data.copy()
        keys = list(data.keys())
        for key in keys:
            # removes any hidden characters
            header = str(key)
            # remap any keys
            if isinstance(rename_map, dict) and header in rename_map.keys():
                header = rename_map[key]
            # convert case
            if case is not None:
                header = eval("str.{}(header)".format(case))
            # replaces spaces at the end just in case title is used
            header = str(header).replace(' ', replace_spaces)
            data[header] = data.pop(key)
        if not inplace:
            return data

    # drop column that only have 1 value in them
    def auto_remove_columns(self, data, null_min: float=None, predominant_max: float=None,
                            nulls_list: [bool, list]=None, inplace: bool=False, save_intent: bool=None,
                            intent_level: [int, str]=None, intent_order: int=None, replace_intent: bool=None,
                            remove_duplicates: bool=None) -> dict:
        """ auto removes columns that are np.NaN, a single value or have a predominat value greater than.

        :param data: the data to auto remove
        :param null_min: the minimum number of null values default to 0.998 (99.8%) nulls
        :param predominant_max: the percentage max a single field predominates default is 0.998
        :param nulls_list: can be boolean or a list:
                    if boolean and True then null_list equals ['NaN', 'nan', 'null', '', 'None']
                    if list then this is considered potential null values.
        :param inplace: if to change the passed data or return a copy (see return)
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
        :return: if inplace, returns a formatted cleaner contract for this method, else a deep copy data.
        """
        # intent persist options
        self._set_intend_signature(self._intent_builder(method=inspect.currentframe().f_code.co_name, params=locals()),
                                   intent_level=intent_level, intent_order=intent_order, replace_intent=replace_intent,
                                   remove_duplicates=remove_duplicates, save_intent=save_intent)
        # intent code
        null_min = 0.998 if not isinstance(null_min, (int, float)) else null_min
        predominant_max = 0.998 if not isinstance(predominant_max, (int, float)) else predominant_max
        if isinstance(nulls_list, bool) and nulls_list:
            nulls_list = ['NaN', 'nan', 'null', '', 'None']
        elif not isinstance(nulls_list, list):
            nulls_list = None
        if not inplace:
            with threading.Lock():
                data = data.copy()

        to_remove = list()
        for c in data.keys():
            col = data.get(c)
            if nulls_list is not None:
                col[:] = [None if x in nulls_list else x for x in col]
            # remove all None using list comprehension
            col[:] = list(filter(None, col))
            if len(col) == 0 or round(len(col) / len(data.get(c)), 3) > null_min:
                to_remove.append(c)
            elif len(set(col)) == 1:
                to_remove.append(c)
            elif round(sorted([col.count(x) for x in set(col)], reverse=True)[0] / len(col), 3) >= predominant_max:
                to_remove.append(c)
        for c in to_remove:
            data.pop(c)
        if not inplace:
            return data

    def to_remove(self, data: dict, headers: [str, list]=None, drop: bool=False, dtype: [str, list]=None,
                  exclude: bool=False, regex: [str, list]=None, re_ignore_case: bool=True,
                  inplace: bool = False, save_intent: bool = None, intent_level: [int, str] = None,
                  intent_order: int = None, replace_intent: bool = None, remove_duplicates: bool = None) -> dict:
        """ remove columns from the Canonical,

        :param data: the Canonical data to get the column headers from
        :param headers: a list of headers to drop or filter on type
        :param drop: to drop or not drop the headers
        :param dtype: the column types to include or excluse. Default None else int, float, bool, object, 'number'
        :param exclude: to exclude or include the dtypes
        :param regex: a regiar expression to seach the headers
        :param re_ignore_case: true if the regex should ignore case. Default is False
        :param inplace: if the passed Canonical, should be used or a deep copy
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
        # intent code
        if not inplace:
            with threading.Lock():
                data = data.copy()

        selection = AistacCommons.filter_headers(data=data, headers=headers, drop=drop, dtype=dtype, exclude=exclude,
                                                 regex=regex, re_ignore_case=re_ignore_case)
        for c in selection:
            data.pop(c)
        if not inplace:
            return data

    def to_select(self, data: dict, headers: [str, list]=None, drop: bool=False, dtype: [str, list]=None,
                  exclude: bool=False, regex: [str, list]=None, re_ignore_case: bool=True,
                  inplace: bool = False, save_intent: bool = None, intent_level: [int, str] = None,
                  intent_order: int = None, replace_intent: bool = None, remove_duplicates: bool = None) -> dict:
        """ remove columns from the Canonical,

        :param data: the Canonical data to get the column headers from
        :param headers: a list of headers to drop or filter on type
        :param drop: to drop or not drop the headers
        :param dtype: the column types to include or excluse. Default None else int, float, bool, object, 'number'
        :param exclude: to exclude or include the dtypes
        :param regex: a regiar expression to seach the headers
        :param re_ignore_case: true if the regex should ignore case. Default is False
        :param inplace: if the passed Canonical, should be used or a deep copy
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
        # intent code
        if not inplace:
            with threading.Lock():
                data = data.copy()

        data = AistacCommons.filter_columns(data=data, headers=headers, drop=drop, dtype=dtype, exclude=exclude,
                                            regex=regex, re_ignore_case=re_ignore_case, inplace=True)
        if not inplace:
            return data

    def to_bool_type(self, data: dict, bool_map, headers: [str, list]=None, drop: bool=False, dtype: [str, list]=None,
                     exclude: bool=False, regex: [str, list]=None, re_ignore_case: bool=True,
                     inplace: bool = False, save_intent: bool = None, intent_level: [int, str] = None,
                     intent_order: int = None, replace_intent: bool = None, remove_duplicates: bool = None) -> dict:
        """ converts column to bool based on the map

        :param data: the Canonical data to get the column headers from
        :param bool_map: a mapping of what to make True and False
        :param headers: a list of headers to drop or filter on type
        :param drop: to drop or not drop the headers
        :param dtype: the column types to include or excluse. Default None else int, float, bool, object, 'number'
        :param exclude: to exclude or include the dtypes
        :param regex: a regiar expression to seach the headers
        :param re_ignore_case: true if the regex should ignore case. Default is False
        :param inplace: if the passed Canonical, should be used or a deep copy
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
        # intent code
        if not inplace:
            with threading.Lock():
                data = data.copy()

        selection = AistacCommons.filter_headers(data=data, headers=headers, drop=drop, dtype=dtype, exclude=exclude,
                                                 regex=regex, re_ignore_case=re_ignore_case)
        for c in selection:
            values = data.pop(c)
            data[c] = [bool(x) for x in values]
        if not inplace:
            return data

    def to_numeric_type(self, data: dict, headers: [str, list]=None, drop: bool=False, dtype: [str, list]=None,
                        exclude: bool=False, regex: [str, list]=None, re_ignore_case: bool=True, precision: int=None,
                        fillna: str=None, errors: str=None, inplace: bool=False, save_intent: bool=None,
                        intent_level: [int, str]=None, intent_order: int=None, replace_intent: bool=None,
                        remove_duplicates: bool=None) -> dict:
        """ converts columns to int type

        :param data: the Canonical data to get the column headers from
        :param headers: a list of headers to drop or filter on type
        :param drop: to drop or not drop the headers
        :param dtype: the column types to include or excluse. Default None else int, float, bool, object, 'number'
        :param exclude: to exclude or include the dtypes
        :param regex: a regular expression to seach the headers
        :param re_ignore_case: true if the regex should ignore case. Default is False
        :param precision: how many decimal places to set the return values. if None then the number is unchanged
        :param fillna: { num_value, 'mean', 'mode', 'median' }. Default to np.nan
                    - If num_value, then replaces NaN with this number value. Must be a value not a string
                    - If 'mean', then replaces NaN with the mean of the column
                    - If 'mode', then replaces NaN with a mode of the column. random sample if more than 1
                    - If 'median', then replaces NaN with the median of the column
        :param errors : {'ignore', 'raise', 'coerce'}, default 'coerce'
                    - If 'raise', then invalid parsing will raise an exception
                    - If 'coerce', then invalid parsing will be set as NaN
                    - If 'ignore', then invalid parsing will return the input
        :param inplace: if the passed Canonical, should be used or a deep copy
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
        # intent code
        precision = 3 if not isinstance(precision, int) else precision
        if not inplace:
            with threading.Lock():
                data = data.copy()

        selection = AistacCommons.filter_headers(data=data, headers=headers, drop=drop, dtype=dtype, exclude=exclude,
                                                 regex=regex, re_ignore_case=re_ignore_case)
        for c in selection:
            values = data.pop(c)
            values = [round(float(x), precision) for x in values if isinstance(x, float)]
            values = [int(x) for x in values if isinstance(x, int)]
            data[c] = [float('nan') for x in values if not isinstance(x, (float, int))]
        if not inplace:
            return data

    def to_int_type(self, data: dict, headers: [str, list]=None, drop: bool=False, dtype: [str, list]=None,
                    exclude: bool=False, regex: [str, list]=None, re_ignore_case: bool=True, fillna: str=None,
                    errors: str=None, inplace: bool=False, save_intent: bool=None, intent_level: [int, str]=None,
                    intent_order: int=None, replace_intent: bool=None, remove_duplicates: bool=None) -> dict:
        """ converts columns to int type

        :param data: the Canonical data to get the column headers from
        :param headers: a list of headers to drop or filter on type
        :param drop: to drop or not drop the headers
        :param dtype: the column types to include or excluse. Default None else int, float, bool, object, 'number'
        :param exclude: to exclude or include the dtypes
        :param regex: a regiar expression to seach the headers
        :param re_ignore_case: true if the regex should ignore case. Default is False
        :param fillna: { num_value, 'mean', 'mode', 'median' }. Default to 0
                    - If num_value, then replaces NaN with this number value
                    - If 'mean', then replaces NaN with the mean of the column
                    - If 'mode', then replaces NaN with a mode of the column. random sample if more than 1
                    - If 'median', then replaces NaN with the median of the column
        :param errors : {'ignore', 'raise', 'coerce'}, default 'coerce'
                    - If 'raise', then invalid parsing will raise an exception
                    - If 'coerce', then invalid parsing will be set as NaN
                    - If 'ignore', then invalid parsing will return the input
        :param inplace: if the passed Canonical, should be used or a deep copy
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
        # intent code
        if not inplace:
            with threading.Lock():
                data = data.copy()

        selection = AistacCommons.filter_headers(data=data, headers=headers, drop=drop, dtype=dtype, exclude=exclude,
                                                 regex=regex, re_ignore_case=re_ignore_case)
        for c in selection:
            values = data.pop(c)
            data[c] = [int(x) if isinstance(x, (float, int)) else int('nan') for x in values]
            if errors == 'raise':
                if int('nan') in data.get(c):
                    raise ValueError("Not all values can be converted to int")
        if not inplace:
            return data

    def to_float_type(self, data: dict, headers: [str, list]=None, drop: bool=False, dtype: [str, list]=None,
                      exclude: bool=False, regex: [str, list]=None, re_ignore_case: bool=True, precision: int=None,
                      fillna: str=None, errors: str=None, inplace: bool=False, save_intent: bool=None,
                      intent_level: [int, str]=None, intent_order: int=None, replace_intent: bool=None,
                      remove_duplicates: bool=None) -> dict:
        """ converts columns to float type

        :param data: the Canonical data to get the column headers from
        :param headers: a list of headers to drop or filter on type
        :param drop: to drop or not drop the headers
        :param dtype: the column types to include or excluse. Default None else int, float, bool, object, 'number'
        :param exclude: to exclude or include the dtypes
        :param regex: a regiar expression to seach the headers
        :param re_ignore_case: true if the regex should ignore case. Default is False
        :param precision: how many decimal places to set the return values. if None then the number is unchanged
        :param fillna: { num_value, 'mean', 'mode', 'median' }. Default to np.nan
                    - If num_value, then replaces NaN with this number value
                    - If 'mean', then replaces NaN with the mean of the column
                    - If 'mode', then replaces NaN with a mode of the column. random sample if more than 1
                    - If 'median', then replaces NaN with the median of the column
        :param errors : {'ignore', 'raise', 'coerce'}, default 'coerce' }. Default to 'coerce'
                    - If 'raise', then invalid parsing will raise an exception
                    - If 'coerce', then invalid parsing will be set as NaN
                    - If 'ignore', then invalid parsing will return the input
        :param inplace: if the passed Canonical, should be used or a deep copy
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
        # intent code
        precision = 3 if not isinstance(precision, int) else precision
        if not inplace:
            with threading.Lock():
                data = data.copy()

        selection = AistacCommons.filter_headers(data=data, headers=headers, drop=drop, dtype=dtype, exclude=exclude,
                                                 regex=regex, re_ignore_case=re_ignore_case)
        for c in selection:
            values = data.pop(c)
            data[c] = [round(float(x), precision) if isinstance(x, (float, int)) else float('nan') for x in values]
        if not inplace:
            return data

    def to_str_type(self, data: dict, headers: [str, list]=None, drop: bool=False, dtype: [str, list]=None,
                    exclude: bool=False, regex: [str, list]=None, re_ignore_case: bool=True,
                    nulls_list: [bool, list]=None, inplace: bool=False, save_intent: bool=None,
                    intent_level: [int, str]=None, intent_order: int=None, replace_intent: bool=None,
                    remove_duplicates: bool=None) -> dict:
        """ converts columns to object type

        :param data: the Canonical data to get the column headers from
        :param headers: a list of headers to drop or filter on type
        :param drop: to drop or not drop the headers
        :param dtype: the column types to include or excluse. Default None else int, float, bool, object, 'number'
        :param exclude: to exclude or include the dtypes
        :param regex: a regiar expression to seach the headers
        :param re_ignore_case: true if the regex should ignore case. Default is False
        :param nulls_list: can be boolean or a list:
                    if boolean and True then null_list equals ['NaN', 'nan', 'null', '', 'None']
                    if list then this is considered potential null values.
        :param inplace: if the passed Canonical, should be used or a deep copy
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
        # intent code
        if not inplace:
            with threading.Lock():
                data = data.copy()

        selection = AistacCommons.filter_headers(data=data, headers=headers, drop=drop, dtype=dtype, exclude=exclude,
                                                 regex=regex, re_ignore_case=re_ignore_case)
        for c in selection:
            values = data.pop(c)
            data[c] = [str(x) if x is not None else None for x in values]
        if not inplace:
            return data

    def to_date_type(self, data: dict, headers: [str, list]=None, drop: bool=False, dtype: [str, list]=None,
                     exclude: bool=False, regex: [str, list]=None, re_ignore_case: bool=None, as_num: bool=False,
                     day_first: bool=False, year_first: bool=False, inplace: bool=False, save_intent: bool=None,
                     intent_level: [int, str]=None, intent_order: int=None, replace_intent: bool=None,
                     remove_duplicates: bool=None) -> dict:
        """ converts columns to date types

        :param data: the Canonical data to get the column headers from
        :param headers: a list of headers to drop or filter on type
        :param drop: to drop or not drop the headers
        :param dtype: the column types to include or excluse. Default None else int, float, bool, object, 'number'
        :param exclude: to exclude or include the dtypes
        :param regex: a regiar expression to seach the headers
        :param re_ignore_case: true if the regex should ignore case. Default is False
        :param as_num: if true returns number of days since 0001-01-01 00:00:00 with fraction being hours/mins/secs
        :param year_first: specifies if to parse with the year first
                If True parses dates with the year first, eg 10/11/12 is parsed as 2010-11-12.
                If both dayfirst and yearfirst are True, yearfirst is preceded (same as dateutil).
        :param day_first: specifies if to parse with the day first
                If True, parses dates with the day first, eg %d-%m-%Y.
                If False default to the a prefered preference, normally %m-%d-%Y (but not strict)
        :param inplace: if the passed Canonical, should be used or a deep copy
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
        self._set_intend_signature(self._intent_builder(method=inspect.currentframe().f_code.co_name, params=locals()),
                                   intent_level=intent_level, intent_order=intent_order, replace_intent=replace_intent,
                                   remove_duplicates=remove_duplicates, save_intent=save_intent)
        if not inplace:
            with threading.Lock():
                data = data.copy()

        selection = AistacCommons.filter_headers(data=data, headers=headers, drop=drop, dtype=dtype, exclude=exclude,
                                                 regex=regex, re_ignore_case=re_ignore_case)
        for c in selection:
            values = data.pop(c)
            data[c] = [datetime.strptime(x, '%m/%d/%Y') for x in values]
        if not inplace:
            return data
