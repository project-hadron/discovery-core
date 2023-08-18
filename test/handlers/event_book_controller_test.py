import unittest
import os
from pathlib import Path
import shutil
from datetime import datetime
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
from ds_core.properties.property_manager import PropertyManager
from ds_core.handlers.event_book_controller import EventBookController

# Pandas setup
pd.set_option('max_colwidth', 320)
pd.set_option('display.max_rows', 100)
pd.set_option('display.max_columns', 99)
pd.set_option('expand_frame_repr', True)


class FeatureBuilderTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        # clean out any old environments
        for key in os.environ.keys():
            if key.startswith('HADRON'):
                del os.environ[key]
        # Local Domain Contract
        os.environ['HADRON_PM_PATH'] = os.path.join('working', 'contracts')
        os.environ['HADRON_PM_TYPE'] = 'parquet'
        # Local Connectivity
        os.environ['HADRON_DEFAULT_PATH'] = Path('working/data').as_posix()
        # Specialist Component
        try:
            os.makedirs(os.environ['HADRON_PM_PATH'])
        except OSError:
            pass
        try:
            os.makedirs(os.environ['HADRON_DEFAULT_PATH'])
        except OSError:
            pass
        try:
            shutil.copytree('../_test_data', os.path.join(os.environ['PWD'], 'working/source'))
        except OSError:
            pass
        PropertyManager._remove_all()

    def tearDown(self):
        try:
            shutil.rmtree('working')
        except OSError:
            pass

    def test_for_smoke(self):
        num = pa.array([1.0, 12.0, 5.0, None], pa.float64())
        val = pa.array([7, None, 3, 5], pa.int64())
        date = pc.strptime(["2023-01-02 04:49:06", "2023-01-02 04:57:12", None, "2023-01-02 05:23:50"], format='%Y-%m-%d %H:%M:%S', unit='ns')
        text = pa.array(["Blue", "Green", None, 'Red'], pa.string())
        binary = pa.array([True, True, None, False], pa.bool_())
        cat = pa.array([None, 'M', 'F', 'M'], pa.string()).dictionary_encode()
        t1 = pa.table([num, val, text],
                       names=['num', 'int', 'text'])
        t2 = pa.table([num, val, date, text, binary, cat],
                       names=['num', 'int', 'date', 'text', 'bool', 'cat'])
        ebc = EventBookController()
        ebc.add_event_book('book1', t1)
        ebc.add_event_book('book2', t2)
        result = ebc.get_event('book1')
        self.assertEqual(t1, result)
        self.assertNotEqual(t2, result)
        self.assertEqual(['book1', 'book2'], ebc.event_book_names)
        result = ebc.get_event('book2', drop=True)
        self.assertEqual(t2, result)
        self.assertEqual(['book1'], ebc.event_book_names)


    def test_raise(self):
        startTime = datetime.now()
        with self.assertRaises(KeyError) as context:
            env = os.environ['NoEnvValueTest']
        self.assertTrue("'NoEnvValueTest'" in str(context.exception))
        print(f"Duration - {str(datetime.now() - startTime)}")


if __name__ == '__main__':
    unittest.main()
