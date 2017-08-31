from abc import ABCMeta, abstractmethod
import requests
from .service import AbsTaskUnitSessionTask


class AbsFetchTask(AbsTaskUnitSessionTask, metaclass=ABCMeta):
    def _prepare(self):
        state: dict = self.state
        self.s = requests.Session()
        cookies = state.get('cookies')
        if cookies:
            self.s.cookies = cookies
        self.s.headers.update(self._get_common_headers())

        # result
        result: dict = self.result
        result.setdefault('meta', {})
        result.setdefault('data', {})
        result.setdefault('identity', {})

    def _update_session_data(self):
        super()._update_session_data()
        self.state['cookies'] = self.s.cookies

    @abstractmethod
    def _get_common_headers(self):
        """恢复状态里设置的通用头部"""
        return {}
