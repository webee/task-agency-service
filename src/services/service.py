import importlib
import logging
import os
import pkgutil
import re
import time
import traceback
import uuid
from abc import ABCMeta, abstractmethod
from collections import namedtuple
from typing import List, Callable, TypeVar

from services.errors import AskForParamsError, TaskNotAvailableError, PreconditionNotSatisfiedError, \
    TaskNotImplementedError
from services.utils import AttributeDict

logger = logging.getLogger(__name__)


class AbsTask(metaclass=ABCMeta):
    @abstractmethod
    def run(self, *args, **kwargs):
        pass


def if_not_none_else(v, e):
    return v if v is not None else e


class SessionData(object):
    def __init__(self, id: str = None, task_id: str = None, state: dict = None, result: dict = None):
        self.id = if_not_none_else(id, '')
        self.task_id = if_not_none_else(task_id, '')
        self.state = if_not_none_else(state, {})
        self.result = if_not_none_else(result, {})

    def __repr__(self):
        return repr(dict(id=self.id, task_id=self.task_id, state=self.state, result=self.result))


class AbsStatefulTask(AbsTask):
    task_info = {}

    @classmethod
    def inspect(cls, params: dict):
        raise NotImplementedError()

    @abstractmethod
    def run(self, params=None):
        raise NotImplementedError()

    @abstractmethod
    def query(self, params=None):
        raise NotImplementedError()


class AbsSessionTask(AbsStatefulTask):
    @classmethod
    def inspect(cls, params: dict):
        params = if_not_none_else(params, {})
        # 先尝试查询元数据
        if '_t' in params:
            return cls._inspect_meta(params)
        # 如没被处理，则尝试其它查询
        try:
            return cls._inspect(params)
        except:
            logger.warning(traceback.format_exc())

    @classmethod
    def _inspect_meta(cls, params: dict):
        """
        检查任务元数据
        :param params: parameters
        :return:
        """
        t = params.get('_t')
        return cls.task_info.get(t)

    @classmethod
    def _inspect(cls, params: dict):
        t = params.get('t')
        if t is None:
            return cls.task_info
        return cls.task_info.get(t)

    def __init__(self, session_data: SessionData=None, prepare_data=None, is_start=True):
        super().__init__()
        self._session_data = if_not_none_else(session_data, SessionData())
        self._is_start = is_start
        # 任务未实现
        self._not_implemented = False
        # 任务结束
        self._end = False
        # 任务完成
        self._done = False

        self._setup()
        if prepare_data is None:
            # FIXME: 兼容之前无参方法, 在所有实现都修复后去掉
            self._prepare()
        else:
            self._prepare(prepare_data)

    def _setup(self):
        """设置
        for extend sub class to use
        :return:
        """
        pass

    @abstractmethod
    def _prepare(self, data=None):
        """恢复状态，初始化结果
        for concrete class to use
        :return:
        """
        pass

    def _update_run_params(self, params: dict):
        """修改运行参数
        :param params: 原运行参数
        :return: 新运行参数
        """
        return params

    def _update_param_requirements(self, param_requirements, details):
        """修改参数请求
        :param param_requirements: 原参数请求
        :param details: 可能的请求细节
        :return: 新参数请求
        """
        return param_requirements

    def run(self, params: dict = None):
        params = if_not_none_else(params, {})
        try:
            # 修改运行参数
            params = self._update_run_params(params)
            res = self._run(params)
            self._set_end()
            self._set_done()
            # NOTE: 正常返回
            return dict(end=self.end, done=self.done, data=res)
        except AskForParamsError as e:
            # NOTE: 请求参数
            self._update_session_data()
            # 修改参数请求
            param_requirements = self._update_param_requirements(e.param_requirements, e.details)
            res = dict(end=self.end, done=self.done, param_requirements=param_requirements)
            if e.err_msg:
                res.update(dict(err_msg=e.err_msg))
            return res
        except Exception as e:
            # NOTE: 异常
            self._set_end()
            not_available = isinstance(e, TaskNotAvailableError)
            if isinstance(e, TaskNotImplementedError):
                self._set_not_implemented()
            if not not_available:
                logger.error("%s, %s\n%s\n%s", self.session_data.id, self.session_data.task_id,
                             params,
                             traceback.format_exc())
            return dict(end=self.end, done=self.done, not_available=not_available, err_msg=str(e))

    def query(self, params: dict = None):
        params = if_not_none_else(params, {})
        try:
            data = self._query(params)
            if data is None:
                # 如没被处理，则尝试查询元数据
                data = self._query_meta(params)
            return dict(ret=True, data=data)
        except Exception as e:
            logger.warning(traceback.format_exc())
            return dict(ret=False, err_msg=str(e))
        finally:
            self._update_session_data()

    @abstractmethod
    def _update_session_data(self):
        """保存状态
        update session_data
        :return:
        """
        pass

    @abstractmethod
    def _run(self, params: dict):
        """执行任务"""
        pass

    def _query_meta(self, params: dict):
        """
        查询任务元数据
        :param params: parameters
        :return:
        """
        t = params.get('_t')
        if t == '_meta.session':
            return self.session_data

    @abstractmethod
    def _query(self, params: dict):
        """任务状态查询"""
        pass

    @property
    def session_data(self) -> SessionData:
        return self._session_data

    @property
    def state(self) -> dict:
        return self._session_data.state

    @property
    def result(self) -> dict:
        return self._session_data.result

    @property
    def is_start(self) -> bool:
        return self._is_start

    @property
    def not_implemented(self) -> bool:
        return self._not_implemented

    def _set_not_implemented(self):
        self._not_implemented = True

    @property
    def end(self) -> bool:
        return self._end

    def _set_end(self):
        self._end = True

    @property
    def done(self) -> bool:
        return self._done

    def _set_done(self):
        self._done = True


