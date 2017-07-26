from services.service import TestAbsMemorySessionTasksManager
import importlib


class TestTasksManager(TestAbsMemorySessionTasksManager):
    def _get_task_cls(self, task_id: str):
        t = importlib.import_module(__package__ + '.tasks.t_%s' % task_id)
        return t.Task


def query():
    """
    测试查询数据
    :return:
    """
    pass
