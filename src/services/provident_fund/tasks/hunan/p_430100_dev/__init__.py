# cff---长沙--湖南省省会   公积金信息

import time
import requests
from bs4 import BeautifulSoup
import re

from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError, InvalidConditionError, \
    PreconditionNotSatisfiedError
from services.commons import AbsFetchTask

MAIN_URL = r''
LOGIN_URL = r"http://www.csgjj.com.cn:8001/login.do"
VC_URL=r"http://www.csgjj.com.cn:8001/CaptchaImg"


class Task(AbsFetchTask):
    task_info = dict(
        city_name="长沙",
        help="""
            <li>您可以登录中心新网厅个人版重新注册，也可以通过手机APP或微信公众号重新注册</li>
            <li>为保证信息安全，注册时需验证您在中心预留的手机号码，如果您没有预留或需要更改预留手机号码，可以通过本单位住房公积金专管员所使用的网厅单位版实时申报，也可以携带本人身份证原件到各管理部柜台申报</li>
            """,

        developers=[{'name': '程菲菲', 'email': 'feifei_cheng@chinahrs.net'}]
    )

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.79 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.csgjj.com.cn:8001',
        }


    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '身份证号' in params, '缺少身份证号'
        assert '账户名' in params, '缺少账户名'
        assert '密码' in params, '缺少密码'
        # other check
        身份证号 = params['身份证号']
        账户名 = params['账户名']
        密码 = params['密码']

        if len(身份证号) == 0:
            raise InvalidParamsError('身份证号为空，请输入身份证号')
        elif len(身份证号) < 15:
            raise InvalidParamsError('身份证号不正确，请重新输入')

        if len(账户名) == 0:
            raise InvalidParamsError('账户名为空，请输入账户名')

        if len(密码) == 0:
            raise InvalidParamsError('密码为空，请输入密码！')
        elif len(密码) < 6:
            raise InvalidParamsError('密码不正确，请重新输入！')

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '身份证号' not in params:
                params['身份证号'] = meta.get('身份证号')
            if '账户名' not in params:
                params['账户名'] = meta.get('账户名')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '身份证号' and '身份证号' in meta:
                continue
            elif pr['key'] == '账户名' and '账户名' in meta:
                continue
            elif pr['key'] == '密码' and '密码' in meta:
                continue
            res.append(pr)
        return res


    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)

                id_num = params.get("身份证号")
                account_name = params.get("账户名")
                account_pass = params.get("密码")

                self.result_key = id_num
                self.result_meta['身份证号'] =id_num
                self.result_meta['账户名'] = account_name
                self.result_meta['密码']=account_pass

                raise TaskNotImplementedError('查询服务维护中')

            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input', placeholder='身份证号/手机号码/个人账号', value=params.get('身份证号', '')),
            dict(key='账户名', name='账户名', cls='input', value=params.get('账户名', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
        ], err_msg)

    def _unit_fetch(self):
        try:

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        return True


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task(SessionData()))
    client.run()

