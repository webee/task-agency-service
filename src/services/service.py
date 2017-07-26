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
        raise NotImplementedError()

    @property
    def session_data(self) -> SessionData:
        return self._session_data

    @property
    def done(self) -> bool:
        return self._done

    def _set_done(self):
        self._done = True


class AbsSessionTasksManager(metaclass=ABCMeta):
    def start(self, task_id):
        """
        start a task by task_id
        :param task_id: task type id
        :return: session_id, task result
        """
        session_id = self._new_session_id()
        session_data = SessionData(session_id, task_id, {}, {})
        return session_id, self._run(session_data, {})

    def resume(self, session_id, params):
        """
        resume a started task session
        :param session_id: session id
        :param params: params
        :return: session_id, task result
        """
        session_data = self._get_session_data(session_id)
        if session_data is None:
            raise PermissionError('session not exists')

        return session_id, self._run(session_data, params)

    def _run(self, session_data: SessionData, params: dict):
        task = self._get_task(session_data)
        res = task.run(params)
        if task.done:
            self._remove_session(session_data.id)
        else:
            self._save_session(task.session_data)
        return res

    def _get_task(self, session_data: SessionData) -> AbsSessionTask:
        task_id = session_data.task_id
        task_cls = self._get_task_cls(task_id)
        return task_cls(session_data)

    @abstractmethod
    def _get_task_cls(self, task_id: str):
        raise NotImplementedError()

    @abstractmethod
    def _new_session_id(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def _get_session(self, session_id: str) -> SessionData:
        raise NotImplementedError()

    @abstractmethod
    def _remove_session(self, session_id: str):
        raise NotImplementedError()

    @abstractmethod
    def _save_session(self, session_data: SessionData):
        raise NotImplementedError()


class TestAbsMemorySessionTasksManager(AbsSessionTasksManager):
    def _new_session_id(self) -> str:
        return uuid.uuid4().hex

    def __init__(self):
        self.__sessions = {}

    def _save_session(self, session_data: SessionData):
        self.__sessions[session_data.id] = session_data

    def _get_session(self, session_id: str) -> SessionData:
        return self.__sessions.get(session_id)

    def _remove_session(self, session_id: str):
        del self.__sessions[session_id]
