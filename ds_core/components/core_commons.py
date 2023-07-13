from __future__ import annotations

from collections import abc, Counter
import math
import re
from datetime import datetime
from typing import Any
import pyarrow as pa
import pyarrow.compute as pc
from pyarrow.lib import ArrowInvalid, ArrowTypeError, ArrowNotImplementedError

class CoreCommons(object):
    """ common methods """

    @staticmethod
    def list_formatter(value: Any) -> list:
        """ Useful utility method to convert any type of str, list, tuple or pd.Series into a list"""
        if isinstance(value, (int, float, str, datetime)):
            return [value]
        if isinstance(value, (list, tuple, set)):
            return list(value)
        if isinstance(value, (abc.KeysView, abc.ValuesView, abc.ItemsView)):
            return list(value)
        if isinstance(value, dict):
            return list(value.keys())
        return list()

    @staticmethod
    def valid_date(str_date: str):
        """Validates if a string could be a date. This assumes a combination of year month day are the start
        of the string"""
        if not isinstance(str_date, str):
            return False
        try:
            mat = re.match('(\d{2})[/.-](\d{2})[/.-](\d{4}?)', str_date)
            if mat is not None:
                groups = tuple(mat.groups()[-1::-1])
                if int(groups[1]) > 12:
                    groups = (groups[0], groups[2], groups[1])
                datetime(*(map(int, groups)))
                return True
            mat = re.match('(\d{4})[/.-](\d{2})[/.-](\d{2}?)', str_date)
            if mat is not None:
                groups = tuple(mat.groups())
                if int(groups[1]) > 12:
                    groups = (groups[0], groups[2], groups[1])
                datetime(*(map(int, groups)))
                return True
        except ValueError:
            pass
        return False

    @staticmethod
    def bytes2human(size_bytes: int):
        """Converts byte value to a human-readable format"""
        if size_bytes == 0:
            return "0b"
        size_name = ("b", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s}{size_name[i]}"

    @staticmethod
    def param2dict(**kwargs):
        return dict((k, v) for (k, v) in locals().get('kwargs', {}).items() if v is not None)

    @staticmethod
    def dict_with_missing(base: dict, default: Any):
        """returns a dictionary with defining  __missing__() which returns the default value"""

        class DictMissing(dict):

            def __missing__(self, x):
                return default

        return DictMissing(base)

    @staticmethod
    def label_gen(limit: int=None, prefix: str=None) -> str:
        """generates a sequential headers. if limit is set will return at that limit. I prefix is set then
        adds a prefix to the start of the name.

        To use get the generator with gen = Commons.label_gen() then use next(gen) to retrieve the label
        """
        headers = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        prefix = prefix if isinstance(prefix, str) else ''
        counter = 0
        for n in range(0, 100):
            for i in range(len(headers)):
                rtn_str = f"{prefix}{headers[i]}" if n == 0 else f"{prefix}{headers[i]}{n}"
                if isinstance(limit, int) and counter >= limit:
                    return rtn_str
                counter += 1
                yield rtn_str

    @staticmethod
    def precision_scale(num: [int, float]) -> tuple:
        """Returns the precision and scale of a number"""
        max_digits = 14
        int_part = int(abs(num))
        magnitude = 1 if int_part == 0 else int(math.log10(int_part)) + 1
        if magnitude >= max_digits:
            return magnitude, 0
        frac_part = abs(num) - int_part
        multiplier = 10 ** (max_digits - magnitude)
        frac_digits = multiplier + int(multiplier * frac_part + 0.5)
        while frac_digits % 10 == 0:
            frac_digits /= 10
        scale = int(math.log10(frac_digits))
        return magnitude + scale, scale

    @staticmethod
    def list_equal(seq: list, other: list) -> bool:
        """checks if two lists are equal in count and frequency of elements, ignores order"""
        if not isinstance(seq, list):
            raise ValueError("The sequence must be of type 'list'")
        if not isinstance(other, list):
            raise ValueError("The sequence must be of type 'list'")
        if Counter(seq) == Counter(other):
            return True
        return False

    @staticmethod
    def list_diff(seq: list, other: list, symmetric: bool=True) -> list:
        """ Useful utility method to return the difference between two list where the list is unique.
        Symmetric set to True returns diff in both, False returns the difference of the first to the last"""
        if not isinstance(seq, list):
            raise ValueError("The sequence must be of type 'list'")
        if not isinstance(other, list):
            raise ValueError("The sequence must be of type 'list'")
        if isinstance(symmetric, bool) and symmetric:
            return list(set(set(seq).symmetric_difference(set(other))))
        return list(set(seq).difference(set(other)))

    @staticmethod
    def list_intersect(seq: list, other: list, symmetric: bool=True) -> list:
        """ Useful utility method to return the intersection between two list where the list is unique."""
        if not isinstance(seq, list):
            raise ValueError("The sequence must be of type 'list'")
        if not isinstance(other, list):
            raise ValueError("The sequence must be of type 'list'")
        return list(set(seq).intersection(set(other)))

    @staticmethod
    def list_union(seq: list, other: list, symmetric: bool=True) -> list:
        """ Useful utility method to return the union between two list where the list is unique."""
        if not isinstance(seq, list):
            raise ValueError("The sequence must be of type 'list'")
        if not isinstance(other, list):
            raise ValueError("The sequence must be of type 'list'")
        return list(set(seq).union(set(other)))

    @staticmethod
    def list_unique(seq: list) -> list:
        """ Useful utility method to retain the order of a list but removes duplicates"""
        if not isinstance(seq, list):
            raise ValueError("The sequence must be of type 'list'")
        seen = set()
        # Note: assign seen add to a local variable as local variable are less costly to resolve than dynamic call
        seen_add = seen.add
        # Note: seen.add() always returns None, the 'or' is only there to attempt to set update
        return [x for x in seq if not (x in seen or seen_add(x))]

    @staticmethod
    def list_resize(seq: list, resize: int) -> list:
        """resize a sequence list duplicating or removing sequence entries to fit to the new size. if the
        seq length and the resize length are not divisible, values are repeated or removed to make the length
            for example: [1,4,2] resized to 7 => [1,1,1,4,4,2,2] where the first index is repeated an additional time.
        """
        if not isinstance(seq, list):
            raise ValueError("The sequence must be of type 'list'")
        if len(seq) == 0:
            return [0] * resize
        seq_len = len(seq)
        rtn_counter = [int(round(resize / seq_len))] * seq_len
        shortfall = resize - sum(rtn_counter)
        for i in range(abs(shortfall)):
            if shortfall > 0:
                rtn_counter[rtn_counter.index(min(rtn_counter))] += 1
            elif shortfall < 0:
                rtn_counter[rtn_counter.index(max(rtn_counter))] -= 1
        rtn_seq = []
        for i in range(len(seq)):
            rtn_seq += [seq[i]] * rtn_counter[i]
        return rtn_seq

    @staticmethod
    def list_standardize(seq: list, precision: int=None) -> list:
        """standardise a numeric list"""
        if not isinstance(seq, list):
            raise ValueError("The sequence must be of type 'list'")
        if not all(isinstance(x, (int, float)) for x in seq):
            raise ValueError("The sequence must be a list of numeric values")
        precision = precision if isinstance(precision, int) else 5
        mean = sum(seq) / len(seq)
        variance = sum([((x - mean) ** 2) for x in seq]) / len(seq)
        std = variance ** 0.5
        return [round((x - mean)/std if std != 0 else 0, precision) for x in seq]

    @staticmethod
    def list_normalize(seq: list, a: [int, float], b: [int, float], precision: int=None) -> list:
        """Normalises a numeric list between a and b where min(x) and max(x) will normalise to a and b"""
        if not isinstance(seq, list):
            raise ValueError("The sequence must be of type 'list'")
        if not all(isinstance(x, (int, float)) for x in seq):
            raise ValueError("The sequence must be a list of numeric values")
        if a >= b:
            raise ValueError("a must be less than b where a is the lowest boundary and b the highest boundary")
        precision = precision if isinstance(precision, int) else 5
        seq_min = min(seq)
        seq_range = max(seq) - seq_min
        n_range = (b - a)
        return [round((n_range * ((x - seq_min) / seq_range)) + a, precision) for x in seq]

    @staticmethod
    def filter_headers(data: pa.Table, headers: [str, list]=None, d_type: pa.DataType=None, drop: bool=None,
                       regex: [str, list]=None) -> list:
        """ returns a list of headers based on the filter criteria

        :param data: the Canonical data to get the column headers from
        :param headers: a list of headers to drop or filter on type
        :param d_type: a li
        :param drop: to drop or not drop the selection
        :param regex: a regular expression to search the headers
        :return: a filtered list of headers

        :raise: TypeError if any of the types are not as expected
        """
        if not isinstance(data, pa.Table):
            raise TypeError("The first function attribute must be a pa.Table")
        drop = drop if isinstance(drop, bool) else False
        headers = CoreCommons.list_formatter(headers)
        regex = '|'.join(CoreCommons.list_formatter(regex))

        rtn_list = data.column_names
        if headers is not None and headers:
            _ = pc.is_in(rtn_list, pa.array(headers))
            rtn_list = pa.array(rtn_list).filter(_).to_pylist()
        if regex is not None and regex:
            _ = pc.extract_regex(rtn_list, regex).is_valid()
            rtn_list = pa.array(rtn_list).filter(_).to_pylist()
        if drop:
            return CoreCommons.list_diff(data.column_names, rtn_list)
        return rtn_list

    @staticmethod
    def filter_columns(data: pa.Table, headers=None, drop: bool=None, regex: [str, list]=None) -> pa.Table:
        """ Returns a subset of columns based on the filter criteria

        :param data: the Canonical data to get the column headers from
        :param headers: a list of headers to drop or filter on type
        :param drop: to drop or not drop the headers
        :param regex: a regular expression to search the headers
        :return:
        """
        return data.select(CoreCommons.filter_headers(data=data, headers=headers, drop=drop, regex=regex))

    @staticmethod
    def table_append(t1: pa.Table, t2: pa.Table):
        """ appends all the columns in t2 to t1 """
        if not isinstance(t2, pa.Table):
            raise ValueError("As a minimum, the second value passed must be a PyArrow Table")
        if not isinstance(t1, pa.Table):
            return t2
        if t1.shape[0] != t2.shape[0]:
            raise ValueError(f"The tables passed are not of equal row size. "
                             f"The first has '{t1.shape[0]}' rows and the second has '{t2.shape[0]}' rows")
        for c in t2.column_names:
            t1 = t1.append_column(c, t2.column(c))
        return t1

    @staticmethod
    def table_flatten(t :pa.Table):
        """ flattens a table of lists and struct data types """
        working = True

        while working:
            working = False
            for idx in range(len(t.column_names)):
                c = t.column_names[idx]
                record = t.column(c).combine_chunks()
                if pa.types.is_list(record.type):
                    for i in range(pc.min(pc.list_value_length(record)).as_py()):
                        t = t.append_column(f'{c}.{i}', pc.list_element(t.column(c), i).combine_chunks())
                    t = t.drop_columns(c)
                    working = True
                if pa.types.is_struct(record.type):
                    t = t.flatten()
                    working = True
        return t

    @staticmethod
    def table_nest(t: pa.Table) -> list:
        """ turns a flattened table back to a nested pattern """

        def set_dict(tree, vector, value):
            key = vector[0]
            tree[key] = value if len(vector) == 1 else set_dict(tree[key] if key in tree else {}, vector[1:], value)
            return tree

        def set_list(struct, keys, tree):
            for key in tuple(struct.keys()):
                if isinstance(struct.get(key), dict) and len(struct.get(key)) > 0:
                    keys.append(key)
                    set_list(struct.get(key), keys, tree)
                if str(key).isnumeric():
                    snippet = list([struct.get(key, {})])
                    if snippet[0] == {}:
                        continue
                    branch = tree
                    for k in keys[:-1]:
                        branch = branch.get(k)
                    snippet = list(struct.values())
                    struct.clear()
                    branch[keys[-1]] = snippet
            if len(keys) > 0:
                keys.pop()
            return tree

        rtn_lst = []
        for idx in range(t.num_rows):
            rtn_value = {}
            for n in t.column_names:
                values = t.column(n).to_pylist()
                rtn_value = set_dict(rtn_value, n.split('.'), values[idx])
            rtn_value = set_list(rtn_value, [], rtn_value)
            rtn_lst.append(rtn_value)
        return rtn_lst

    @staticmethod
    def column_cast(a: pa.Array, ty: pa.DataType) -> pa.Array:
        """ attempt to cast a pyarrow array to the given type """
        try:
            return a.cast(ty)
        except (ArrowInvalid, ArrowTypeError, ArrowNotImplementedError):
            return a

    @staticmethod
    def table_cast(t: pa.Table, cat_max: int=None):
        """ attempt to cast a pyarrow table columns to the given type """
        cat_max = cat_max if isinstance(cat_max, int) else 40
        rtn_tbl = None
        for n in t.column_names:
            c = t.combine_chunks().column(n)
            if pa.types.is_string(c.type):
                c = CoreCommons.column_cast(c, pa.timestamp('ns'))
            if pa.types.is_string(c.type):
                c = CoreCommons.column_cast(c, pa.float64())
            if pa.types.is_floating(c.type):
                c = CoreCommons.column_cast(c, pa.int64())
            if pa.types.is_integer(c.type) and c.drop_null().unique().sort().equals(pa.array([0, 1])):
                c = CoreCommons.column_cast(c, pa.bool_())
            if pa.types.is_string(c.type) and pc.count_distinct(c.drop_null()).equals(pa.scalar(2)):
                c = CoreCommons.column_cast(c, pa.bool_())
            if pa.types.is_string(c.type) and 1 <= pc.count_distinct(c.drop_null()).as_py() <= cat_max:
                c = c.dictionary_encode()
            rtn_tbl = CoreCommons.table_append(rtn_tbl, pa.table([c], names=[n]))
        return rtn_tbl