TaskUnitWithPre = namedtuple('TaskUnitWithPre', ['unit', 'pre'])


class AbsTaskUnitSessionTask(AbsSessionTask, metaclass=ABCMeta):
    _CUR_TASK_UNIT_IDX = '_cur_task_unit_idx'

    def _setup(self):
        super()._setup()
        # 实现全局变量
        self.g = AttributeDict()
        self._task_units: List[TaskUnitWithPre] = []
        self._task_unit_indexes = {}
        self._setup_task_units()

        self._cur_task_unit_idx = self.state.get(self._CUR_TASK_UNIT_IDX, 0 if len(self._task_units) > 0 else -1)

    @abstractmethod
    def _setup_task_units(self):
        """设置任务执行单元"""
        pass

    def _add_unit(self, unit: Callable, pre: Callable = None):
        idx = len(self._task_units)
        self._task_units.append(TaskUnitWithPre(unit, pre))
        self._task_unit_indexes[unit] = idx

    @abstractmethod
    def _update_session_data(self):
        self.session_data.state[self._CUR_TASK_UNIT_IDX] = self._cur_task_unit_idx

    def _get_task_unit_idx(self, unit):
        return self._task_unit_indexes.get(unit, -1)

    def _get_cur_task_unit(self):
        if 0 <= self._cur_task_unit_idx < len(self._task_units):
            return self._task_units[self._cur_task_unit_idx]

    def _run(self, params: dict):
        task_unit = self._get_cur_task_unit()
        if task_unit is None:
            return

        try:
            task_unit.unit(params)
            self._cur_task_unit_idx += 1

            while self._cur_task_unit_idx < len(self._task_units):
                task_unit = self._get_cur_task_unit()
                task_unit.unit()
                self._cur_task_unit_idx += 1
            key = self.result.get('key')
            if not key:
                raise RuntimeError('result key not set')
            return dict(task_id=self.session_data.task_id, key=key)
        except PreconditionNotSatisfiedError:
            self._cur_task_unit_idx = self._get_task_unit_idx(task_unit.pre)
            return self._run(params)


class AbsSessionStorage(metaclass=ABCMeta):
    @abstractmethod
    def get_session(self, session_id: str) -> SessionData:
        raise NotImplementedError()

    @abstractmethod
    def remove_session(self, session_id: str):
        raise NotImplementedError()

    @abstractmethod
    def save_session(self, session_data: SessionData, expire=None):
        raise NotImplementedError()


class AbsSessionIDGenerator(metaclass=ABCMeta):
    @abstractmethod
    def new(self, task_id=None) -> str:
        raise NotImplementedError()


class AbsTaskClassFinder(metaclass=ABCMeta):
    @abstractmethod
    def find(self, task_id: str) -> TypeVar(AbsSessionTask):
        raise NotImplementedError()


class AbsTaskResultHandler(metaclass=ABCMeta):
    @abstractmethod
    def handle(self, task_id: str, result: dict, is_done: bool=True):
        raise NotImplementedError()


