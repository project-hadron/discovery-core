from ds_core.handlers.abstract_handlers import HandlerFactory, ConnectorContract
import unittest


class HandlerFactoryTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_runs(self):
        """Basic smoke test"""
        HandlerFactory()

    def test_exceptions(self):
        # Bad module
        connector_contract = ConnectorContract(uri='example.csv;file_type=csv',
                                               module_name='ds_core.handlers.none',
                                               handler='PythonSourceHandler',
                                               kwargs={'sep': ',', 'encoding': 'latin1'})
        with self.assertRaises(ModuleNotFoundError) as context:
            HandlerFactory.instantiate(connector_contract)
        self.assertTrue("The module 'ds_core.handlers.none' could not be found" in str(context.exception))
        # bad handler
        connector_contract = ConnectorContract(uri='example.csv', module_name='test.handlers.pyarrow_handlers',
                                               handler='none')
        with self.assertRaises(ImportError) as context:
            HandlerFactory.instantiate(connector_contract)
        self.assertTrue("The handler 'none' could not be found in the module 'test.handlers.pyarrow_handlers'" in str(context.exception))
        # Everything correct
        connector_contract = ConnectorContract(uri='example.csv', module_name='test.handlers.pyarrow_handlers',
                                               handler='PythonSourceHandler')
        handler = HandlerFactory.instantiate(connector_contract)
        self.assertEqual("<class 'test.handlers.pyarrow_handlers.PythonSourceHandler'>", str(type(handler)))

    def test_handler_check(self):
        # Module
        result = HandlerFactory.check_module('test.handlers.pyarrow_handlers')
        self.assertTrue(result)
        result = HandlerFactory.check_module('ds_core.handlers.none')
        self.assertFalse(result)
        # Handdler
        result = HandlerFactory.check_handler(module_name='test.handlers.pyarrow_handlers', handler='PythonSourceHandler')
        self.assertTrue(result)
        result = HandlerFactory.check_handler(module_name='ds_core.handlers.None', handler='PythonSourceHandler')
        self.assertFalse(result)
        result = HandlerFactory.check_handler(module_name='test.handlers.pyarrow_handlers', handler='None')
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
