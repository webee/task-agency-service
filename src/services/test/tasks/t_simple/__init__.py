import time
from services.test.mock_site import TestSite
from services.test.mock import UserAgent, LogRequestFilter
from services.service import AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError
from services.errors import InvalidParamsError

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
        result.setdefault('identity', {})

    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_x, self._unit_login)

    def _update_session_data(self):
        super()._update_session_data()
        self.state['session'] = self.ua.session

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert 'username' in params, '缺少用户名'
        assert 'password' in params, '缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check

    def _unit_login(self, params=None):
        err_msg = None
        if params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                username = params['username']
                password = params['password']
                vc = params['vc']
                self.ua.login(username, password,vc)

                self.result['key'] = username
                self.result['meta'] = {
                    'username': username,
                    'password': password
                }
                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='username', name='用户名', cls='input'),
            dict(key='password', name='密码', cls='input:password'),
            dict(key='vc', name='验证码', cls='data', query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch_x(self):
        try:
            # 设置data
            data = self.result['data']
            data['x'] = self.ua.x()

            # 设置identity
            identity: dict = self.result['identity']
            identity.update({
                'task_name': '测试simple',
                'target_name': self.result['meta']['username'],
                'target_id': self.result['meta']['username'],
                'status': '正常',
            })

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        return dict(cls="data", content=self.ua.get_vc())


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()
