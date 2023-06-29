import os
import shutil
import unittest
from pprint import pprint

from ds_core.handlers.abstract_handlers import ConnectorContract, HandlerFactory
from ds_core.properties.property_manager import PropertyManager


class PropertyManagerTest(unittest.TestCase):
    """Test: """

    def setUp(self):
        try:
            shutil.rmtree('test')
        except:
            pass
        os.mkdir('test')
        pass

    def tearDown(self):
        PropertyManager()._remove_all()
        self.assertEqual({}, PropertyManager().get_all())

        try:
            shutil.rmtree('test')
        except:
            pass

    def test_runs(self):
        """Basic smoke test"""
        PropertyManager()

    def test_replace_dict_with_dict(self):
        pm = PropertyManager()
        control = {'contract': {'connector': {}, 'cleaner': '{}', 'version': '0.00'}}
        result = {'root': {'contract': {'connector': {}, 'cleaner': '{}', 'version': '0.00'}}}
        pm.set('root', control)
        self.assertEqual(result, pm.get_all())
        control = {'contract': {'connector': {'files': ['myfile.csv', 'yourfile.csv']}, 'version': '1.00.001'}}
        result = {'root': {'contract': {'connector': {'files': ['myfile.csv', 'yourfile.csv']},
                                        'cleaner': '{}',
                                        'version': '1.00.001'}}}
        pm.set('root', control)
        self.assertEqual(result, pm.get_all())
        control = {'contract': {'connector': {'files': {'in' : 'in_file', 'out': 'out_file'}},
                                'version': '1.00.002'}}
        result = {'root': {'contract': {'connector': {'files': {'in' : 'in_file', 'out': 'out_file'}},
                                        'cleaner': '{}',
                                        'version': '1.00.002'}}}
        pm.set('root', control)
        self.assertEqual(result, pm.get_all())

    def test_set_list(self):
        pm = PropertyManager()
        pm.set('some_name', ['item1'])
        self.assertEqual(['item1'], pm.get('some_name'))
        pm.set('some_name', ['item2', 'item3'])
        self.assertEqual(['item1', 'item2', 'item3'], pm.get('some_name'))

    def test_dump_load_persist(self):
        connector_contract = ConnectorContract(uri='test/properties.parquet',
                                               module_name='ds_core.handlers.pyarrow_handlers',
                                               handler='PyarrowPersistHandler', file_type='parquet')
        handler = HandlerFactory.instantiate(connector_contract)
        pm = PropertyManager()
        file = 'test/properties.parquet'
        pm.set('KeyA', 'ValueA')
        self.assertEqual('ValueA', pm.get('KeyA'))
        pm.dump(handler)
        self.assertTrue(os.path.exists(file))
        self.assertTrue(pm.is_key('KeyA'))
        pm.remove('KeyA')
        self.assertFalse(pm.is_key('KeyA'))
        pm.load(handler)
        self.assertTrue(pm.is_key('KeyA'))
        self.assertEqual('ValueA', pm.get('KeyA'))

    def test_dump_load_key(self):
        connector_contract = ConnectorContract(uri='test/properties.parquet',
                                               module_name='ds_core.handlers.pyarrow_handlers',
                                               handler='PyarrowPersistHandler', file_type='parquet')
        handler = HandlerFactory.instantiate(connector_contract)
        pm = PropertyManager()
        pm.set('transition.task1', {'keyA1': 'valueA1'})
        pm.set('transition.task2', {'keyA2': 'valueA2'})
        pm.set('feature_catalog.task2', {'keyA2': 'valueA2'})
        base = pm.get_all()
        pm.dump(handler=handler)
        pm.load(handler=handler, replace=True)
        self.assertDictEqual(base, pm.get_all())
        pm.load(handler=handler, key='transition.task1', replace=True)
        control = {'transition': {'task1': {'keyA1': 'valueA1'}}}
        self.assertDictEqual(control, pm.get_all())
        pm.load(handler=handler, key='transition', replace=True)
        control = {'transition': {'task1': {'keyA1': 'valueA1'}, 'task2': {'keyA2': 'valueA2'}}}
        self.assertDictEqual(control, pm.get_all())
        pm.load(handler=handler, key='', replace=True, ignore_key_error=True)
        self.assertDictEqual({}, pm.get_all())
        pm.load(handler=handler, key='one.two.three', replace=True, ignore_key_error=True)
        self.assertDictEqual({}, pm.get_all())
        pm.set('feature_catalog.task2', {'keyA2': 'valueA2'})
        pm.load(handler=handler, key='one.two.three', replace=False, ignore_key_error=True)
        control = {'feature_catalog': {'task2': {'keyA2': 'valueA2'}}}
        self.assertDictEqual(control, pm.get_all())

    def test_raise(self):
        connector_contract = ConnectorContract(uri='test/properties.parquet',
                                               module_name='ds_core.handlers.pyarrow_handlers',
                                               handler='PyarrowPersistHandler', file_type='parquet')
        handler = HandlerFactory.instantiate(connector_contract)
        pm = PropertyManager()
        pm.dump(handler)
        with self.assertRaises(KeyError) as context:
            pm.load(handler=handler, key='one.two.three')
        self.assertTrue("The key 'one.two.three' could not " in str(context.exception))

    def test_dump_load_overwrite(self):
        connector_contract = ConnectorContract(uri='test/properties.parquet',
                                               module_name='ds_core.handlers.pyarrow_handlers',
                                               handler='PyarrowPersistHandler', file_type='parquet')
        handler = HandlerFactory.instantiate(connector_contract)
        pm = PropertyManager()
        file = 'test/properties.parquet'
        pm.set('KeyA', 'ValueA')
        self.assertEqual('ValueA', pm.get('KeyA'))
        # dump the file then add a new item and see if it doesn't get overwritten
        pm.dump(handler)
        self.assertTrue(os.path.exists(file))
        pm.set('KeyB', 'ValueB')
        self.assertEqual('ValueB', pm.get('KeyB'))
        pm.remove('KeyA')
        self.assertFalse(pm.is_key('KeyA'))
        self.assertTrue(pm.is_key('KeyB'))
        pm.load(handler)
        self.assertTrue(pm.is_key('KeyA'))
        self.assertEqual('ValueA', pm.get('KeyA'))
        self.assertTrue(pm.is_key('KeyB'))
        self.assertEqual('ValueB', pm.get('KeyB'))
        # change KeyA to another value and load again
        pm.set('KeyA', 'ReplaceA')
        self.assertEqual('ReplaceA', pm.get('KeyA'))
        pm.load(handler)
        self.assertEqual('ValueA', pm.get('KeyA'))
        self.assertEqual('ValueB', pm.get('KeyB'))

    def test_singleton(self):
        """tests singleton works"""
        pm1 = PropertyManager()
        pm2 = PropertyManager()

        # adding properties to s1 exists in s2
        pm1.set('KeyA', 'ValueA')
        pm1.set('KeyB', 'ValueB')
        self.assertEqual(pm1.get_all(), pm2.get_all())
        self.assertEqual(pm1.get('KeyA'), 'ValueA')
        self.assertEqual(pm2.get('KeyA'), 'ValueA')
        self.assertEqual(pm1.get('KeyB'), 'ValueB')
        self.assertEqual(pm2.get('KeyB'), 'ValueB')

        # removing properties
        pm1.remove('KeyB')
        self.assertEqual(pm1.get('KeyB'), None)
        self.assertEqual(pm2.get('KeyB'), None)

        # add property to s2
        pm2.set('KeyC', 'ValueC')
        self.assertEqual(pm1.get('KeyC'), 'ValueC')

    def test_is_key(self):
        """tests singleton works"""
        pm = PropertyManager()
        pm.set('level0.level1.level2', 'value012')

        self.assertFalse(pm.is_key('NoKey'))
        self.assertFalse(pm.is_key(''))
        self.assertFalse(pm.is_key(None))

        self.assertTrue(pm.is_key('level0'))
        self.assertTrue(pm.is_key('level0.level1'))
        self.assertTrue(pm.is_key('level0.level1.level2'))
        self.assertFalse(pm.is_key('level0.level1.notKey'))

    def test_get(self):
        """ Test the get with complex dictionary"""
        pm = PropertyManager()
        pm.set('level0.level1.branch1', '01b1')
        pm.set('level0.level1.branch2', '01b2')

        self.assertEqual(pm.get(''), None)
        self.assertEqual(pm.get('noValue'), None)
        self.assertEqual(pm.get('noValue.noValue'), None)
        self.assertEqual(pm.get('level0.noValue'), None)
        self.assertEqual(pm.get('level0.level1.noValue'), None)

        self.assertEqual('01b1', pm.get('level0.level1.branch1'))
        self.assertEqual('01b2', pm.get('level0.level1.branch2'))
        self.assertEqual({'branch1': '01b1', 'branch2': '01b2'}, pm.get('level0.level1'))

    def test_replace_list(self):
        # Configuration
        pm = PropertyManager()
        pm.set('level0.level1', {'keyList': ['list1', 'list2', 'list3'], 'newItem': 'newValue'})
        self.assertEqual(['list1', 'list2', 'list3'], pm.get('level0.level1.keyList'))
        self.assertEqual('newValue', pm.get('level0.level1.newItem'))
        pm.set('level0.level1', {'keyList': ['list5', 'list6', 'list7'], 'newItem': 'newValue'})
        self.assertNotEqual(['list1', 'list2', 'list3'], pm.get('level0.level1.keyList'))
        self.assertEqual(['list5', 'list6', 'list7'], pm.get('level0.level1.keyList'))

    def test_join(self):
        pm = PropertyManager()
        self.assertEqual('1.2.3', pm.join('1', '2', '3'))
        self.assertEqual('1/2/3', pm.join('1', '2', '3', sep='/'))


if __name__ == '__main__':
    unittest.main()
