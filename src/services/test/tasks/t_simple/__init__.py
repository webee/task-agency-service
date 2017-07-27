import time
from services.test.mock_site import TestSite
from services.test.mock import UserAgent, LogRequestFilter
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError


test_site = TestSite()


class Task(AbsTaskUnitSessionTask):
    # noinspection PyAttributeOutsideInit
    def _prepare(self):
        state: dict = self.state
        self.ua = UserAgent(test_site, state.get('session'))
        self.ua.register_request_filter(LogRequestFilter())

        # result
        result: dict = self.result
        result.setdefault('meta', {})
        result.setdefault('data', {})

    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_x, self._unit_login)

    def _update_session_data(self):
        super()._update_session_data()
        self.session_data.state['session'] = self.ua.session

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert 'username' in params, '用户名不能为空'
        assert 'password' in params, '密码不能为空'
        assert 'vc' in params, '验证码不能为空'
        # other check

    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                username = params['username']
                password = params['password']
                vc = params['vc']
                self.ua.login(username, password, vc)

                self.result['key'] = 'simple.a'
                self.result['meta'] = {
                    'task': 'simple',
                    'username': username,
                    'password': password,
                    'updated': time.time()
                }
                return
            except Exception as e:
                err_msg = str(e)

        vc = self._new_vc()
        raise AskForParamsError([
            dict(key='username', name='用户名', cls='input'),
            dict(key='password', name='密码', cls='input'),
            dict(key='vc', name='验证码', cls='data', data=vc, query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch_x(self):
        try:
            data = self.result['data']
            data['x'] = self.ua.x()
            return self.result
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        return self.ua.get_vc()


if __name__ == '__main__':
    from services.client import TestClient
    client = TestClient(Task(SessionData()))
    client.run()