class AnalyticsSection(object):
    """A section  subset of the analytics"""

    _section = {}

    def __init__(self, section: dict):
        """pass a section dictionary that is a subset dictionary of attributes"""
        self._section = section
        for k, v in self._section.items():
            self._add_property(k, v)

    def elements(self) -> list:
        """return the list of available element names"""
        return list(self._section.keys())

    def items(self):
        """return the list of available element names"""
        return self._section.items()

    def is_element(self, element: str):
        """Checks if an element exists in the section"""
        if element in self.elements():
            return True
        return False

    def get(self, element: str, default: Any=None):
        """returns a specific name from a section"""
        return self._section.get(element, default)

    def _add_property(self, name: str, rtn_value: Any):
        _method = self._make_method(rtn_value)
        setattr(self, name, _method)

    @staticmethod
    def _make_method(rtn_value: Any):
        @property
        def _method() -> type(rtn_value):
            return rtn_value
        return _method.fget()

    def to_dict(self):
        return self._section.copy()

    def __len__(self):
        return self._section.__len__()

    def __str__(self):
        return self._section.__str__()

    def __repr__(self):
        return f"<{self.__class__.__name__} {self._section.__str__()}"

    def __eq__(self, other: dict):
        return self._section.__eq__(other)

    def __delattr__(self, element):
        raise AttributeError(
            "{} is an immutable class and elements cannot be removed".format(self.__class__.__name__))


