import importlib
import time
from typing import List, Callable
from abc import ABCMeta, abstractmethod
import uuid
from collections import namedtuple


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


class AskForParamsError(Exception):
    def __init__(self, param_requirements, err_msg=None, message='parameters required'):
        super().__init__(message)
        self.param_requirements = param_requirements
        self.err_msg = err_msg


class PreconditionNotSatisfiedError(Exception):
    pass


class AskForParamsError(Exception):
    def __init__(self, param_requirements, err_msg=None, message='parameters required'):
        super().__init__(message)
        self.param_requirements = param_requirements
        self.err_msg = err_msg


class AbsSessionTask(AbsTask):
    def __init__(self, session_data: SessionData, is_start=True):
        super().__init__()
        self._session_data = session_data
        self._is_start = is_start
        self._done = False

        self._prepare()

    @abstractmethod
    def _prepare(self):
        pass

    def run(self, params: dict = None):
        params = if_not_none_else(params, {})
        try:
            res = self._run(params)
            self._set_done()
            # NOTE: 正常返回
            return dict(ret=True, done=True, data=res)
        except AskForParamsError as e:
            # NOTE: 请求参数
            self._update_session_data()
            res = dict(ret=True, done=False, param_requirements=e.param_requirements)
            if e.err_msg:
                res.update(err_msg=e.err_msg)
            return res
        except Exception as e:
            # NOTE: 异常
            self._set_done()
            return dict(ret=False, err_msg=str(e))

    def query(self, params: dict = None):
        params = if_not_none_else(params, {})
        try:
            data = self._query(params)
            if data is None:
                # 如没被处理，则尝试查询元数据
                data = self._query_meta(params)
            return dict(ret=True, data=data)
        except Exception as e:
            return dict(ret=False, err_msg=str(e))
        finally:
            self._update_session_data()

    @abstractmethod
    def _update_session_data(self):
        """
        update session_data
        :return:
        """
        pass

    @abstractmethod
    def _run(self, params: dict):
        pass

    def _query_meta(self, params: dict):
        """
        查询任务元数据
        :param params: parameters
        :return:
        """
        t = params.get('t')
        if t == '_meta.session':
            return self.session_data

    @abstractmethod
    def _query(self, params: dict):
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
    def done(self) -> bool:
        return self._done

    @property
    def is_start(self) -> bool:
        return self._is_start

    def _set_done(self):
        self._done = True


class AbsSessionStorage(metaclass=ABCMeta):
    @abstractmethod
    def get_session(self, session_id: str) -> SessionData:
        raise NotImplementedError()

    @abstractmethod
    def remove_session(self, session_id: str):
        raise NotImplementedError()

    @abstractmethod
    def save_session(self, session_data: SessionData):
        raise NotImplementedError()


class AbsSessionIDGenerator(metaclass=ABCMeta):
    @abstractmethod
    def new(self, *args, **kwargs) -> str:
        raise NotImplementedError()


class AbsTaskClassFinder(metaclass=ABCMeta):
    @abstractmethod
    def find(self, task_id: str):
        raise NotImplementedError()


class AbsResultHandler(metaclass=ABCMeta):
    @abstractmethod
    def handle(self, result: dict):
        raise NotImplementedError()


class SessionTasksManager(object):
    def __init__(self, session_id_generator: AbsSessionIDGenerator,
                 session_storage: AbsSessionStorage, task_class_finder: AbsTaskClassFinder):
        super().__init__()
        self._sig = session_id_generator
        self._ss = session_storage
        self._tcf = task_class_finder
        self._result_handlers: List[AbsResultHandler] = []

    def start(self, task_id, params=None):
        """
        start a task by task_id
        :param task_id: task type id
        :param params: parameters
        :return: session_id, task result
        """
        session_id = self._sig.new()
        session_data = SessionData(session_id, task_id, {}, {})
        return session_id, self._run(session_data, params)

    def resume(self, session_id, params=None):
        """
        resume a started task session
        :param session_id: session id
        :param params: parameters
        :return: task result
        """
        session_data = self._get_session_data(session_id)
        return self._run(session_data, params, is_start=False)

    def query(self, session_id, params=None):
        """
        query task info from a started task session
        :param session_id: session id
        :param params: parameters
        :return: result
        """
        session_data = self._get_session_data(session_id)
        task = self._get_task(session_data)
        res = task.query(params)
        self._ss.save_session(task.session_data)
        return res

    def register_result_handler(self, handler: AbsResultHandler):
        self._result_handlers.append(handler)

    def _run(self, session_data: SessionData, params: dict, is_start=True):
        task = self._get_task(session_data, is_start=is_start)
        res = task.run(params)
        if task.done:
            result = task.session_data.result
            for handler in self._result_handlers:
                handler.handle(result)
            self._ss.remove_session(session_data.id)
        else:
            self._ss.save_session(task.session_data)
        return res

    def _get_session_data(self, session_id):
        session_data = self._ss.get_session(session_id)
        if session_data is None:
            raise ValueError('task session not exists')
        return session_data

    def _get_task(self, session_data: SessionData, is_start=True) -> AbsSessionTask:
        task_id = session_data.task_id
        task_cls = self._tcf.find(task_id)
        return task_cls(session_data, is_start=is_start)


class UUIDSessionIDGenerator(AbsSessionIDGenerator):
    def new(self) -> str:
        return uuid.uuid4().hex


class MemorySessionStorage(AbsSessionStorage):
    def __init__(self, expire=None):
        self._expire = expire
        self.__sessions = {}

    def save_session(self, session_data: SessionData):
        self.__sessions[session_data.id] = (session_data, time.time())

    def get_session(self, session_id: str) -> SessionData:
        res = self.__sessions.get(session_id)
        if res is not None:
            data, t = res
            if self._expire is None or t + self._expire > time.time():
                return data
            self.remove_session(session_id)

    def remove_session(self, session_id: str):
        if session_id in self.__sessions:
            del self.__sessions[session_id]


class PathTaskClassFinder(AbsTaskClassFinder):
    def __init__(self, get_path_func: Callable, cls_name: str):
        self._get_path_func = get_path_func
        self._cls_name = cls_name

    def find(self, task_id: str):
        m = importlib.import_module(self._get_path_func(task_id))
        return getattr(m, self._cls_name)


TaskUnitWithPre = namedtuple('TaskUnitWithPre', ['unit', 'pre'])


class AbsTaskUnitSessionTask(AbsSessionTask, metaclass=ABCMeta):
    _CUR_TASK_UNIT_IDX = '_cur_task_unit_idx'

    def __init__(self, session_data: SessionData):
        super().__init__(session_data)
        self._task_units: List[TaskUnitWithPre] = []
        self._task_unit_indexes = {}
        self._setup_task_units()

        self._cur_task_unit_idx = self.state.get(self._CUR_TASK_UNIT_IDX, 0 if len(self._task_units) > 0 else -1)

    @abstractmethod
    def _setup_task_units(self):
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
            res = task_unit.unit(params)
            self._cur_task_unit_idx += 1

            while self._cur_task_unit_idx < len(self._task_units):
                task_unit = self._get_cur_task_unit()
                res = task_unit.unit()
                self._cur_task_unit_idx += 1
            return res
        except PreconditionNotSatisfiedError:
            self._cur_task_unit_idx = self._get_task_unit_idx(task_unit.pre)
            return self._run(params)
