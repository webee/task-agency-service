from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask


class Task(AbsFetchTask):
    task_info = dict(
        city_name="深圳",
        help="""<li>如您首次在网上查询您的公积金账户，初始密码为身份证后六位，身份证号码有字母的用数字“0”代替。</li>
                <li>如您在公积金官网查询过您的公积金账户，请输入账户信息和密码登录即可。</li>"""
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
        assert '公积金账号' in params, '缺少公积金账号'
        assert '密码' in params, '缺少密码'
        # other check
        公积金账号 = params['公积金账号']
        密码 = params['密码']
        if len(密码) < 6:
            raise InvalidParamsError('公积金账号或密码错误')
        if 公积金账号.isdigit():
            if len(公积金账号) !=11:
                raise InvalidParamsError('个人公积金账号位数不正确!')
            return
        if '@' in 公积金账号:
            if not 公积金账号.endswith('@hz.cn'):
                raise InvalidParamsError('市民邮箱错误')
            return
        raise InvalidParamsError('公积金账号或密码错误')

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                self.result_key = params.get('公积金账号')
                # 保存到meta
                self.result_meta['公积金账号'] = params.get('公积金账号')
                self.result_meta['密码'] = params.get('密码')

                raise TaskNotImplementedError('查询服务维护中')
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='公积金账号', name='公积金账号', cls='input', placeholder='公积金账号', value=params.get('公积金账号', '')),
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
