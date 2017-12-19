from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask

LOGIN_URL='http://wsbs.njhrss.gov.cn/NJLD/'
class Task(AbsFetchTask):
    task_info = dict(
        city_name="南京",
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
        assert 'other' in params, '请选择登录方式'
        if params["other"] == "1":
            assert 'bh1' in params, '缺少客户号'
            assert 'mm1' in params, '缺少密码'
        elif params["other"] == "3":
            assert 'bh3' in params, '缺少用户名'
            assert 'mm3' in params, '缺少密码'
        # other check
        if params["other"] == "1":
            用户名 = params['bh1']
        elif params["other"] == "3":
            用户名 = params['bh3']
        if params["other"] == "1":
            密码 = params['mm1']
        elif params["other"] == "3":
            密码 = params['mm3']
        if len(密码) < 4:
            raise InvalidParamsError('密码错误')

        if len(用户名) <8:
            raise InvalidParamsError('用户名错误！')

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                if params["other"] == "3":
                    code = "3"
                elif params["other"] == "1":
                    code = "1"
                id_num = params['bh' + code]
                password = params['mm' + code]
                self.result_key = id_num
                # 保存到meta
                self.result_meta['用户名'] = id_num
                self.result_meta['密码'] = password

                raise TaskNotImplementedError('查询服务维护中')
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='other',
                     name='[{"tabName":"社会保障卡号","tabCode":"1","isEnable":"1"},{"tabName":"身份证号","tabCode":"3","isEnable":"1"}]',
                 cls='tab', value=params.get('类型Code', '')),
            dict(key='bh1', name='社会保障卡号', cls='input', tabCode="1", value=params.get('用户名', '')),
            dict(key='mm1', name='密码', cls='input:password', tabCode="1", value=params.get('密码', '')),
            dict(key='bh3', name='身份证号', cls='input', tabCode="3", value=params.get('用户名', '')),
            dict(key='mm3', name='密码', cls='input:password', tabCode="3", value=params.get('密码', '')),
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
