# cff---河北石家庄--社保账号采集

import time
import requests
import json
from bs4 import BeautifulSoup

from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError, InvalidConditionError, \
    PreconditionNotSatisfiedError
from services.commons import AbsFetchTask


LoginUrl="http://grsbcx.sjz12333.gov.cn/login.do?method=begin"
VC_URL="http://grsbcx.sjz12333.gov.cn/jcaptcha"
Main_URL="http://grsbcx.sjz12333.gov.cn/ria_grid.do?method=query"


class Task(AbsFetchTask):
    task_info = dict(
        city_name="石家庄",
        help="""
            <li>1.社会保障号为公民身份证号码</li>
            <li>2.请您使用社会保障卡服务密码或医保卡密码进行查询</li>
            """,

        developers=[{'name': '程菲菲', 'email': 'feifei_cheng@chinahrs.net'}]
    )

    def _get_common_headers(self):
        return {
            'User-Agent':'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.79 Safari/537.36',
            'Accept-Encoding':'gzip, deflate',
            'Host':'grsbcx.sjz12333.gov.cn',
            'Connection':'keep-alive',
            'Upgrade-Insecure-Requests':'1'
        }


    def _new_vc(self):
        resp = self.s.get(VC_URL)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])

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
        assert '社保号' in params, '缺少社保号'
        assert '密码' in params, '缺少密码'
        # other check
        证件号 = params['社保号']
        密码 = params['密码']

        if len(证件号) == 0:
            raise InvalidParamsError('社保号为空，请输入社保号！')
        elif len(证件号)!=15 and len(证件号)!=18:
            raise InvalidParamsError('社保号不正确，请重新输入！')

        if len(密码) == 0:
            raise InvalidParamsError('密码为空，请输入密码！')
        elif len(密码) < 6:
            raise InvalidParamsError('密码不正确，请重新输入！')

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '社保号' not in params:
                params['社保号'] = meta.get('社保号')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '社保号' and '社保号' in meta:
                continue
            elif pr['key'] == '密码' and '密码' in meta:
                continue
            res.append(pr)
        return res


    def _unit_login(self, params=None):
        err_msg = None
        if params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params.get("社保号")
                account_pass = params.get("密码")
                vc = params.get("vc")

                data = {
                    'Method':'P',
                    'pid':'1373174326875',  #  str(time.time()*1000)[0:13]
                    'j_username': id_num,
                    'j_password': account_pass,
                    'jcaptcha_response': vc
                }
                resp = self.s.post("http://grsbcx.sjz12333.gov.cn/j_unieap_security_check.do", data=data)

                if(resp.url!='http://grsbcx.sjz12333.gov.cn/enterapp.do?method=begin&name=/si&welcome=/si/pages/index.jsp'):
                    raise InvalidParamsError("登录失败，请重新登录！")
                else:
                    self.result_key = id_num
                    self.result_meta['社保号'] =id_num
                    self.result_meta['密码']=account_pass
                    return
                #raise TaskNotImplementedError('查询服务维护中')

            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='社保号', name='社保号', cls='input',value=params.get('社保号', '')),
            dict(key='密码', name='密码', cls='input:password',value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)


    def _unit_fetch(self):
        try:
            ds=self.s.get("http://grsbcx.sjz12333.gov.cn/si/pages/zindex/default.html")
            re=self.s.get("http://grsbcx.sjz12333.gov.cn/si/pages/innerindex.jsp")
            ress=self.s.get("http://grsbcx.sjz12333.gov.cn/si/pages/menu/Page.jsp")
            res=self.s.get("http://grsbcx.sjz12333.gov.cn/si/pages/default.jsp")
            resp=self.s.post(Main_URL)
            soup=BeautifulSoup(resp.content,'html.parser').findAll('body')

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task(SessionData()))
    client.run()

    # 130105198609142416   777129
