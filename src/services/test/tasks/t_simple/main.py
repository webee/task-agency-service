from services.test.mock_site import TestSite
from services.test.mock import UserAgent, LogRequestFilter
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError


test_site = TestSite()


class Task(AbsTaskUnitSessionTask):
    X_PARAM_REQUIREMENTS = {
    }

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
        self._add_unit(self._login)
        self._add_unit(self._fetch_x, self._login)

    def _update_session_data(self):
        super()._update_session_data()
        self.session_data.state['session'] = self.ua.session

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    def _login(self, params=None):
        err_msg = None
        if 'username' in params and 'password' in params and 'vc' in params:
            username = params['username']
            password = params['password']
            vc = params['vc']
            try:
                self.ua.login(username, password, vc)
                return
            except Exception as e:
                err_msg = str(e)
        vc = self._new_vc()
        raise AskForParamsError([
            dict(key='username', name='用户名', schema=None),
            dict(key='password', name='密码', schema=None),
            dict(key='vc', name='验证码', data=vc, query={'t': 'vc'}, schema=None),
        ], err_msg)

    def _fetch_x(self):
        try:
            data = self.result['data']
            data['x'] = self.ua.x()
            return data
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        return self.ua.get_vc()


if __name__ == '__main__':
    task = Task(SessionData())
    res = task.run()
    while not task.done:
        print(res)
        username = input('username:')
        password = input('password:')
        vc = input('vc:')
        res = task.run(dict(username=username, password=password, vc=vc))
    # check result
    print(task.result)
