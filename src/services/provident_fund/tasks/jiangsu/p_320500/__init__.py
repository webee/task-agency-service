from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask


class Task(AbsFetchTask):
    task_info = dict(
        city_name="苏州",
        help="""<li>有未还清的公积金贷款的用户可以使用代扣还款银行卡(折)帐号登录；</li>
        <li>身份证号码如包含x，录入时不区分大小写；</li>
        <li>如果密码控件不可用，说明您的计算机未安装JRE或版本太低，请参照以下内容安装并设置JRE：
        1)如果浏览器没有自动下载,请点击[下载]手动安装
        2)安装JRE需要数分钟时间,请耐心等待,安装完成后请刷新登录页面</li>
        """,
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
            dict(key='登陆名', name='登陆名', cls='input', placeholder='用户名或者公积金账号或身份证号登录', value=params.get('登陆名', '')),
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


#登陆名：100091745304  密码：592316   登陆名：100095161703   密码：843320