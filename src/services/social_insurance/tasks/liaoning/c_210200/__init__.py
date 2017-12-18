from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask

LOGIN_URL='http://bsdt.dl12333.gov.cn/personal.jsp'
class Task(AbsFetchTask):
    task_info = dict(
        city_name="大连",
        help="""""",
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
        assert '手机号码' in params,'缺少手机号码'
        assert '个人编号' in params, '缺少个人编号'
        assert '密码' in params, '缺少密码'
        # other check
        手机号码=params['手机号码']
        个人编号 = params['个人编号']
        密码 = params['密码']
        if len(密码) < 4:
            raise InvalidParamsError('密码错误')

        if len(个人编号) !=8:
            raise InvalidParamsError('请输入8位个人编号！')

        if len(手机号码) !=11:
            raise InvalidParamsError('请输入正确手机号！')

        raise InvalidParamsError('个人编号或手机号或密码错误')

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)

                self.result_key = params.get('个人编号')
                # 保存到meta
                self.result_meta['个人编号'] = params.get('个人编号')
                self.result_meta['手机号码'] = params.get('手机号码')
                self.result_meta['密码'] = params.get('密码')

                raise TaskNotImplementedError('查询服务维护中')
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='个人编号', name='个人编号',placeholder='个人编号', cls='input', value=params.get('个人编号', '')),
            dict(key='手机号码', name='手机号码', cls='input', value=params.get('手机号码', '')),
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
