from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask


class Task(AbsFetchTask):
    task_info = dict(
        city_name="成都",
        help="""<li>联名卡有两个密码，一个是银行查询密码，一个是公积金查询服务密码。</li>
        <li>如若查询服务密码，可拨打服务热线12329修改。</li>""",
        developers=[{'name':'卜圆圆','email':'byy@qinqinxiaobao.com'}]
    )
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
        assert '账号' in params, '缺少账号'
        assert '密码' in params, '缺少密码'
        # other check
        账号 = params['账号']
        密码 = params['密码']
        if len(密码) < 4:
            raise InvalidParamsError('账号或密码错误')
        if 账号.isdigit():
            if len(账号) < 5:
                raise InvalidParamsError('身份证错误')
            return
        raise InvalidParamsError('账号或密码错误')

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                self.result_key = params.get('账号')
                # 保存到meta
                self.result_meta['账号'] = params.get('账号')
                self.result_meta['密码'] = params.get('密码')

                raise TaskNotImplementedError('查询服务维护中')
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='账号', name='账号', cls='input', placeholder='账号', value=params.get('账号', '')),
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

    meta = {'账号': '6222108326064250','密码': '786042'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()
#联名卡登录 ：[{'账号': '6222803811824115177', '密码': '117173'}] [{'账号': '6222108326064250', '密码': '786042'}]

