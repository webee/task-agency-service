from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask


class Task(AbsFetchTask):
    task_info = dict(
        city_name="杭州",
        help="""<li>个人客户号作为办理业务的唯一编号，可通过询问单位经办人或本人携带本人身份证到本中心查询的方式获取。</li>
        <li>在获取到个人客户号后，请到杭州公积金管理中心官网网完成“注册”然后再登录。</li>""",
        developers=[{'name':'卜圆圆','email':'byy@qinqinxiaobao.com'}]
    )

    def _prepare(self):
        """恢复状态，初始化结果"""
        super()._prepare()
        # state
        # state: dict = self.state
        # TODO: restore from state

        # result
        # result: dict = self.result
        # TODO: restore from result

    def _update_session_data(self):
        """保存任务状态"""
        super()._update_session_data()
        # state
        # state: dict = self.state
        # TODO: update state

        # result
        # result: dict = self.result
        # TODO: update temp result

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
        assert '登陆名' in params, '缺少账号'
        assert '密码' in params, '缺少密码'
        # other check
        登陆名 = params['登陆名']
        密码 = params['密码']
        if len(密码) < 4:
            raise InvalidParamsError('登陆名或密码错误')
        if 登陆名.isdigit():
            if len(登陆名) < 5:
                raise InvalidParamsError('登陆名错误')
            return
        if '@' in 登陆名:
            if not 登陆名.endswith('@hz.cn'):
                raise InvalidParamsError('市民邮箱错误')
            return
        raise InvalidParamsError('登陆名或密码错误')

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                self.result_key = params.get('登陆名')
                # 保存到meta
                self.result_meta['登陆名'] = params.get('登陆名')
                self.result_meta['密码'] = params.get('密码')

                raise TaskNotImplementedError('查询服务维护中')
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='登陆名', name='登陆名', cls='input', placeholder='登陆名或者市民邮箱(@hz.cn)', value=params.get('登陆名', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
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
