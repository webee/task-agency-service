from services.test.mock_site import TestSite
from services.test.mock import UserAgent, LogRequestFilter
from services.service import AbsSessionTask


test_site = TestSite()


class Task(AbsSessionTask):
    X_PARAM_REQUIREMENTS = {
    }

    def __init__(self, state=None, params=None, result=None):
        # 执行状态
        self.state = state
        # 外部参数
        self.params = params
        # 中间结果
        self.result = result

        self.done = False

        self.key = None
        self.meta = None
        self.data = None

        # initialize
        self._init_state()

    def get_result(self):
        return self.state

    def is_done(self) -> bool:
        return self.done

    def get_state(self):
        return self.state

    def _init_state(self):
        self.ua = UserAgent(test_site, self.state.get('session'))
        self.ua.register_request_filter(LogRequestFilter())

    @property
    def s(self):
        return self.state['s']

    def run(self):
        self._fetch_x()

    def _get_login_params(self):
        # check params
        username = self.params['username']
        password = self.params['password']
        vc = self.params['vc']

        return username, password, vc

    def _fetch_x(self):
        username, password, vc = self._get_login_params()
        try:
            self.ua.login(username, password, vc)
        except Exception as e:
            pass

        x = self.ua.x()
