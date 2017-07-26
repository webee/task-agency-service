import importlib
from typing import List, Callable
from abc import ABCMeta, abstractmethod
import uuid


class AbsTask(metaclass=ABCMeta):
    @abstractmethod
    def run(self, *args, **kwargs):
        raise NotImplementedError()


class SessionData(object):
    def __init__(self, id: str, task_id: str, state: dict, result: dict):
        self.id = id
        self.task_id = task_id
        self.state = state
        self.result = result

    def __repr__(self):
        return repr({
            'id': self.id,
            'task_id': self.task_id,
            'state': self.state,
            'result': self.result,
        })


class AskForParamsError(Exception):
    def __init__(self, param_requirements, message):
        super().__init__(message)
        self.param_requirements = param_requirements


class AbsSessionTask(AbsTask):
    def __init__(self, session_data: SessionData):
        self._session_data = session_data
        self._done = False

    @abstractmethod
    def run(self, params: dict):
        try:
            res = self._do_run(params)
            self._set_done()
            # TODO: 正常返回
        except AskForParamsError as e:
            # TODO: 请求参数
            pass
        except Exception as e:
            self._set_done()
            # TODO: 错误返回
            return {
            }

    @abstractmethod
    def _do_run(self, params: dict):
        raise NotImplementedError()

    @property
    def session_data(self) -> SessionData:
        return self._session_data

    @property
    def done(self) -> bool:
        return self._done

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

    def start(self, task_id):
        """
        start a task by task_id
        :param task_id: task type id
        :return: session_id, task result
        """
        session_id = self._sig.new()
        session_data = SessionData(session_id, task_id, {}, {})
        return session_id, self._run(session_data, {})

    def resume(self, session_id, params):
        """
        resume a started task session
        :param session_id: session id
        :param params: params
        :return: session_id, task result
        """
        session_data = self._ss.get_session(session_id)
        if session_data is None:
            raise PermissionError('session not exists')

        return session_id, self._run(session_data, params)

    def register_result_handler(self, handler: AbsResultHandler):
        self._result_handlers.append(handler)

    def _run(self, session_data: SessionData, params: dict):
        task = self._get_task(session_data)
        res = task.run(params)
        if task.done:
            result = task.session_data.result
            for handler in self._result_handlers:
                handler.handle(result)
            self._ss.remove_session(session_data.id)
        else:
            self._ss.save_session(task.session_data)
        return res

    def _get_task(self, session_data: SessionData) -> AbsSessionTask:
        task_id = session_data.task_id
        task_cls = self._tcf.find(task_id)
        return task_cls(session_data)


class UUIDSessionIDGenerator(AbsSessionIDGenerator):
    def new(self) -> str:
        return uuid.uuid4().hex


class MemorySessionStorage(AbsSessionStorage):
    def __init__(self):
        self.__sessions = {}

    def save_session(self, session_data: SessionData):
        self.__sessions[session_data.id] = session_data

    def get_session(self, session_id: str) -> SessionData:
        return self.__sessions.get(session_id)

    def remove_session(self, session_id: str):
        del self.__sessions[session_id]


class PathTaskClassFinder(AbsTaskClassFinder):
    def __init__(self, get_path_func: Callable, cls_name: str):
        self._get_path_func = get_path_func
        self._cls_name = cls_name

    def find(self, task_id: str):
        m = importlib.import_module(self._get_path_func(task_id))
        return getattr(m, self._cls_name)
