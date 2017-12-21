from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask

LOGIN_URL='http://www.fsgjj.gov.cn/webapply/login.do?fromFlag=wwgr'
class Task(AbsFetchTask):
    task_info = dict(
        city_name="佛山",

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
        assert '用户名' in params, '缺少证件号码'
        assert '个人账号' in params, '个人账号'
        # other check
        证件号码 = params['证件号码']
        个人账号 = params['个人账号']
        if len(个人账号) !=8:
            raise InvalidParamsError('个人账号')
        if len(证件号码) < 15:
            raise InvalidParamsError('证件号码错误')


    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                self.result_key = params.get('用户名')
                # 保存到meta
                self.result_meta['证件号码'] = params.get('证件号码')
                self.result_meta['个人账号'] = params.get('个人账号')

                raise TaskNotImplementedError('查询服务维护中')
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='证件号码', name='证件号码', cls='input', placeholder='证件号码（以单位申报为准）', value=params.get('证件号码', '')),
            dict(key='个人账号', name='个人账号', cls='input',placeholder='对帐簿或原存折帐号后8位', value=params.get('个人账号', '')),
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


