import os
import shutil
import unittest
from pprint import pprint

from ds_core.components.core_commons import CoreCommons
from ds_core.handlers.abstract_handlers import ConnectorContract

from ds_core.properties.abstract_properties import AbstractPropertyManager, AbstractProperty
from ds_core.properties.property_manager import PropertyManager


class ControlPropertyManager(AbstractPropertyManager):

    def __init__(self, task_name: str, root_keys: list=None, knowledge_keys: list=None, creator: str=None):
        root_keys = root_keys if isinstance(root_keys, list) else []
        knowledge_keys = knowledge_keys if isinstance(knowledge_keys, list) else []
        creator = creator if isinstance(creator, str) else 'default'
        root_keys += ['cleaners']
        super().__init__(task_name, root_keys, knowledge_keys, creator)

    @classmethod
    def manager_name(cls) -> str:
        return str(cls.__name__).lower().replace('propertymanager', '')


class AbstractPropertiesManagerTest(unittest.TestCase):
    """Test: """

    def setUp(self):
        self.connector = ConnectorContract(uri='works/config_contract.parquet?sep=.&encoding=Latin1',
                                           module_name='ds_core.handlers.pyarrow_handlers',
                                           handler='PyarrowPersistHandler', name='darryl', password='mypass')
        try:
            os.makedirs('works')
        except:
            pass
        PropertyManager._remove_all()

    def tearDown(self):
        try:
            shutil.rmtree('works')
        except:
            pass

    def test_runs(self):
        """Basic smoke test"""
        ControlPropertyManager('test_abstract_properties')

    def test_manager_name(self):
        manager = ControlPropertyManager('test_abstract_properties')
        self.assertEqual('control', manager.manager_name())

    def test_creator(self):
        manager = ControlPropertyManager('test_abstract_properties')
        self.assertEqual('default', manager.creator)
        manager = ControlPropertyManager('test_abstract_properties', creator='fbloggs')
        self.assertEqual('fbloggs', manager.creator)

    def test_keys(self):
        augmented_keys = ['observations', 'notes']
        manager = ControlPropertyManager('test_abstract_properties', knowledge_keys=augmented_keys)
        result = manager.KEY.keys()
        self.assertIn('knowledge.observations_key', result)
        self.assertIn('knowledge.notes_key', result)
        self.assertIn("knowledge.schema_key", result)
        self.assertIn('cleaners_key', result)
        self.assertIn('version_key', result)
        control = 'control.test_abstract_properties.version'
        result = manager.KEY.version_key
        self.assertEqual(control, result)
        control = 'control.test_abstract_properties.knowledge.notes'
        result = manager.KEY.knowledge.notes_key
        self.assertEqual(control, result)

    def test_abstract_key(self):
        keys = ['connectors', 'values']
        ab = AbstractProperty(keys, manager='contract', contract='subset')
        self.assertEqual('contract.subset', ab.contract_key)
        self.assertEqual('contract.subset.connectors', ab.connectors_key)

        ab = AbstractProperty(keys, manager='contract')
        self.assertEqual('contract', ab.manager_key)
        self.assertEqual('contract.connectors', ab.connectors_key)

        ab = AbstractProperty(keys)
        self.assertEqual('connectors', ab.connectors_key)
        self.assertEqual('values', ab.values_key)

    def test_abstract_key_complex(self):
        keys = [{'connectors': ['one', 'two']}]
        ab = AbstractProperty(keys, manager='contract', contract='subset')
        self.assertEqual('contract.subset', ab.contract_key)
        self.assertEqual('contract.subset.connectors', ab.connectors_key)
        self.assertEqual('contract.subset.connectors.one', ab.connectors.one_key)

    def test_reset_abstract_properties(self):
        keys = ['connectors', 'intent', 'overview']
        pm = ControlPropertyManager(task_name='contract', root_keys=keys, knowledge_keys=[])
        pm.set(pm.KEY.intent_key, 'some value')
        pm.set_version('v1')
        control = {'description': "", 'status': 'discovery', 'cleaners': {}, 'connectors': {}, 'intent': 'some value', 'overview': {}, 'run_book': {},'snapshot': {}, 'version': 'v1',
                   'meta': {'class': 'ControlPropertyManager', 'module': pm.__module__.split(".")}, 'knowledge': {'intent': {}, 'schema': {}}}
        self.assertEqual(control, pm.get(pm.KEY.contract_key))
        pm.reset_all()
        control = {'description': "", 'status': 'discovery', 'cleaners': {}, 'connectors': {}, 'intent': {}, 'overview': {}, 'run_book': {},'snapshot': {}, 'version': '0.0.1',
                   'meta': {'class': 'ControlPropertyManager', 'module': pm.__module__.split(".")}, 'knowledge': {'intent': {}, 'schema': {}}}
        self.assertEqual(control, pm.get(pm.KEY.contract_key))

    def test_set_property(self):
        pm = ControlPropertyManager('test_abstract_properties')
        pm.set_property_connector(self.connector)
        result = pm.get_connector_contract(pm.CONNECTOR_PM_CONTRACT)
        self.assertEqual('works/config_contract.parquet?sep=.&encoding=Latin1', result.raw_uri)
        self.assertEqual('ds_core.handlers.pyarrow_handlers', result.raw_module_name)
        self.assertEqual('PyarrowPersistHandler', result.raw_handler)
        self.assertDictEqual({'name': 'darryl', 'password': 'mypass'}, result.raw_kwargs)
        self.assertEqual('0.0.1', result.version)

    def test_reset(self):
        pm = ControlPropertyManager('test_abstract_properties')
        pm.reset_all()
        pm.set_property_connector(self.connector)
        control = pm.get(pm.KEY.connectors_key)
        pm.set_version('latest')
        version = pm.version
        self.assertEqual('latest', pm.version)
        pm.reset_all()
        result = pm.get(pm.KEY.connectors_key)
        self.assertEqual(control, result)
        self.assertNotEqual(version, pm.version)
        self.assertEqual('0.0.1', pm.version)
        # add new properties and check the connector is not removed
        pm.set(pm.KEY.cleaners_key, {'clean_header': {'case': 'title', 'rename': {'surname: last_name'}}})
        pm.set(pm.KEY.version_key, 'v1.00')
        self.assertEqual(['pm_control_test_abstract_properties'], list(pm.get(pm.KEY.connectors_key).keys()))
        self.assertEqual(['clean_header'], list(pm.get(pm.KEY.cleaners_key).keys()))
        self.assertEqual('v1.00', pm.get(pm.KEY.version_key))
        pm.reset_all()
        self.assertEqual(['pm_control_test_abstract_properties'], list(pm.get(pm.KEY.connectors_key).keys()))
        self.assertEqual({}, pm.get(pm.KEY.cleaners_key))
        self.assertEqual('0.0.1', pm.get(pm.KEY.version_key))

    def test_multi_instance(self):
        dpm = ControlPropertyManager('test_abstract_properties')
        self.assertEqual('0.0.1', dpm.get(dpm.KEY.version_key))
        self.assertEqual([], list(dpm.get(dpm.KEY.cleaners_key).keys()))
        dpm.set_connector_contract('raw_source', connector_contract=self.connector)
        dpm.set(dpm.KEY.cleaners_key, {'clean_header': {'case': 'title', 'rename': {'surname: last_name'}}})
        dpm.set(dpm.KEY.version_key, '5.01')
        self.assertEqual('5.01', dpm.get(dpm.KEY.version_key))
        self.assertEqual(['clean_header'], list(dpm.get(dpm.KEY.cleaners_key).keys()))
        #now load a new instance
        dpm2 = ControlPropertyManager('test_abstract_properties')
        self.assertEqual('5.01', dpm2.get(dpm.KEY.version_key))
        self.assertEqual(['clean_header'], list(dpm.get(dpm.KEY.cleaners_key).keys()))

    def test_set_connector_contract(self):
        connector_name = 'raw_source'
        dpm = ControlPropertyManager('test_abstract_properties')
        dpm.set_connector_contract(connector_name=connector_name, connector_contract=self.connector)
        result = dpm.get_connector_contract(connector_name)
        self.assertEqual(self.connector.raw_uri, result.raw_uri)
        self.assertEqual(self.connector.module_name, result.module_name)
        self.assertEqual(self.connector.handler, result.handler)
        self.assertEqual(self.connector.get_key_value('sep'), result.get_key_value('sep'))
        self.assertEqual(self.connector.get_key_value('encoding'), result.get_key_value('encoding'))

    def test_set_version(self):
        dpm = ControlPropertyManager('test_abstract_properties')
        self.assertEqual('0.0.1', dpm.get(dpm.KEY.version_key))
        dpm.set(dpm.KEY.version_key, '1.00')
        self.assertEqual('1.00', dpm.get(dpm.KEY.version_key))
        self.assertEqual(dpm.get(dpm.KEY.version_key), dpm.version)

    def test_set_status(self):
        dpm = ControlPropertyManager('test_abstract_properties')
        self.assertEqual('discovery', dpm.get(dpm.KEY.status_key))
        dpm.set(dpm.KEY.status_key, 'complete')
        self.assertEqual('complete', dpm.get(dpm.KEY.status_key))
        self.assertEqual(dpm.get(dpm.KEY.status_key), dpm.status)

    def test_set_description(self):
        dpm = ControlPropertyManager('test_abstract_properties')
        self.assertEqual('', dpm.get(dpm.KEY.description_key))
        dpm.set(dpm.KEY.description_key, 'This Task description')
        self.assertEqual('This Task description', dpm.get(dpm.KEY.description_key))
        self.assertEqual(dpm.get(dpm.KEY.description_key), dpm.description)

    def test_info(self):
        dpm = ControlPropertyManager('test')
        result = dpm.report_task_meta()
        control = {'contract': 'control', 'task': 'test', 'description': '', 'status': 'discovery', 'version': '0.0.1'}
        self.assertEqual(control, result)
        dpm.set_description('This Task description')
        dpm.set_version('v1.01')
        dpm.set_status('stable')
        result = dpm.report_task_meta()
        control = {'contract': 'control', 'task': 'test', 'description': 'This Task description', 'status': 'stable', 'version': 'v1.01'}
        self.assertEqual(control, result)
        dpm.reset_task_meta()
        result = dpm.report_task_meta()
        control = {'contract': 'control', 'task': 'test', 'description': '', 'status': 'discovery', 'version': '0.0.1'}
        self.assertEqual(control, result)

    def test_set_snapshot(self):
        dpm = ControlPropertyManager('test_abstract_properties')
        dpm.set_snapshot('3.00.001')
        control = ['description', 'status', 'cleaners', 'snapshot', 'intent', 'version', 'run_book','connectors', 'knowledge', 'meta']
        self.assertCountEqual(control, list(dpm.get(dpm.KEY.contract_key).keys()))
        result = list(dpm.get(dpm.KEY.snapshot_key).keys())
        control = ['test_abstract_properties_#3_00_001']
        self.assertCountEqual(control, result)
        result = list(dpm.get(dpm.KEY.snapshot_key).get('test_abstract_properties_#3_00_001').keys())
        # check the snapshot hasn't been copied to the snapshot
        control = ['cleaners', 'description', 'version', 'status', 'connectors', 'intent', 'run_book', 'meta', 'knowledge', 'snapshot']
        self.assertCountEqual(control, result)

    def test_recover_snapshot(self):
        dpm = ControlPropertyManager('test_abstract_properties')
        version = '1.00.000'
        dpm.set(dpm.KEY.version_key, version)
        self.assertEqual(version, dpm.version)
        snap_name = dpm.set_snapshot("test")
        control = '1.00.001'
        dpm.set(dpm.KEY.version_key, control)
        self.assertEqual(control, dpm.version)
        dpm.recover_snapshot(snap_name)
        self.assertEqual(version, dpm.version)

    def test_get_snapshot(self):
        dpm = ControlPropertyManager('test_abstract_properties')
        control = []
        result = dpm.snapshots
        self.assertEqual(control, result)
        dpm.set_snapshot('3.00.001')
        dpm.set_snapshot('test')
        control = ['test_abstract_properties_#3_00_001', 'test_abstract_properties_#test']
        result = dpm.snapshots
        self.assertEqual(control, result)
        dpm2 = ControlPropertyManager('new_abstract_properties')
        dpm2.set_snapshot('2018-06-12')
        control = ['new_abstract_properties_#2018-06-12']
        result = dpm2.snapshots
        self.assertEqual(control, result)
        control = ['test_abstract_properties_#3_00_001', 'test_abstract_properties_#test']
        result = dpm.snapshots
        self.assertEqual(control, result)

    def test_get_knowledge(self):
        keys = ['overview', 'notes']
        manager = ControlPropertyManager('test_abstract_properties', knowledge_keys=keys)
        manager.set_knowledge(text="My Note", label='age', catalog='notes')
        manager.set_knowledge(text="general note", label='comment', catalog='notes')
        manager.set_knowledge(text="and another", label='comment', catalog='notes')
        result = manager.get_knowledge(catalog='overview')
        self.assertEqual({}, result)
        result = manager.get_knowledge(catalog='notes')
        self.assertEqual(['age', 'comment'], CoreCommons.list_formatter(result.keys()))
        result = manager.get_knowledge(catalog='notes', as_list=True)
        self.assertEqual(['age', 'comment'], result)
        result = manager.get_knowledge(catalog='notes', label='comment')
        self.assertEqual(['general note', 'and another'], CoreCommons.list_formatter(result.values()))
        result = manager.get_knowledge(catalog='notes', label='comment', as_list=True)
        self.assertEqual(['general note', 'and another'], result)

    def test_set_and_remove_knowledge(self):
        keys = ['overview', 'notes', 'observations', 'attribute', 'dictionary', 'tor']
        manager = ControlPropertyManager('test_abstract_properties', knowledge_keys=keys)
        manager.set_knowledge(text="My Note", label='age', catalog='notes')
        manager.set_knowledge(text="general note", label='comment', catalog='notes')
        result = manager.knowledge_filter(catalog='notes', label='age')
        self.assertEqual(["My Note"], list(result.get('notes').get('age').values()))
        #remove
        result = manager.reset_knowledge()
        self.assertEqual({}, manager.knowledge_filter(catalog='notes'))

    def test_set_knowledge_with_replace(self):
        keys = ['overview', 'notes', 'observations', 'attribute', 'dictionary', 'tor']
        manager = ControlPropertyManager('test_abstract_properties', knowledge_keys=keys)
        manager.set_knowledge(text="My Note", label='age', catalog='notes')
        result = manager.knowledge_filter(catalog='notes', label='age')
        self.assertEqual(["My Note"], list(result.get('notes').get('age').values()))
        manager.set_knowledge(text="New Note", label='age', catalog='notes', replace=True)
        result = manager.knowledge_filter(catalog='notes', label='age')
        self.assertEqual(["New Note"], list(result.get('notes').get('age').values()))

    def test_has_knowledge(self):
        keys = ['overview', 'notes', 'observations', 'attribute', 'dictionary', 'tor']
        manager = ControlPropertyManager('test_abstract_properties', knowledge_keys=keys)
        result = manager.has_knowledge()
        self.assertFalse(result)
        manager.set_knowledge(catalog='overview', label='label', text='text')
        result = manager.has_knowledge()
        self.assertTrue(result)
        result = manager.has_knowledge(catalog='notes')
        self.assertFalse(result)
        result = manager.has_knowledge(catalog='overview')
        self.assertTrue(result)
        result = manager.has_knowledge(catalog='overview', label='bob')
        self.assertFalse(result)
        result = manager.has_knowledge(catalog='overview', label='label')
        self.assertTrue(result)
        result = manager.has_knowledge(label='label')
        self.assertTrue(result)
        result = manager.has_knowledge(label='bob')
        self.assertFalse(result)

    def test_bulk_upload_and_filter(self):
        keys = ['attributes']
        manager = ControlPropertyManager('test_abstract_properties', knowledge_keys=keys)
        upload = {'Attribute': ['APP_CD', 'APP_DESC', 'BILT_CUST_NBR', 'BU_ID', 'FISC_QTR_ID', 'FISC_WK_ID'],
                  'description': ['Esupport Application Code', 'Esupport Application Description',
                                  'Bill To Customer number', 'Business Unit ID (number that represents the country)',
                                  'Fiscal Quarter', 'Fiscal WK', ]}
        manager.bulk_upload_knowledge(upload, catalog='attributes', label_key='Attribute', text_key='description')
        result = manager.report_notes(catalog='attributes')
        self.assertEqual(['attributes']*6, result.get('section'))
        self.assertCountEqual(upload.get('Attribute'), result.get('label'))
        self.assertCountEqual(upload.get('description'), result.get('text'))

    def test_set_intent(self):
        dpm = ControlPropertyManager('test_abstract_properties')
        with self.assertRaises(ValueError) as context:
            dpm.set_intent(intent_param=[])
        self.assertTrue("The intent section must be a dictionary" in str(context.exception))
        dpm.set_intent(intent_param={})
        control = {}
        self.assertEqual(control, dpm.get_intent())
        # add values
        cleaner1 = {'clean_01': {'headers': 'h1', 'dtype': ['number', 'str']}}
        dpm.set_intent(cleaner1)
        control = {'A': {'0': {'clean_01': {'dtype': ['number', 'str'], 'headers': 'h1'}}}}
        self.assertEqual(control, dpm.get_intent())
        # adding the same cleaner should not change anything
        dpm.set_intent(cleaner1)
        self.assertEqual(control, dpm.get_intent())
        # same cleaner different intent
        cleaner1 = {'clean_01': {'headers': 'h4'}}
        control = {'A': {'0': {'clean_01': {'dtype': ['number', 'str'], 'headers': 'h1'}}}}
        dpm.set_intent(cleaner1, order=0, replace_intent=False)
        self.assertEqual(control, dpm.get_intent())
        control = {'A': {'0': {'clean_01': {'headers': 'h4'}}}}
        dpm.set_intent(cleaner1, order=0, replace_intent=True)
        self.assertEqual(control, dpm.get_intent())
        # second cleaner
        cleaner2 = {'clean_02': {'headers': ['h2', 'h3'], 'regex': 'text'}}
        dpm.set_intent(cleaner2, order=0)
        control = {'A': {'0': {'clean_01': {'headers': 'h4'},
                         'clean_02': {'headers': ['h2', 'h3'], 'regex': 'text'}}}}
        self.assertEqual(control, dpm.get_intent())
        cleaner1 = {'clean_01': {'headers': 'h1', 'dtype': ['number', 'str']}}
        dpm.set_intent(cleaner1, order=0, replace_intent=True)
        control = {'A': {'0': {'clean_01': {'dtype': ['number', 'str'], 'headers': 'h1'},
                         'clean_02': {'headers': ['h2', 'h3'], 'regex': 'text'}}}}
        self.assertEqual(control, dpm.get_intent())

    def test_set_intent_order(self):
        dpm = ControlPropertyManager('test_abstract_properties')
        cleaner1 = {'clean_01': {'headers': 'h1'}}
        dpm.set_intent(cleaner1, order=0)
        control = {'A': {'0': {'clean_01': {'headers': 'h1'}}}}
        self.assertEqual(control, dpm.get_intent())
        dpm.set_intent(cleaner1, order=1)
        control = {'A': {'1': {'clean_01': {'headers': 'h1'}}}}
        self.assertEqual(control, dpm.get_intent())
        # change params
        cleaner1 = {'clean_01': {'headers': 'h3'}}
        dpm.set_intent(cleaner1, order=0)
        control = {'A': {'0': {'clean_01': {'headers': 'h3'}},
                         '1': {'clean_01': {'headers': 'h1'}}}}
        self.assertEqual(control, dpm.get_intent())
        # used -1 same intent, different params
        cleaner1 = {'clean_01': {'headers': 'h4'}}
        dpm.set_intent(cleaner1, order=-1)
        control = {'A': {'0': {'clean_01': {'headers': 'h3'}},
                         '1': {'clean_01': {'headers': 'h1'}},
                         '2': {'clean_01': {'headers': 'h4'}}}}
        self.assertEqual(control, dpm.get_intent())
        # replace just one of them using -1
        cleaner1 = {'clean_01': {'headers': 'h1'}}
        dpm.set_intent(cleaner1, order=-1)
        self.assertEqual(control, dpm.get_intent())

    def test_remove_intent(self):
        dpm = ControlPropertyManager('test_abstract_properties')
        # setup
        dpm.set_intent({'clean_01': {'headers': 'h1'}})
        # remove by label
        self.assertTrue(dpm.has_intent(level='A'))
        dpm.remove_intent('clean_01')
        self.assertEqual({}, dpm.get_intent())
        dpm.set_intent({'clean_01': {'headers': 'h1'}}, order=0)
        dpm.set_intent({'clean_01': {'headers': 'h4'}}, order=1)
        self.assertTrue(dpm.has_intent(level='A'))
        dpm.remove_intent('clean_01')
        self.assertEqual({}, dpm.get_intent())
        # remove by cleaner
        dpm.set_intent({'clean_01': {'headers': 'h1'}}, order=0)
        dpm.set_intent({'clean_01': {'headers': 'h4'}}, order=1)
        self.assertEqual(['0', '1'], CoreCommons.list_formatter(dpm.get_intent(level='A').keys()))
        dpm.remove_intent({'clean_01': {'headers': 'h4'}})
        self.assertTrue(dpm.has_intent(level='A'))
        self.assertEqual(['0'], CoreCommons.list_formatter(dpm.get_intent(level='A').keys()))
        # remove all
        dpm.set_intent({'clean_01': {'headers': 'h1'}})
        dpm.set_intent({'clean_02': {'headers': 'h4'}})
        dpm.set_intent({'clean_03': {'headers': 'h3'}}, level='B')
        dpm.reset_intents()
        self.assertEqual({}, dpm.get_intent())
        # test restricted remove
        dpm.set_intent({'clean_01': {'headers': 'h1'}}, level='A')
        dpm.set_intent({'clean_02': {'headers': 'h4'}}, level='B')
        dpm.remove_intent(level='C')
        dpm.remove_intent(level='A')
        self.assertEqual(['B'], CoreCommons.list_formatter(dpm.get_intent().keys()))
        dpm.remove_intent(level='B')
        self.assertEqual({}, dpm.get_intent())
        # remove all intent in a level
        dpm.set_intent({'clean_01': {'headers': 'h1'}}, level='A', order=-1)
        dpm.set_intent({'clean_01': {'headers': 'h2'}}, level='A', order=-1)
        dpm.set_intent({'clean_01': {'headers': 'h4'}}, level='B')
        self.assertEqual(['0', '1'], CoreCommons.list_formatter(dpm.get_intent(level='A').keys()))
        self.assertEqual(['0'], CoreCommons.list_formatter(dpm.get_intent(level='B').keys()))
        dpm.remove_intent(intent_param='clean_01', level='A')
        self.assertEqual([], CoreCommons.list_formatter(dpm.get_intent(level='A').keys()))
        self.assertEqual(['0'], CoreCommons.list_formatter(dpm.get_intent(level='B').keys()))

    def test_get_intent(self):
        dpm = ControlPropertyManager('test_abstract_properties')
        dpm.set_intent({'remove_head': {'headers': ['one', 'two']}, 'to_str': {'headers': ['five', 'six']}})
        dpm.set_intent({'clean_03': {'headers': 'h3'}}, level='B')
        result = dpm.get_intent(level='A', order=0, intent='remove_head')
        self.assertDictEqual({'remove_head': {'headers': ['one', 'two']}}, result)
        result = dpm.get_intent(level='A', order=1, intent='to_str')
        self.assertDictEqual({'to_str' : {'headers': ['five', 'six']}}, result)
        result = dpm.get_intent(level='A')
        self.assertEqual(['0', '1'], CoreCommons.list_formatter(result.keys()))
        result = dpm.get_intent(level='B')
        self.assertEqual(['0'], CoreCommons.list_formatter(result.keys()))
        self.assertEqual(['clean_03'], CoreCommons.list_formatter(result.get('0').keys()))
        result = dpm.get_intent()
        self.assertEqual(['A', 'B'], CoreCommons.list_formatter(result.keys()))

    def test_set_intent_description(self):
        pm = ControlPropertyManager('task')
        with self.assertRaises(ValueError) as context:
            pm.set_intent_description(level='control', text='Some intent level text')
        self.assertTrue(f"The intent_level 'control' can not be found " in str(context.exception))
        pm.set_intent({'clean_03': {'headers': 'h3'}}, level='control')
        pm.set_intent_description(level='control', text='Some intent level text')
        self.assertEqual(['Some intent level text'], pm.get_knowledge(catalog='intent', label='control',as_list=True))
        pm.remove_intent(level='control')
        self.assertEqual([], pm.get_knowledge(catalog='intent', label='control', as_list=True))

    def test_intent_report(self):
        dpm = ControlPropertyManager('test_abstract_properties')
        dpm.set_intent({'clean_03': {'headers': 'h3'}}, level='A')
        dpm.set_intent({'clean_02': {'dtype': ['number', 'str'], 'headers': 'h1'}}, level='C')
        dpm.set_intent({'clean_01': {'headers': 'h1'}}, order=-1)
        dpm.set_intent({'clean_01': {'headers': 'h3'}}, order=-1)
        report = dpm.report_intent()
        self.assertEqual(['clean_03', 'clean_01', 'clean_01', 'clean_02'], report['intent'])
        self.assertEqual(['A', 'A', 'A', 'C'], report['level'])
        self.assertEqual(['0', '1', '2', '0'], report['order'])
        self.assertEqual(["headers='h3'"], report['parameters'][0])
        self.assertEqual(["headers='h1'"], report['parameters'][1])
        self.assertEqual(["headers='h3'"], report['parameters'][2])
        self.assertEqual(['default']*4, report['creator'])
        self.assertEqual( ["dtype=['number', 'str']", "headers='h1'"], report['parameters'][3])
        report = dpm.report_intent(level_label='features')
        self.assertEqual(['features', 'order', 'intent', 'parameters', 'creator'], list(report))
        dpm.set_intent_description(level='A', text='Initial cleaning')
        report = dpm.report_intent(as_description=True, level_label='features')
        self.assertEqual(['features', 'description'], list(report))
        self.assertEqual(['A', 'C'], report['features'])
        self.assertEqual(['Initial cleaning', ''], report['description'])

    def test_run_book(self):
        pm = ControlPropertyManager('test_abstract_properties')
        result = pm.report_run_book()
        self.assertDictEqual({'name': [], 'run_book': []}, result)
        pm.set_run_book(book_name='run1', run_levels=[1,5,3])
        self.assertEqual([1,5,3], pm.get_run_book('run1'))
        pm.set_run_book(book_name='run2', run_levels=['A', 'B'])
        self.assertEqual(['A', 'B'], pm.get_run_book('run2'))
        pm.set_run_book(book_name='run1', run_levels=[1, 2, 3])
        self.assertEqual([1,2,3], pm.get_run_book('run1'))
        result = pm.report_run_book()
        self.assertDictEqual({'name': ['run2', 'run1'], 'run_book': [['A', 'B'], [1, 2, 3]]}, result)

    def test_schema(self):
        pm = ControlPropertyManager('test_abstract_properties')
        self.assertEqual([], pm.canonical_schemas)
        self.assertFalse(pm.has_canonical_schema(name='root'))
        schema1 =  dict({'att1': ['type', 'nulls']})
        schema2 =  dict({'A': [1, 0.98]})
        pm.set_canonical_schema('root', schema1)
        pm.set_canonical_schema('schema', schema2)
        self.assertTrue(pm.has_canonical_schema(name='root'))
        self.assertTrue(pm.has_canonical_schema(name='schema'))
        self.assertDictEqual(schema1, pm.get_canonical_schema('root'))
        self.assertDictEqual(schema2, pm.get_canonical_schema('schema'))
        self.assertCountEqual(['root', 'schema'], pm.canonical_schemas)
        self.assertFalse(pm.remove_canonical_schema('name'))
        self.assertTrue(pm.remove_canonical_schema('schema'))
        self.assertCountEqual(['root'], pm.canonical_schemas)
        self.assertDictEqual(schema1, pm.get_canonical_schema('root'))
        self.assertDictEqual({}, pm.get_canonical_schema('schema'))

    def test_file_pattern(self):
        pm = ControlPropertyManager('task')
        result = pm.file_pattern(name='source')
        self.assertEqual('hadron_control_task_source.parquet', result)
        result = pm.file_pattern(name='source', file_type='parquet')
        self.assertEqual('hadron_control_task_source.parquet', result)
        result = pm.file_pattern(name='source', stamped="hours")
        self.assertEqual('hadron_control_task_source${TO_HOURS}.parquet', result)
        result = pm.file_pattern(name='source', versioned=True, stamped="minutes")
        self.assertEqual('hadron_control_task_source${VERSION}${TO_MINUTES}.parquet', result)
        result = pm.file_pattern(name='source', versioned=True)
        self.assertEqual('hadron_control_task_source${VERSION}.parquet', result)
        # Check it works with connector contract
        cc = ConnectorContract(uri=result, module_name="", handler="", version="v1.01")
        self.assertEqual("hadron_control_task_source_v1.01.parquet", cc.uri)
        # test prefix & suffix & suffix_name
        result = pm.file_pattern(name='source', prefix="prefix_")
        self.assertEqual('prefix_source.parquet', result)
        result = pm.file_pattern(name='source')
        self.assertEqual('hadron_control_task_source.parquet', result)
        result = pm.file_pattern(name='source', suffix="?name=fred&type=male")
        self.assertEqual('hadron_control_task_source.parquet?name=fred&type=male', result)
        result = pm.file_pattern(name='source', prefix="prefix_", suffix="?name=fred&type=male")
        self.assertEqual('prefix_source.parquet?name=fred&type=male', result)
        # test path
        result = pm.file_pattern(name='source', path="s3://bucket/path")
        self.assertEqual('s3://bucket/path/hadron_control_task_source.parquet', result)
        result = pm.file_pattern(name='source', path=["s3://bucket", "path"])
        self.assertEqual('s3://bucket/path/hadron_control_task_source.parquet', result)
        # test project
        result = pm.file_pattern(name='source', project='tester')
        self.assertEqual('tester_control_task_source.parquet', result)

    def test_modify_connector_uri(self):
        pm = ControlPropertyManager('task')
        connector_name = 'connector'
        uri = "s3://bucket/path/hadron_control_task_connector.parquet?name=fred&value=45"
        cc = ConnectorContract(uri=uri, module_name='module.package', handler='Handler')
        pm.set_connector_contract(connector_name=connector_name, connector_contract=cc)
        control = "http://git.com/project-hadron/hadron_control_task_connector.parquet?name=fred&value=45"
        result = pm.modify_connector_uri(connector_name=connector_name, old_pattern="s3://bucket/path/", new_pattern="http://git.com/project-hadron/")
        self.assertEqual(control, pm.get_connector_contract(connector_name=connector_name).uri)

    def test_modify_connector_aligned(self):
        pm = ControlPropertyManager('task')
        connector_name = 'connector'
        uri = "s3://bucket/path/hadron_control_task_connector.parquet?name=fred&value=45"
        cc = ConnectorContract(uri=uri, module_name='module.package', handler='Handler')
        template = ConnectorContract(uri="http://git.com/hadron/", module_name='module.parquet', handler='PickleHandler',
                                     sep= ',', encoder= 'latin1')
        pm.set_connector_contract(connector_name=connector_name, connector_contract=cc, aligned=True)
        pm.modify_connector_aligned(connector_name=connector_name, template_contract=template)
        control = "http://git.com/hadron/hadron_control_task_connector.parquet?name=fred&value=45"
        result = pm.get_connector_contract(connector_name=connector_name)
        self.assertEqual('module.parquet', result.raw_module_name)
        self.assertEqual('PickleHandler', result.raw_handler)
        self.assertEqual(control, result.raw_uri)
        self.assertDictEqual( {'encoder': 'latin1', 'sep': ','}, result.kwargs)

    def test_reset_each(self):
        pm = ControlPropertyManager('task')
        pm.reset_canonical_schemas()
        pm.reset_connector_contracts()
        pm.reset_intents()
        pm.reset_knowledge()
        pm.reset_run_books()
        pm.reset_snapshots()
        result = pm.get(pm.KEY.contract_key)
        control = {'cleaners': {}, 'description': '', 'status': 'discovery', 'version': '0.0.1', 'connectors': {}, 'intent': {},
                   'meta': {'class': 'ControlPropertyManager', 'module': pm.__module__.split(".")}, 'knowledge': {'schema': {}}, 'run_book': {}, 'snapshot': {}}
        self.assertDictEqual(control, result)

    def test_report_connectors_align(self):
        pm = ControlPropertyManager('task')
        connector_name = 'connector'
        uri = "https://bucket/path/hadron_control_task_connector.parquet?name=fred&value=45"
        cc = ConnectorContract(uri=uri, module_name='module.package', handler='Handler')
        pm.set_connector_contract(connector_name='source', connector_contract=cc)
        pm.set_connector_contract(connector_name='persist', connector_contract=cc, aligned=True)
        result = pm.report_connectors()
        self.assertEqual([False, True], result.get('aligned'))

    def test_report_task(self):
        pm = ControlPropertyManager('task')
        control = ['cleaners', 'description', 'version', 'status', 'connectors', 'intent', 'run_book', 'knowledge']
        self.assertCountEqual(control, list(pm.report_task().keys()))

    def test_report_intent_param(self):
        pm = ControlPropertyManager('task')
        cleaner1 = {'get_number': {'range_value': '0', 'to_value': 24}}
        pm.set_intent(cleaner1, level='age', order=0)
        result = pm.report_intent_params('age')
        self.assertCountEqual(['order', 'intent', 'parameter', 'value'], list(result.keys()))


if __name__ == '__main__':
    unittest.main()