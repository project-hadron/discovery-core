from ds_core.properties.abstract_properties import AbstractPropertyManager

__author__ = 'Darryl Oatridge'


class PyarrowPropertyManager(AbstractPropertyManager):

    def __init__(self, task_name: str, creator: str):
        # set additional keys
        root_keys = []
        knowledge_keys = []
        super().__init__(task_name=task_name, root_keys=root_keys, knowledge_keys=knowledge_keys, creator=creator)
