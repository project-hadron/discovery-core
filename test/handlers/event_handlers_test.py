import unittest
import os
from pathlib import Path
import shutil
from datetime import datetime

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from ds_core.handlers.abstract_handlers import ConnectorContract
from ds_core.handlers.event_handlers import EventSourceHandler, EventPersistHandler, EventManager
from ds_core.properties.property_manager import PropertyManager
from test.components.pyarrow_component import PyarrowComponent

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
        os.environ['HADRON_PM_PATH'] = "event://pm_story"
        os.environ['HADRON_PM_TYPE'] = 'json'
        # Local Connectivity
        os.environ['HADRON_DEFAULT_PATH'] = "event://data"
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


    def test_enent_manager_string(self):
        tbl = get_table()
        em = EventManager().reset()
        em.set('task1', tbl)
        em.set('task2', None)
        print(em)

    def test_event_manager(self):
        tbl = get_table()
        em = EventManager().reset()
        # set
        em.set('task', tbl)
        self.assertTrue(em.is_event('task'))
        self.assertTrue(em.is_event('task'))
        self.assertEqual(['task'], em.event_names())
        self.assertTrue(tbl.equals(em.get('task')))
        # update
        sub_tbl = tbl.drop_columns(['num', 'cat'])
        em.update('task', sub_tbl)
        self.assertFalse(tbl.equals(em.get('task')))
        self.assertTrue(sub_tbl.equals(em.get('task')))
        # delete
        em.delete('task')
        self.assertFalse(em.is_event('task'))

    def test_connector_handler(self):
        tbl = get_table()
        uri = 'event://task/'
        test1 = PyarrowComponent.from_env('test1', has_contract=False)
        test1.set_persist_uri(uri=uri)
        test1.save_canonical(test1.CONNECTOR_PERSIST, tbl)
        result = test1.load_canonical(test1.CONNECTOR_PERSIST)
        self.assertEqual((7, 6), result.shape)
        test2 = PyarrowComponent.from_env('test2', has_contract=False)
        test2.set_source_uri(test1.get_persist_uri())
        result = test2.load_canonical(test2.CONNECTOR_SOURCE)
        self.assertEqual((7, 6), result.shape)
        self.assertTrue(tbl.equals(result))
        result = test2.load_canonical(test2.CONNECTOR_SOURCE, drop=True)
        self.assertEqual((7, 6), result.shape)
        with self.assertRaises(ValueError) as context:
            _ = test2.load_canonical(test2.CONNECTOR_SOURCE)
        self.assertTrue("The event 'task' does not exist" in str(context.exception))

    def test_connector_contract(self):
        tbl = get_table()
        uri = 'event://task/'
        cc = ConnectorContract(uri, 'module_name', 'handler')
        in_handler = EventPersistHandler(cc)
        in_handler.persist_canonical(tbl)
        out_handler = EventSourceHandler(cc)
        result = out_handler.load_canonical()
        self.assertTrue(tbl.equals(result))

    def test_raise(self):
        startTime = datetime.now()
        with self.assertRaises(KeyError) as context:
            env = os.environ['NoEnvValueTest']
        self.assertTrue("'NoEnvValueTest'" in str(context.exception))
        print(f"Duration - {str(datetime.now() - startTime)}")

def get_table():
    num = pa.array([1.0, None, 5.0, -0.46421, 3.5, 7.233, -2], pa.float64())
    val = pa.array([1, 2, 3, 4, 5, 6, 7], pa.int64())
    date = pc.strptime(["2023-01-02 04:49:06", "2023-01-02 04:57:12", None, None, "2023-01-02 05:23:50", None, None],
                       format='%Y-%m-%d %H:%M:%S', unit='ns')
    text = pa.array(["Blue", "Green", None, 'Red', 'Orange', 'Yellow', 'Pink'], pa.string())
    binary = pa.array([True, True, None, False, False, True, False], pa.bool_())
    cat = pa.array([None, 'M', 'F', 'M', 'F', 'M', 'M'], pa.string()).dictionary_encode()
    return pa.table([num, val, date, text, binary, cat], names=['num', 'int', 'date', 'text', 'bool', 'cat'])


if __name__ == '__main__':
    unittest.main()
