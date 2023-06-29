import unittest
import os
import shutil

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
