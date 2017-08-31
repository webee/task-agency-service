from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskAbortedError
from services.commons import AbsFetchTask


class Task(AbsFetchTask):
    task_info = dict(
        city_name="杭州",
        help="首次申请密码或遗忘网上登陆密码，本人须携带有效身份证件至就近街道社区事务受理中心或就近社保分中心自助机具上申请办理"
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
        pass

    def _query(self, params: dict):
        """任务状态查询"""
        pass

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '用户名' in params, '缺少用户名'
        assert '密码' in params, '缺少密码'
        # other check

    def _unit_login(self, params=None):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                raise TaskAbortedError('查询服务维护中')
            except Exception as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='用户名', name='用户名', cls='input', placeholder='身份证号或者邮箱'),
            dict(key='密码', name='密码', cls='input:password'),
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