class DataAnalytics(object):
    """Analytics abstraction to store the analytics dictionary in a structured set of properties"""

    def __init__(self, analysis: dict):
        """pass an analysis dictionary that is a dictionary of dictionaries"""
        if not isinstance(analysis, dict) or len(analysis) == 0:
            raise ValueError("The passed analysis is not a dictionary or is of zero length")
        self._analysis = analysis.copy()
        for k, v in self._analysis.items():
            self._add_property(k, AnalyticsSection(v))

    @property
    def section_names(self) -> list:
        """return the list of available section names"""
        return list(self._analysis.keys())

    @property
    def sections(self) -> list:
        """return the list of available sections as AnalyticsSection"""
        return list(self._analysis.values())

    def is_section(self, section: str):
        """Checks if a section exists in the sections available"""
        if section in self.section_names:
            return True
        return False

    def get(self, section: str, default: Any=None):
        """returns a specific attribute from a section"""
        if self.is_section(section):
            return eval(f"self.{section}")
        if default is not None:
            return default
        return {}

    def _add_property(self, name: str, rtn_value: Any):
        _method = self._make_method(rtn_value)
        setattr(self, name, _method)

    @staticmethod
    def _make_method(rtn_value: Any):
        @property
        def _method() -> type(rtn_value):
            return rtn_value
        return _method.fget()

    def to_dict(self):
        return self._analysis.copy()

    def __len__(self):
        return self._analysis.__len__()

    def __str__(self):
        return self._analysis.__str__()

    def __repr__(self):
        return f"<{self.__class__.__name__} {self._analysis.__str__()}"

    def __eq__(self, other: dict):
        return self._analysis.__eq__(other)

    @staticmethod
    def get_tree_roots(analytics_blob: dict) -> list:
        """ given an analytics blob, returns the tree branch paths for the individual Data Analytics

        :param analytics_blob: an analytics blob created through associative analytics
        :return: the list of branch names
        """

        def get_level(_analysis: dict, tree: list):
            for name, values in _analysis.items():
                tree.append(values.get('branch', {}).get('root', ''))
                if values.get('sub_category'):
                    for section in values.get('sub_category', {}):
                        get_level(values.get('sub_category', {}).get(section, {}), tree)
            return tree

        return get_level(_analysis=analytics_blob, tree=list())

    @staticmethod
    def from_root(analytics_blob: dict, root: str) -> DataAnalytics:
        """ given a root, returns the Data Analytics tree branch as a dictionary

        :param analytics_blob: an analytics blob created through associative analytics
        :param root: the analytics blob root to the branch
        :return: the Data Analytics on the branch
        """
        keys = root.split('.')
        result = analytics_blob.copy()
        is_index = False
        label = None
        for k in keys:
            if is_index:
                idx = int(k)
                leaves = result.get(label).get('branch', {}).get('leaves', [])
                result = result.get(label).get('sub_category', {}).get(leaves[idx], {})
            else:
                label = k
            is_index = not is_index
        result = result.get(label, {}).get('insight', {})
        return DataAnalytics(analysis=result)

    @staticmethod
    def build_category(header: str, lower: [int, float]=None, upper: [int, float]=None, top: int=None,
                       nulls_list: list=None, replace_zero: [int, float]=None, freq_precision: int=None) -> dict:
        return DataAnalytics._build_params(**locals())

    @staticmethod
    def build_number(header: str, granularity: Any=None, lower: [int, float]=None,
                     upper: [int, float]=None, precision: int=None, freq_precision: int=None,
                     dominant: [int, float, list]=None, exclude_dominant: bool=None, detail_stats: bool=None,
                     p_percent: float=None, replicates: int=None) -> dict:
        return DataAnalytics._build_params(**locals())

    @staticmethod
    def build_date(header: str, granularity: Any=None, lower: Any=None, upper: Any=None, day_first: bool=None,
                     year_first: bool=None, date_format: str=None, freq_precision: int=None) -> dict:
        return DataAnalytics._build_params(**locals())

    @staticmethod
    def _build_params(**kwargs):
        params = dict((k, v) for (k, v) in locals().get('kwargs', {}).items() if v is not None)
        header = params.pop('header')
        return {header: {**params}}
