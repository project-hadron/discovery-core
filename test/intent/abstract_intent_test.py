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




if __name__ == '__main__':
    unittest.main()
