from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask


class Task(AbsFetchTask):
    task_info = dict(
        city_name="广州",
        help="""<li></li>"""
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
        assert '证件号' in params, '缺少证件号'
        assert '姓名' in params, '姓名'
        assert '密码' in params, '缺少密码'
        # other check
        证件号 = params['证件号']
        姓名 = params['姓名']
        密码 = params['密码']
        if len(密码) < 6:
            raise InvalidParamsError('密码错误')
        if 证件号.isdigit():
            if len(证件号) < 15:
                raise InvalidParamsError('证件号错误')
        if len(姓名) <= 0:
            raise InvalidParamsError('姓名不能为空')
            return
        raise InvalidParamsError('账号或密码错误')

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                self.result_key = params.get('证件号')
                # 保存到meta
                self.result_meta['证件号'] = params.get('证件号')
                self.result_meta['姓名'] = params.get('姓名')
                self.result_meta['密码'] = params.get('密码')

                raise TaskNotImplementedError('查询服务维护中')
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='证件号', name='证件号', cls='input', value=params.get('证件号', '')),
            dict(key='姓名', name='姓名', cls='input', value=params.get('姓名', '')),
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
