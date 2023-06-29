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
                                               handler='PyarrowSourceHandler',
                                               kwargs={'sep': ',', 'encoding': 'latin1'})
        with self.assertRaises(ModuleNotFoundError) as context:
            HandlerFactory.instantiate(connector_contract)
        self.assertTrue("The module 'ds_core.handlers.none' could not be found" in str(context.exception))
        # bad handler
        connector_contract = ConnectorContract(uri='example.csv', module_name='ds_core.handlers.pyarrow_handlers',
                                               handler='none')
        with self.assertRaises(ImportError) as context:
            HandlerFactory.instantiate(connector_contract)
        self.assertTrue("The handler 'none' could not be found in the module 'ds_core.handlers.pyarrow_handlers'" in str(context.exception))
        # Everything correct
        connector_contract = ConnectorContract(uri='example.csv', module_name='ds_core.handlers.pyarrow_handlers',
                                               handler='PyarrowSourceHandler')
        handler = HandlerFactory.instantiate(connector_contract)
        self.assertEqual("<class 'ds_core.handlers.pyarrow_handlers.PyarrowSourceHandler'>", str(type(handler)))

    def test_handler_check(self):
        # Module
        result = HandlerFactory.check_module('ds_core.handlers.pyarrow_handlers')
        self.assertTrue(result)
        result = HandlerFactory.check_module('ds_core.handlers.none')
        self.assertFalse(result)
        # Handdler
        result = HandlerFactory.check_handler(module_name='ds_core.handlers.pyarrow_handlers', handler='PyarrowSourceHandler')
        self.assertTrue(result)
        result = HandlerFactory.check_handler(module_name='ds_core.handlers.None', handler='PyarrowSourceHandler')
        self.assertFalse(result)
        result = HandlerFactory.check_handler(module_name='ds_core.handlers.pyarrow_handlers', handler='None')
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