class SessionTasksManager(object):
    def __init__(self, session_id_generator: AbsSessionIDGenerator,
                 session_storage: AbsSessionStorage, task_class_finder: AbsTaskClassFinder):
        super().__init__()
        self._sig = session_id_generator
        self._ss = session_storage
        self._tcf = task_class_finder
        self._result_handlers: List[AbsTaskResultHandler] = []
        self._not_implemented_result_handlers: List[AbsTaskResultHandler] = []

    def inspect(self, task_id, params=None):
        """
        inspect task info
        :param task_id: task type id
        :param params: parameters
        :return:
        """
        task_cls: AbsSessionTask = self._tcf.find(task_id)
        params = if_not_none_else(params, {})
        return task_cls.inspect(params)

    def start(self, task_id, params=None, prepare_data=None):
        """
        start a task by task_id
        :param task_id: task type id
        :param params: parameters
        :param prepare_data: prepare data
        :return: session_id, task result
        """
        session_id = self._sig.new(task_id)
        session_data = SessionData(session_id, task_id, {}, {})
        return session_id, self._run(session_data, params, prepare_data, is_start=True)

    def resume(self, session_id, params=None, prepare_data=None):
        """
        resume a started task session
        :param session_id: session id
        :param params: parameters
        :param prepare_data: prepare data
        :return: task result
        """
        session_data = self._get_session_data(session_id)
        return self._run(session_data, params, prepare_data, is_start=False)

    def query(self, session_id, params=None, prepare_data=None):
        """
        query task info from a started task session
        :param session_id: session id
        :param params: parameters
        :param prepare_data: prepare data
        :return: result
        """
        session_data = self._get_session_data(session_id)
        task = self._get_task(session_data, prepare_data, is_start=False)
        res = task.query(params)
        self._ss.save_session(task.session_data, task.inspect({'_t': '_meta.session.expire'}))
        return res

    def abort(self, session_id):
        """
        abort task
        :param session_id:  session register_result_handlerid
        :return:
        """
        self._ss.remove_session(session_id)

    def register_result_handler(self, handler: AbsTaskResultHandler):
        self._result_handlers.append(handler)

    def register_not_implemented_result_handler(self, handler: AbsTaskResultHandler):
        self._not_implemented_result_handlers.append(handler)

    def _run(self, session_data: SessionData, params: dict, prepare_data, is_start):
        task = self._get_task(session_data, prepare_data, is_start)
        res = task.run(params)
        if task.end:
            # 任务结束
            result = task.session_data.result
            if task.not_implemented:
                # 任务未实现处理
                for handler in self._not_implemented_result_handlers:
                    try:
                        handler.handle(task.session_data.task_id, result)
                    except:
                        logger.warning(traceback.format_exc())
            else:
                # 任务成功或失败
                for handler in self._result_handlers:
                    try:
                        handler.handle(task.session_data.task_id, result, is_done=task.done)
                    except Exception as e:
                        logger.warning(traceback.format_exc())

            # 删除会话
            self._ss.remove_session(session_data.id)
        else:
            self._ss.save_session(task.session_data, task.inspect({'_t': '_meta.session.expire'}))
        return res

    def _get_session_data(self, session_id):
        session_data = self._ss.get_session(session_id)
        if session_data is None:
            raise ValueError('task session not exists')
        return session_data

    def _get_task(self, session_data: SessionData, prepare_data, is_start) -> AbsSessionTask:
        task_id = session_data.task_id
        try:
            task_cls = self._tcf.find(task_id)
            if task_cls is None:
                raise RuntimeError()
        except:
            logger.warning(traceback.format_exc())
            raise ImportError('can not find task: %s' % task_id)

        return task_cls(session_data, prepare_data, is_start=is_start)


class UUIDSessionIDGenerator(AbsSessionIDGenerator):
    def new(self, task_id=None) -> str:
        return uuid.uuid4().hex


class MemorySessionStorage(AbsSessionStorage):
    """内存存储，测试用"""
    def __init__(self, expire=None):
        self._expire = expire
        self.__sessions = {}

    def save_session(self, session_data: SessionData, expire=None):
        expire = expire or self._expire
        expire_at = None
        if expire:
            expire_at = time.time() + expire
        self.__sessions[session_data.id] = (session_data, expire_at)

    def get_session(self, session_id: str) -> SessionData:
        res = self.__sessions.get(session_id)
        if res is not None:
            data, expire_at = res
            if expire_at is None or expire_at > time.time():
                return data
            self.remove_session(session_id)

    def remove_session(self, session_id: str):
        if session_id in self.__sessions:
            del self.__sessions[session_id]


class PathTaskClassFinder(AbsTaskClassFinder):
    """通过路径模式寻找"""
    def __init__(self, get_path_func: Callable, cls_name: str):
        self._get_path_func = get_path_func
        self._cls_name = cls_name

    def find(self, task_id: str):
        m = importlib.import_module(self._get_path_func(task_id))
        return getattr(m, self._cls_name)


class PackageTaskClassFinder(AbsTaskClassFinder):
    def __init__(self, base_package: str, cls_name: str, task_name_pattern: str, get_task_name_func: Callable):
        """
        递归扫描package寻找指定的任务类
        :param base_path: 任务父路径
        :param cls_name: 任务类名称
        :param task_name_pattern: 任务名模式
        :param get_task_name_func: 通过task_id生成任务名的方法
        """
        self._base_path = importlib.import_module(base_package).__path__[0]
        self._cls_name = cls_name
        self._task_name_pattern = re.compile(task_name_pattern)
        self._get_task_name_func = get_task_name_func
        self._task_modules = {}
        self._initial_scan(self._base_path)

    def _initial_scan(self, base_path):
        for importer, name, is_pkg in pkgutil.iter_modules([base_path]):
            if name.startswith('_'):
                continue

            if self._task_name_pattern.match(name):
                self._task_modules[name] = importer.find_module(name).load_module(name)
                continue

            if is_pkg:
                self._initial_scan(os.path.join(base_path, name))

    def find(self, task_id: str):
        m = self._task_modules.get(self._get_task_name_func(task_id))
        if m:
            return getattr(m, self._cls_name)


if __name__ == '__main__':
    from services.social_insurance import tasks
    ptcf = PackageTaskClassFinder(tasks.__package__, 'Task', r'^c_\d+$', lambda task_id: 'c_%s' % task_id)
