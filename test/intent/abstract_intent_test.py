import unittest
import os
import shutil

from ds_core.handlers.abstract_handlers import ConnectorContract
from ds_core.properties.abstract_properties import AbstractPropertyManager
from ds_core.properties.property_manager import PropertyManager

from test.intent.pyarrow_intent_model import PyarrowIntentModel


class ControlPropertyManager(AbstractPropertyManager):

    def __init__(self, task_name: str, creator: str=None):
        # set additional keys
        root_keys = []
        knowledge_keys = []
        creator = creator if isinstance(creator, str) else 'default'
        super().__init__(task_name=task_name, root_keys=root_keys, knowledge_keys=knowledge_keys, creator=creator)

    @classmethod
    def manager_name(cls) -> str:
        return str(cls.__name__).lower().replace('propertymanager', '')


class IntentModelTest(unittest.TestCase):

    def setUp(self):
        self.connector = ConnectorContract(uri='contracts/config_contract.pq?sep=.&encoding=Latin1',
                                           module_name='ds_core.handlers.pyarrow_handlers',
                                           handler='PyarrowPersistHandler')
        try:
            os.makedirs('contracts')
        except:
            pass
        PropertyManager._remove_all()
        self.pm = ControlPropertyManager('test_abstract_properties')
        self.pm.set_property_connector(self.connector)

    def tearDown(self):
        try:
            shutil.rmtree('contracts')
        except:
            pass

    def test_runs(self):
        """Basic smoke test"""
        PyarrowIntentModel(property_manager=self.pm)

    def test_run_intent_pipeline(self):
        model = PyarrowIntentModel(property_manager=self.pm)
        canonical = {'A': [1,4,7], 'B': [4,5,9]}
        result = model.run_intent_pipeline(canonical=canonical, inplace=False)
        self.assertDictEqual(canonical, result)
        model.to_str_type(data=canonical, headers=['B'])
        result = model.run_intent_pipeline(canonical=canonical)
        self.assertDictEqual({'a': [1, 4, 7]}, result)

    def test_run_intent_pipeline_levels(self):
        model = PyarrowIntentModel(property_manager=self.pm)
        data = {'A': [1,4,7], 'B': [4,5,9]}
        model.to_remove(data=data, headers=['B'], inplace=False, intent_level=0)
        model.auto_clean_header(data=data, case='lower', inplace=False, intent_level=1)
        result = model.run_intent_pipeline(canonical=data, inplace=False, intent_levels=0)
        self.assertDictEqual({'A': [1, 4, 7]}, result)
        result = model.run_intent_pipeline(canonical=data, inplace=False, intent_levels=1)
        self.assertDictEqual({'a': [1,4,7], 'b': [4,5,9]}, result)
        result = model.run_intent_pipeline(canonical=data, inplace=False, intent_levels=[0, 1, 2])
        self.assertDictEqual({'a': [1,4,7]}, result)




if __name__ == '__main__':
    unittest.main()
