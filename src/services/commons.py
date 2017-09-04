from abc import ABCMeta, abstractmethod
import requests
from .service import AbsTaskUnitSessionTask


class AbsFetchTask(AbsTaskUnitSessionTask, metaclass=ABCMeta):
    def _prepare(self, data=None):
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

        # data
        if isinstance(data, dict):
            self.state['meta'] = data.get('meta', {})

    @property
    def prepared_meta(self):
        return self.state.get('meta')

    def _update_run_params(self, params: dict):
        if not self.prepared_meta:
            return params
        return self._params_handler(params)

    def _update_param_requirements(self, param_requirements, details):
        if not self.prepared_meta:
            return param_requirements
        return self._param_requirements_handler(param_requirements, details)

    def _params_handler(self, params: dict):
        # TODO: 实现类根据self.prepared_meta，去补充params没提供的参数
        return params

    def _param_requirements_handler(self, param_requirements, details):
        # TODO: 实现类根据self.prepared_meta和details确定需要去掉哪些参数请求
        return param_requirements

    def _update_session_data(self):
        super()._update_session_data()
        self.state['cookies'] = self.s.cookies

    @abstractmethod
    def _get_common_headers(self):
        """恢复状态里设置的通用头部"""
        return {}

    @property
    def result_key(self):
        return self.result.get('key')

    @result_key.setter
    def result_key(self, key):
        self.result['key'] = key

    @property
    def result_meta(self) -> dict:
        return self.result.get('meta')

    @property
    def result_data(self) -> dict:
        return self.result.get('data')

    @property
    def result_identity(self) -> dict:
        return self.result.get('identity')
