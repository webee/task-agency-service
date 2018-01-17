
from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask


LOGIN_URL='http://60.173.202.220/wssb/grlogo.jsp'

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
        assert '姓名' in params, '缺少姓名'
        assert '身份证号' in params, '缺少身份证号'
        assert '密码' in params, '缺少密码'

        # other check
        姓名 = params['姓名']
        身份证号 = params['身份证号']
        密码 = params['密码']

        if len(姓名) <=1:
            raise InvalidParamsError('请输入姓名')
        if len(身份证号) <15 or len(身份证号)>18:
            raise InvalidParamsError('身份证输入有误')
        if len(密码) < 6:
            raise InvalidParamsError('密码输入有误')


    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                self.result_key = params.get('身份证号')

                # 保存到meta
                self.result_meta['姓名'] = params.get('姓名')
                self.result_meta['身份证号'] = params.get('身份证号')
                self.result_meta['密码'] = params.get('密码')

                raise TaskNotImplementedError('查询服务维护中')

            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='姓名', name='姓名', cls='input', value=params.get('姓名', '')),
            dict(key='身份证号', name='身份证号', cls='input', value=params.get('身份证号', '')),
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
