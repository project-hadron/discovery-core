import unittest
import os
import shutil
import pyarrow as pa
from ds_core.components.core_commons import DataAnalytics, CoreCommons
from ds_core.properties.property_manager import PropertyManager


class CommonsTest(unittest.TestCase):

    def setUp(self):
        os.environ['HADRON_PM_PATH'] = os.path.join('work', 'config')
        os.environ['HADRON_DEFAULT_PATH'] = os.path.join('work', 'data')
        try:
            os.makedirs(os.environ['HADRON_PM_PATH'])
            os.makedirs(os.environ['HADRON_DEFAULT_PATH'])
        except:
            pass
        PropertyManager._remove_all()

    def tearDown(self):
        try:
            shutil.rmtree('work')
        except:
            pass

    def test_table_append(self):
        t1 = pa.Table.from_pydict({'A': [1,2], 'B': [1,3], 'C': [2,4]})
        t2 = pa.Table.from_pydict({'X': [4,5], 'Y': [6,7]})
        result = CoreCommons.table_append(t1, t2)
        self.assertEqual((2, 3),t1.shape)
        self.assertEqual(['A', 'B', 'C'],t1.column_names)
        self.assertEqual((2, 2),t2.shape)
        self.assertEqual(['X', 'Y'],t2.column_names)
        self.assertEqual((2, 5),result.shape)
        self.assertEqual(['A', 'B', 'C', 'X', 'Y'], result.column_names)
        result = CoreCommons.table_append(None, t2)
        self.assertEqual((2, 2),result.shape)
        self.assertEqual(['X', 'Y'],result.column_names)
        t3 = pa.Table.from_pydict({'X': [4, 5, 6], 'Y': [6, 7, 8]})
        with self.assertRaises(ValueError) as context:
            result = CoreCommons.table_append(t1, t3)
        self.assertTrue("The tables passed are not of equal row size. The first has '2' rows and the second has '3' rows" in str(context.exception))
        with self.assertRaises(ValueError) as context:
            result = CoreCommons.table_append(t1, None)
        self.assertTrue("As a minimum, the second value passed must be a PyArrow Table" in str(context.exception))

    def test_table_flatten(self):
        document = [
            {"_id": "PI1832341",
             "interactionDate": {"startDateTime": "2023-01-02 04:49:06.955000",
                                 "endDateTime": "2023-01-02 04:50:35.130000"},
             "relatedParty": [{"_id": "C5089669",
                               "role": "Customer",
                               "engagedParty": {"referredType": "Individual"}},
                              {"_id": "dclmappuser1",
                               "role": "CSRAgent"}],
             "productId": ["PR716796"],
             }
        ]
        tbl = pa.Table.from_pylist(document)
        result = CoreCommons.table_flatten(tbl)
        control = ['_id',
                   'interactionDate.endDateTime', 'interactionDate.startDateTime',
                   'relatedParty.nest_list_0._id', 'relatedParty.nest_list_0.engagedParty.referredType', 'relatedParty.nest_list_0.role',
                   'relatedParty.nest_list_1._id', 'relatedParty.nest_list_1.engagedParty.referredType', 'relatedParty.nest_list_1.role',
                   'productId.nest_list_0']
        self.assertEqual(control, result.column_names)

    def test_table_nest(self):
        document = [
            {"_id": "PI1832341",
             "interactionDate": {"startDateTime": "2023-01-02 04:49:06.955000",
                                 "endDateTime": "2023-01-02 04:50:35.130000"},
             "relatedParty": [{"_id": "C5089669",
                               "role": "Customer",
                               "engagedParty": {"referredType": "Individual"}},
                              {"_id": "dclmappuser1",
                               "role": "CSRAgent"}],
             "productId": ["PR716796"],
             }
        ]
        tbl = CoreCommons.table_flatten(pa.Table.from_pylist(document))
        result = CoreCommons.table_nest(tbl)
        self.assertCountEqual(['_id', 'interactionDate', 'relatedParty', 'productId'], result[0].keys())
        self.assertIsInstance(result[0].get('relatedParty'), list)
        self.assertEqual(len(result[0].get('relatedParty')), 2)

    def test_array_cast(self):
        num = pa.array([1.0, 12.0, 5.0, None], pa.float64())
        date = pa.array(["2023-01-02 04:49:06", "2023-01-02 04:57:12", None, "2023-01-02 05:23:50"], pa.string())
        text = pa.array(["Blue", "Green", None, 'Blue'], pa.string())
        bool1 = pa.array([1, 0, 1, None], pa.int64())
        bool2 = pa.array(['true', 'true', None, 'false'], pa.string())
        bool3 = pa.array([None, 'no', 'yes', 'yes'], pa.string())
        # ensure it doesn't fall over
        for c in [num, date, text, bool1, bool2, bool3]:
            for ty in [pa.string(),pa.int64(),pa.float64(),pa.timestamp('ns'),pa.bool_(),pa.null(),]:
                _ = CoreCommons.column_cast(c, ty)
        self.assertEqual(pa.int64(), CoreCommons.column_cast(num, pa.int64()).type)
        self.assertEqual(pa.timestamp('ns'), CoreCommons.column_cast(date, pa.timestamp('ns')).type)
        self.assertEqual(pa.string(), CoreCommons.column_cast(text, pa.string()).type)
        self.assertEqual(pa.bool_(), CoreCommons.column_cast(bool1, pa.bool_()).type)
        self.assertEqual(pa.bool_(), CoreCommons.column_cast(bool2, pa.bool_()).type)
        self.assertEqual(pa.string(), CoreCommons.column_cast(bool3, pa.bool_()).type)

    def test_table_cast(self):
        num = pa.array([1.0, 12.0, 5.0, None], pa.float64())
        date = pa.array(["2023-01-02 04:49:06", "2023-01-02 04:57:12", None, "2023-01-02 05:23:50"], pa.string())
        value = pa.array([None, '1.5', '3.2', '2.0'], pa.string())
        text = pa.array(["Blue", "Green", None, 'Red'], pa.string())
        bool1 = pa.array([1, 0, 1, None], pa.int64())
        bool2 = pa.array(['true', 'true', None, 'false'], pa.string())
        bool3 = pa.array([None, 'M', 'F', 'M'], pa.string())
        tbl = pa.table([num, value, date, text, bool1, bool2, bool3],
                       names=['num', 'value', 'date', 'text', 'bool1', 'bool2', 'bool3'])
        result = CoreCommons.table_cast(tbl).combine_chunks()
        control = pa.schema([('num', pa.int64()),
                             ('value', pa.float64()),
                             ('date', pa.timestamp('ns')),
                             ('text', pa.dictionary(pa.int32(), pa.string())),
                             ('bool1', pa.bool_()),
                             ('bool2', pa.bool_()),
                             ('bool3', pa.dictionary(pa.int32(), pa.string())),
                             ])
        self.assertEqual(control, result.schema)
        result = CoreCommons.table_cast(tbl, cat_max=2).combine_chunks()
        control = pa.schema([('num', pa.int64()),
                             ('value', pa.float64()),
                             ('date', pa.timestamp('ns')),
                             ('text', pa.string()),
                             ('bool1', pa.bool_()),
                             ('bool2', pa.bool_()),
                             ('bool3', pa.dictionary(pa.int32(), pa.string())),
                             ])
        self.assertEqual(control, result.schema)

    def test_filter_headers(self):
        num = pa.array([1.0, 12.0, 5.0, None], pa.float64())
        date = pa.array(["2023-01-02 04:49:06", "2023-01-02 04:57:12", None, "2023-01-02 05:23:50"], pa.string())
        value = pa.array([None, '1.5', '3.2', '2.0'], pa.string())
        text = pa.array(["Blue", "Green", None, 'Red'], pa.string())
        bool1 = pa.array([1, 0, 1, None], pa.int64())
        bool2 = pa.array(['true', 'true', None, 'false'], pa.string())
        cat = pa.array([None, 'M', 'F', 'M'], pa.string())
        tbl = pa.table([num, value, date, text, bool1, bool2, cat],
                       names=['num', 'value', 'date', 'text', 'bool1', 'bool2', 'cat'])
        result = CoreCommons.filter_headers(tbl)
        self.assertEqual(tbl.column_names, result)
        result = CoreCommons.filter_headers(tbl, headers=['num', 'value', 'text'])
        self.assertCountEqual(['num', 'value', 'text'], result)
        result = CoreCommons.filter_headers(tbl, regex=['t', 'value'])
        self.assertCountEqual(['value', 'date', 'text', 'cat'], result)
        result = CoreCommons.filter_headers(tbl, regex=['t', 'value'], drop=True)
        self.assertCountEqual(['bool1', 'bool2', 'num'], result)
        result = CoreCommons.filter_headers(tbl, headers=['value', 'text', 'bool1'], regex='e')
        self.assertCountEqual(['value', 'text'], result)

    def test_filter_columns(self):
        num = pa.array([1.0, 12.0, 5.0, None], pa.float64())
        date = pa.array(["2023-01-02 04:49:06", "2023-01-02 04:57:12", None, "2023-01-02 05:23:50"], pa.string())
        value = pa.array([None, '1.5', '3.2', '2.0'], pa.string())
        text = pa.array(["Blue", "Green", None, 'Red'], pa.string())
        tbl = pa.table([num, value, date, text], names=['num', 'value', 'date', 'text'])
        result = CoreCommons.filter_columns(tbl, headers=['num', 'date'])
        self.assertCountEqual(['num', 'date'], result.column_names)

    def test_list_formatter(self):
        sample = {'A': [1,2], 'B': [1,2], 'C': [1,2]}
        result = CoreCommons.list_formatter(sample)
        self.assertEqual(list("ABC"), result)
        result = CoreCommons.list_formatter(sample.keys())
        self.assertEqual(list("ABC"), result)
        result = CoreCommons.list_formatter("A")
        self.assertEqual(['A'], result)

    def test_presision_scale(self):
        sample = 1
        self.assertEqual((1, 0), CoreCommons.precision_scale(sample))
        sample = 729.0
        self.assertEqual((3, 0), CoreCommons.precision_scale(sample))
        sample = 729.4
        self.assertEqual((4, 1), CoreCommons.precision_scale(sample))
        sample = 0.456
        self.assertEqual((4, 3), CoreCommons.precision_scale(sample))
        sample = 2784.45612367432
        self.assertEqual((14, 10), CoreCommons.precision_scale(sample))
        sample = -3.72
        self.assertEqual((3, 2), CoreCommons.precision_scale(sample))
        sample = -4
        self.assertEqual((1, 0), CoreCommons.precision_scale(sample))

    def test_list_standardize(self):
        seq = [100, 75, 50, 25, 0]
        result = CoreCommons.list_standardize(seq=seq)
        self.assertEqual(0.0, result[2])
        self.assertEqual(0.0, result[1] + result[3])
        self.assertEqual(0.0, result[0] + result[4])

    def test_list_normalize(self):
        seq = [100, 75, 50, 25, 0]
        a = 0
        b = 1
        result = CoreCommons.list_normalize(seq=seq, a=a, b=b)
        self.assertEqual([1.0, 0.75, 0.5, 0.25, 0.0], result)
        a = -1
        b = 1
        result = CoreCommons.list_normalize(seq=seq, a=a, b=b)
        self.assertEqual([1.0, 0.5, 0, -0.5, -1], result)

    def test_diff(self):
        a = [1,2,3,4]
        b = [2,3,4,6,7]
        self.assertEqual([1, 6, 7], CoreCommons.list_diff(a, b))
        self.assertEqual([1], CoreCommons.list_diff(a, b, symmetric=False))

    def test_intersect(self):
        a = [1,2,3,3]
        b = [2,3,4,6,7]
        self.assertEqual([2, 3], CoreCommons.list_intersect(a, b))

    def test_is_list_equal(self):
        a = [1, 4, 2, 1, 4]
        b = [4, 2, 4, 1, 1]
        self.assertTrue(CoreCommons.list_equal(a, b))
        b = [4, 2, 4, 2, 1]
        self.assertFalse(CoreCommons.list_equal(a, b))

    def test_resize_list(self):
        seq = [1,2,3,4]
        for size in range(10):
            result = CoreCommons.list_resize(seq=seq, resize=size)
            self.assertEqual(size, len(result))
            if len(result) >= 4:
                self.assertEqual(seq, CoreCommons.list_unique(result))

    def test_dict_builder(self):
        result = CoreCommons.param2dict()
        self.assertEqual({}, result)
        result = CoreCommons.param2dict(a=1, b='B')
        self.assertEqual({'a': 1, 'b': 'B'}, result)
        result = CoreCommons.param2dict(a=1, b=[1, 2, 3])
        self.assertEqual({'a': 1, 'b': [1, 2, 3]}, result)
        result = CoreCommons.param2dict(a={'A': 1})
        self.assertEqual({'a': {'A': 1}}, result)
        result = CoreCommons.param2dict(a=1, b=None)
        self.assertEqual({'a': 1}, result)

    def test_dict_with_missing(self):
        default = 'no value'
        sample = CoreCommons.dict_with_missing({}, default)
        result = sample['key']
        self.assertEqual(default, result)

    def test_bytestohuman(self):
        result = CoreCommons.bytes2human(1024)
        self.assertEqual('1.0KB', result)
        result = CoreCommons.bytes2human(1024 ** 2)
        self.assertEqual('1.0MB', result)
        result = CoreCommons.bytes2human(1024 ** 3)
        self.assertEqual('1.0GB', result)

    def test_validate_date(self):
        str_date = '2017/01/23'
        self.assertTrue(CoreCommons.valid_date(str_date))
        str_date = '2017/23/01'
        self.assertTrue(CoreCommons.valid_date(str_date))
        str_date = '23-01-2017'
        self.assertTrue(CoreCommons.valid_date(str_date))
        str_date = '01-21-2017'
        self.assertTrue(CoreCommons.valid_date(str_date))
        str_date = 'NaT'
        self.assertFalse(CoreCommons.valid_date(str_date))
        str_date = ''
        self.assertFalse(CoreCommons.valid_date(str_date))
        str_date = '01-21-2017 21:12:46'
        self.assertTrue(CoreCommons.valid_date(str_date))

    def test_analytics(self):
        analysis = {'intent': {'categories': ['a', 'b'], 'dtype': 'category'},
                    'patterns': {'relative_freq': [.6, .4], 'unique_count': 2}}
        result = DataAnalytics(analysis)
        self.assertEqual(['a', 'b'], result.get('intent').get('categories', []))
        self.assertEqual([], result.get('no_name', []))
        self.assertEqual({}, result.get('no_name'))
        self.assertEqual(['a', 'b'], result.intent.categories)
        self.assertEqual('category', result.intent.dtype)
        self.assertEqual(['categories', 'dtype'], result.intent.elements())

    def test_analysis_build(self):
        result = DataAnalytics.build_category(header='gender', lower=0.1, nulls_list=['', ' '])
        self.assertEqual({'gender': {'lower': 0.1, 'nulls_list': ['', ' ']}}, result)
        result = DataAnalytics.build_number(header='age', lower=0.1, upper=100, precision=2)
        self.assertEqual({'age': {'lower': 0.1, 'upper': 100, 'precision': 2}}, result)
        result = DataAnalytics.build_date(header='birth', granularity=4, year_first=True)
        self.assertEqual({'birth': {'granularity': 4, 'year_first': True}}, result)

    def test_label_gen(self):
        gen = CoreCommons.label_gen()
        result = next(gen)
        self.assertTrue('A', result)
        result = [next(gen) for x in range(5)]
        self.assertTrue(['B', 'C', 'D', 'E', 'F'], result)

    def test_raise(self):
        with self.assertRaises(KeyError) as context:
            env = os.environ['NoEnvValueTest']
        self.assertTrue("'NoEnvValueTest'" in str(context.exception))


if __name__ == '__main__':
    unittest.main()
