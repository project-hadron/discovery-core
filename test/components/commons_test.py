import ast
import unittest
import os
import shutil
from pprint import pprint

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from ds_core.components.core_commons import DataAnalytics, CoreCommons
from ds_core.properties.property_manager import PropertyManager


class CommonsTest(unittest.TestCase):

    def setUp(self):
        os.environ['HADRON_PM_PATH'] = "event://pm_story"
        os.environ['HADRON_DEFAULT_PATH'] = "event://data"
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
        t2 = pa.Table.from_pydict({'X': [4,5], 'A': [4,7]})
        result = CoreCommons.table_append(t1, t2)
        self.assertEqual((2, 3),t1.shape)
        self.assertEqual(['A', 'B', 'C'],t1.column_names)
        self.assertEqual((2, 2),t2.shape)
        self.assertEqual(['X', 'A'],t2.column_names)
        self.assertEqual((2, 4),result.shape)
        self.assertEqual(['B', 'C', 'X', 'A'], result.column_names)
        result = CoreCommons.table_append(None, t2)
        self.assertEqual((2, 2),result.shape)
        self.assertEqual(['X', 'A'],result.column_names)
        t3 = pa.Table.from_pydict({'X': [4, 5, 6], 'A': [6, 7, 8]})
        with self.assertRaises(ValueError) as context:
            result = CoreCommons.table_append(t1, t3)
        self.assertTrue("The tables passed are not of equal row size. The first has '2' rows and the second has '3' rows" in str(context.exception))
        with self.assertRaises(ValueError) as context:
            result = CoreCommons.table_append(t1, None)
        self.assertTrue("As a minimum, the second value passed must be a PyArrow Table" in str(context.exception))

    def test_table_flatten_file(self):
        # Individual
        with open('../_data/Individual.txt') as f:
            document = ast.literal_eval(f.read())
        print("\n Individual")
        pprint(document[:1])
        tbl = pa.Table.from_pylist(document)
        f_tbl = CoreCommons.table_flatten(tbl)
        result = CoreCommons.table_nest(f_tbl)
        pprint(result[:1])

        # PartyInteraction
        with open('../_data/PartyInteraction.txt') as f:
            document = ast.literal_eval(f.read())
        print("\n PartyInteraction")
        pprint(document[:1])
        tbl = pa.Table.from_pylist(document)
        f_tbl = CoreCommons.table_flatten(tbl)
        result = CoreCommons.table_nest(f_tbl)
        pprint(result[:1])

        # Organisation
        with open('../_data/Organization.txt') as f:
            document = ast.literal_eval(f.read())
        print("\n Organisation")
        pprint(document[:1])
        tbl = pa.Table.from_pylist(document)
        f_tbl = CoreCommons.table_flatten(tbl)
        result = CoreCommons.table_nest(f_tbl)
        pprint(result[:1])

    def test_table_flatten(self):
        document = [
            {"_id": "I35138", "contactMedium": [{"medium": {"number": "50070028", "type": "mobile"}, "preferred": True}, {"medium": {"emailAddress": "mail@stc.com.kw", "type": "emailAddress"}, "preferred": True}], "gender": "M", "familyName": "Fouad", "givenName": "Fouad", "middleName": "Fouad"},
            {"_id": "I35145", "contactMedium": [{"medium": {"emailAddress": "panneer.rajadurai.c@solutions.com.kw", "type": "EmailAddress"}, "preferred": True}, {"medium": {"number": "51658317", "type": "mobile"}, "preferred": True}, {"medium": {"number": "51658317", "type": "whatsapp"}, "preferred": False}, {"medium": {"number": "51658317", "type": "telegram"}, "preferred": False}, {"medium": {"type": "telephone"}, "role": "AlternateNumber"}], "gender": "M", "familyName": "Jay", "givenName": "Bhuvana", "middleName": ""},
            {"_id": "I35146", "contactMedium": [{"medium": {"emailAddress": "bhuvana.stc21@gmail.com", "type": "EmailAddress"}, "preferred": True}, {"medium": {"type": "mobile"}, "preferred": False}, {"medium": {"type": "whatsapp"}, "preferred": False}, {"medium": {"type": "telegram"}, "preferred": False}], "gender": "F", "familyName": "CORP", "givenName": "TECNOTREE", "middleName": "LTD"},
            {"_id": "I35178", "contactMedium": [{"medium": {"emailAddress": "m.m.alkhoduri@outlook.com", "type": "emailAddress"}, "preferred": True}, {"medium": {"number": "55850055", "type": "mobile"}, "preferred": True}, {"medium": {"number": "55850055", "type": "whatsapp"}, "preferred": False}, {"medium": {"number": "55850055", "type": "telegram"}, "preferred": False}], "gender": "M", "familyName": "", "givenName": "MohammadalKoduri", "middleName": ""},
            {"_id": "I35179", "contactMedium": [{"medium": {"emailAddress": "ahb@bremenintl.com", "type": "emailAddress"}, "preferred": True}, {"medium": {"number": "51500014", "type": "mobile"}, "preferred": True}, {"medium": {"number": "51500014", "type": "whatsapp"}, "preferred": False}, {"medium": {"number": "51500014", "type": "telegram"}, "preferred": False}], "gender": "M", "familyName": "", "givenName": "AhmedBakhiet", "middleName": ""},
            {"_id": "I35180", "contactMedium": [{"medium": {"emailAddress": "test@gmail.com", "type": "emailAddress"}, "preferred": True}], "gender": "M", "familyName": "Admin", "givenName": "FakhrTest", "middleName": ""},
            {"_id": "I35181", "contactMedium": [], "gender": "M", "familyName": "test", "givenName": "test", "nationality": "", "middleName": ""}
        ]
        tbl = pa.Table.from_pylist(document)
        result = CoreCommons.table_flatten(tbl)
        control = CoreCommons.filter_headers(result, regex='nest_list_', drop=True)
        self.assertCountEqual(['middleName', 'gender', '_id', 'givenName', 'familyName'], control)
        control = len(CoreCommons.filter_headers(result, regex='nest_list_'))
        self.assertEqual(16, control)

    def test_table_nest(self):
        document = [
            {"_id": "I35138", "contactMedium": [{"medium": {"number": "50070028", "type": "mobile"}, "preferred": True}, {"medium": {"emailAddress": "mail@stc.com.kw", "type": "emailAddress"}, "preferred": True}], "gender": "M", "familyName": "Fouad", "givenName": "Fouad", "middleName": "Fouad"},
            {"_id": "I35145", "contactMedium": [{"medium": {"emailAddress": "panneer.rajadurai.c@solutions.com.kw", "type": "EmailAddress"}, "preferred": True}, {"medium": {"number": "51658317", "type": "mobile"}, "preferred": True}, {"medium": {"number": "51658317", "type": "whatsapp"}, "preferred": False}, {"medium": {"number": "51658317", "type": "telegram"}, "preferred": False}, {"medium": {"type": "telephone"}, "role": "AlternateNumber"}], "gender": "M", "familyName": "Jay", "givenName": "Bhuvana", "middleName": ""},
            {"_id": "I35146", "contactMedium": [{"medium": {"emailAddress": "bhuvana.stc21@gmail.com", "type": "EmailAddress"}, "preferred": True}, {"medium": {"type": "mobile"}, "preferred": False}, {"medium": {"type": "whatsapp"}, "preferred": False}, {"medium": {"type": "telegram"}, "preferred": False}], "gender": "F", "familyName": "CORP", "givenName": "TECNOTREE", "middleName": "LTD"},
            {"_id": "I35178", "contactMedium": [{"medium": {"emailAddress": "m.m.alkhoduri@outlook.com", "type": "emailAddress"}, "preferred": True}, {"medium": {"number": "55850055", "type": "mobile"}, "preferred": True}, {"medium": {"number": "55850055", "type": "whatsapp"}, "preferred": False}, {"medium": {"number": "55850055", "type": "telegram"}, "preferred": False}], "gender": "M", "familyName": "", "givenName": "MohammadalKoduri", "middleName": ""},
            {"_id": "I35179", "contactMedium": [{"medium": {"emailAddress": "ahb@bremenintl.com", "type": "emailAddress"}, "preferred": True}, {"medium": {"number": "51500014", "type": "mobile"}, "preferred": True}, {"medium": {"number": "51500014", "type": "whatsapp"}, "preferred": False}, {"medium": {"number": "51500014", "type": "telegram"}, "preferred": False}], "gender": "M", "familyName": "", "givenName": "AhmedBakhiet", "middleName": ""},
            {"_id": "I35180", "contactMedium": [{"medium": {"emailAddress": "test@gmail.com", "type": "emailAddress"}, "preferred": True}], "gender": "M", "familyName": "Admin", "givenName": "FakhrTest", "middleName": ""},
            {"_id": "I35181", "contactMedium": [], "gender": "M", "familyName": "test", "givenName": "test", "nationality": "", "middleName": ""}
        ]
        tbl = CoreCommons.table_flatten(pa.Table.from_pylist(document))
        result = CoreCommons.table_nest(tbl)
        self.assertCountEqual(['_id', 'gender', 'familyName', 'givenName', 'middleName', 'contactMedium'], result[0].keys())
        self.assertIsInstance(result[0].get('contactMedium'), list)
        self.assertEqual(len(result[0].get('contactMedium')), 2)
        self.assertEqual(len(result[1].get('contactMedium')), 5)
        self.assertEqual(len(result[2].get('contactMedium')), 4)
        self.assertCountEqual(['_id', 'gender', 'familyName', 'givenName', 'middleName'], result[6].keys())
        pprint(result[:1])

    def test_table_nest_list(self):
        document = [{'a' : [{'b': 1, 'c': [{'z': 6}]},
                            {'c': [{'z': 4}]}]
                     }]
        tbl = CoreCommons.table_flatten(pa.Table.from_pylist(document))
        self.assertEqual(tbl.column_names , ['a.nest_list_0.b', 'a.nest_list_0.c.nest_list_0.z', 'a.nest_list_1.c.nest_list_0.z'] )
        result = CoreCommons.table_nest(tbl)
        self.assertEqual(result,  [{'a': [{'b': 1, 'c': [{'z': 6}]}, {'c': [{'z': 4}]}]}])

    def test_nest_list_order(self):
        document = [{'name': [{'state': 'AZ'},]},
                    {'name': [{'city': 'Fredville'},
                             {'state': 'VA'},]},
                    {'name': [{'state': 'TX'},
                              {'city': 'Georgetown'},]},]
        tbl = CoreCommons.table_flatten(pa.Table.from_pylist(document), flatten_list=False)
        print(CoreCommons.tbl)




    def test_table_nest_flatten(self):
        num = pa.array([1.0, 12.0, 5.0, None], pa.float64())
        val = pa.array([7, None, 3, 5], pa.int64())
        date = pc.strptime(["2023-01-02 04:49:06", "2023-01-02 04:57:12", None, "2023-01-02 05:23:50"], format='%Y-%m-%d %H:%M:%S', unit='ns')
        text = pa.array(["Blue", "Green", None, 'Red'], pa.string())
        binary = pa.array([True, True, None, False], pa.bool_())
        cat = pa.array([None, 'M', 'F', 'M'], pa.string()).dictionary_encode()
        tbl = pa.table([num, val, date, text, binary, cat],
                       names=['num', 'int', 'date', 'text', 'bool', 'cat'])
        result = CoreCommons.table_nest(tbl)
        pprint(result)
        print('')
        t = pa.Table.from_pylist(result)
        print(t.schema)
        print('')
        result = CoreCommons.table_flatten(t)
        print(result.schema)


    def test_column_precision(self):
        num = pa.array([1.471, 12, 5.33, None], pa.float64())
        text = pa.array(["Blue", "Green", None, 'Blue'], pa.string())
        val = pa.array([1, 0, 1, None], pa.int64())
        result = CoreCommons.column_precision(num)
        self.assertEqual(3, result)
        result = CoreCommons.column_precision(val)
        self.assertEqual(0, result)
        with self.assertRaises(ValueError) as context:
            result = CoreCommons.column_precision(text)
        self.assertTrue("The array should be numeric, type 'string' sent." in str(context.exception))

    def test_column_join(self):
        a = pa.array([1,2,3,4,5])
        b = pa.array(list('abcde'))
        c = CoreCommons.column_join(a,b)
        self.assertEqual(['1a', '2b', '3c', '4d', '5e'], c.to_pylist())
        c = CoreCommons.column_join(a,b,sep='_')
        self.assertEqual(['1_a', '2_b', '3_c', '4_d', '5_e'], c.to_pylist())

    def test_array_cast(self):
        num = pa.array([1.0, 12.0, 5.0, None], pa.float64())
        date = pc.strptime(["2023-01-02 04:49:06", "2023-01-02 04:57:12", None, "2023-01-02 05:23:50"], format='%Y-%m-%d %H:%M:%S', unit='ns')
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

    def test_table_cast_us_date(self):
        str_dt = pa.array(["01-16-2023", "03-07-2023", None, "11-05-2023"], pa.string())
        tbl = pa.table([str_dt], names=['str_dt'])
        result = CoreCommons.table_cast(tbl, dt_format="%m-%d-%Y").combine_chunks()
        control = pa.schema([('str_dt', pa.timestamp('ns'))])
        self.assertEqual(control, result.schema)

    def test_table_cast(self):
        num = pa.array([1.0, 12.0, 5.0, None], pa.float64())
        date = pc.strptime(["2023-01-02 04:49:06", "2023-01-02 04:57:12", None, "2023-01-02 05:23:50"], format='%Y-%m-%d %H:%M:%S', unit='ns')
        str_dt = pa.array(["2023-01-16", "2023-03-07", None, "2023-11-05"], pa.string())
        value = pa.array([None, '1.5', '3.2', '2.0'], pa.string())
        text = pa.array(["Blue", "Green", None, 'Red'], pa.string())
        bool1 = pa.array([1, 0, 1, None], pa.int64())
        bool2 = pa.array(['true', 'true', None, 'false'], pa.string())
        bool3 = pa.array([None, 'M', 'F', 'M'], pa.string())
        tbl = pa.table([num, value, date, str_dt, text, bool1, bool2, bool3],
                       names=['num', 'value', 'date', 'str_dt', 'text', 'bool1', 'bool2', 'bool3'])
        result = CoreCommons.table_cast(tbl).combine_chunks()
        control = pa.schema([('num', pa.int64()),
                             ('value', pa.float64()),
                             ('date', pa.timestamp('ns')),
                             ('str_dt', pa.timestamp('ns')),
                             ('text', pa.dictionary(pa.int32(), pa.string())),
                             ('bool1', pa.bool_()),
                             ('bool2', pa.bool_()),
                             ('bool3', pa.dictionary(pa.int32(), pa.string())),
                             ])
        self.assertEqual(control, result.schema)
        result = CoreCommons.table_cast(result, inc_cat=False).combine_chunks()
        control = pa.schema([('num', pa.int64()),
                             ('value', pa.float64()),
                             ('date', pa.timestamp('ns')),
                             ('str_dt', pa.timestamp('ns')),
                             ('text', pa.string()),
                             ('bool1', pa.bool_()),
                             ('bool2', pa.bool_()),
                             ('bool3', pa.string()),
                             ])
        self.assertEqual(control, result.schema)
        result = CoreCommons.table_cast(tbl, cat_max=2).combine_chunks()
        control = pa.schema([('num', pa.int64()),
                             ('value', pa.float64()),
                             ('date', pa.timestamp('ns')),
                             ('str_dt', pa.timestamp('ns')),
                             ('text', pa.string()),
                             ('bool1', pa.bool_()),
                             ('bool2', pa.bool_()),
                             ('bool3', pa.dictionary(pa.int32(), pa.string())),
                             ])
        self.assertEqual(control, result.schema)
        result = CoreCommons.table_cast(tbl, cat_max=2, inc_cat=False, inc_bool=False).combine_chunks()
        control = pa.schema([('num', pa.int64()),
                             ('value', pa.float64()),
                             ('date', pa.timestamp('ns')),
                             ('str_dt', pa.timestamp('ns')),
                             ('text', pa.string()),
                             ('bool1', pa.int64()),
                             ('bool2', pa.string()),
                             ('bool3', pa.string()),
                             ])
        self.assertEqual(control, result.schema)

    def test_filter_headers(self):
        tbl = pq.read_table("../_data/sample_types.parquet")
        result = CoreCommons.filter_headers(tbl)
        self.assertEqual(tbl.column_names, result)
        result = CoreCommons.filter_headers(tbl, headers=['num', 'string', 'cat'])
        self.assertCountEqual(['num', 'string', 'cat'], result)
        result = CoreCommons.filter_headers(tbl, regex=['num', 'int'])
        self.assertCountEqual(['num','int','num_null','int_null','nulls_int'], result)
        result = CoreCommons.filter_headers(tbl, regex=['null', 'num', 'int', 'date', 'nest'], drop=True)
        self.assertCountEqual(['binary', 'cat', 'bool', 'string'], result)
        result = CoreCommons.filter_headers(tbl, headers=['num', 'int', 'string'], regex='i')
        self.assertCountEqual(['int', 'string'], result)
        result = CoreCommons.filter_headers(tbl, d_types=['is_boolean', 'is_string'])
        self.assertCountEqual(['bool', 'string', 'bool_null', 'string_null', 'nulls_str'], result)
        result = CoreCommons.filter_headers(tbl, headers=['num','int','string'], d_types=['is_boolean', 'is_string'])
        self.assertCountEqual(['string'], result)

    def test_filter_columns(self):
        tbl = pq.read_table("../_data/sample_types.parquet")
        result = CoreCommons.filter_columns(tbl, headers=['num', 'date', 'string'], regex='t', d_types=[pa.string()])
        self.assertCountEqual(['string'], result.column_names)
        result = CoreCommons.filter_columns(tbl, headers='num')
        self.assertCountEqual(['num'], result.column_names)

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

    def test_list_dup(self):
        seq = ['A', 'B', 'B', 'C', 'C', 'D']
        result = CoreCommons.list_dup(seq=seq)
        self.assertCountEqual(['B', 'C'], result)
        seq = ['A', 'B', 'C', 'D']
        result = CoreCommons.list_dup(seq=seq)
        self.assertCountEqual([], result)

    def tests_list_beta_find(self):
        seq = ['A', 'B', 'C', 'D', 'E']
        result = CoreCommons.list_search(seq, 'A')
        self.assertEqual(0, result)
        result = CoreCommons.list_search(seq, 'C')
        self.assertEqual(2, result)
        result = CoreCommons.list_search(seq, 'E')
        self.assertEqual(4, result)

    def test_list_standardize(self):
        seq = [100, 75, 50, 25, 0]
        result = CoreCommons.list_standardize(seq=seq)
        self.assertEqual(0.0, result[2])
        self.assertEqual(0.0, result[1] + result[3])
        self.assertEqual(0.0, result[0] + result[4])

    def test_list_normalize_robust(self):
        seq = [100, 75, 50, 25, 0]
        result = CoreCommons.list_normalize_robust(seq=seq)
        self.assertEqual(result, [1.5, 1.0, 0.5, 0.0, -0.5])
        # outlier
        seq = [1,1,2,100,1,2,1,1,1]
        result = CoreCommons.list_normalize_robust(seq=seq)
        self.assertEqual(result, [0.0, 0.0, 1.0, 99.0, 0.0, 1.0, 0.0, 0.0, 0.0])


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
        str_date = '01/21/2017 21:12:46.000000'
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
