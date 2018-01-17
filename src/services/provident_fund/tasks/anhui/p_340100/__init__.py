
from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask


LOGIN_URL='http://117.71.52.54:8888/gjj/login/person_index'

class Task(AbsFetchTask):
    task_info = dict(
        city_name="合肥",
        help="""
        """,

        developers=[{'name':'程菲菲','email':'feifei_cheng@chinahrs.net'}]
    )

    def _prepare(self):
        """恢复状态，初始化结果"""
        super()._prepare()
        # state
        # state: dict = self.state
        # TODO: restore from state

    def _update_session_data(self):
        """保存任务状态"""
        super()._update_session_data()
        # state
        # state: dict = self.state
        # TODO: update state

    def _get_common_headers(self):
        return {}

    def _query(self, params: dict):
        """任务状态查询"""
        pass

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '身份证号' in params, '缺少身份证号'
        assert '登录密码' in params, '缺少登录密码'

        # other check
        身份证号 = params['身份证号']
        登录密码 = params['登录密码']

        if len(身份证号) <9 or len(身份证号)>19:
            raise InvalidParamsError('身份证号或个人公积金帐号或黄山卡号错误')
        if len(登录密码) < 6:
            raise InvalidParamsError('登录密码错误')


    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                self.result_key = params.get('身份证号')

                # 保存到meta
                self.result_meta['身份证号'] = params.get('身份证号')
                self.result_meta['登录密码'] = params.get('登录密码')

                raise TaskNotImplementedError('查询服务维护中')

            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input', placeholder='个人公积金帐号/身份证号/黄山卡号', value=params.get('身份证号', '')),
            dict(key='登录密码', name='登录密码', cls='input:password', value=params.get('登录密码', '')),
            #dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)


    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient
    client = TaskTestClient(Task(SessionData()))
    client.run()
