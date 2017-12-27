# cff---江苏无锡--

import time
import requests
import json
from bs4 import BeautifulSoup

from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError, InvalidConditionError, \
    PreconditionNotSatisfiedError
from services.commons import AbsFetchTask


LoginUrl="http://218.90.158.61/index.html"
Post_LoginURL="http://218.90.158.61/personloginvalidate.html"
VC_URL="http://218.90.158.61/captcha.svl"
Main_URL="http://218.90.158.61/person/personBaseInfo.html"


class Task(AbsFetchTask):
    task_info = dict(
        city_name="无锡",
        help="""
            <li>如果您已经注册，请用您的身份证号和密码登录</li>
            """,

        developers=[{'name': '程菲菲', 'email': 'feifei_cheng@chinahrs.net'}]
    )

    def _get_common_headers(self):
        return {
            'User-Agent':'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.79 Safari/537.36',
            'Accept-Encoding':'gzip, deflate',
            'Host':'218.90.158.61',
            'X-Requested-With':'XMLHttpRequest',
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
        assert '身份证' in params, '缺少身份证'
        assert '密码' in params, '缺少密码'
        # other check
        身份证 = params['身份证']
        密码 = params['密码']

        if len(身份证) == 0:
            raise InvalidParamsError('身份证号为空，请输入身份证号！')
        elif len(身份证)!=15 and len(身份证)!=18:
            raise InvalidParamsError('身份证号不正确，请重新输入！')

        if len(密码) == 0:
            raise InvalidParamsError('密码为空，请输入密码！')
        elif len(密码) < 6:
            raise InvalidParamsError('密码不正确，请重新输入！')

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '身份证' not in params:
                params['身份证'] = meta.get('身份证')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '身份证' and '身份证' in meta:
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
                id_num = params.get("身份证")
                account_pass = params.get("密码")
                vc = params.get("vc")

                data = {
                    'account':id_num,
                    'password':account_pass,
                    'type':'1',
                    'captcha': vc
                }
                resp = self.s.post(Post_LoginURL, data=data)

                if('success' not in resp.text):
                    raise InvalidParamsError("登录失败，请重新登录！")
                else:
                    self.result_key = id_num
                    self.result_meta['身份证'] =id_num
                    self.result_meta['密码']=account_pass
                    return

            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='身份证', name='身份证', cls='input',value=params.get('身份证', '')),
            dict(key='密码', name='密码', cls='input:password',value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)


    def _unit_fetch(self):
        try:
            # 基本信息
            resp=self.s.get(Main_URL)
            soup=BeautifulSoup(resp.content,'html.parser').find('div',{'class':'condition_box'}).findAll('li')

            # 五险状态
            wuxres=self.s.get("http://218.90.158.61/person/personCBInfo.html")
            wxsoup=BeautifulSoup(wuxres.content,'html.parser').findAll('dd')
            wuxianType={
                '养老': wxsoup[33].text.replace('\r','').replace('\n',''),
                '医疗': wxsoup[38].text.replace('\r','').replace('\n',''),
                '失业': wxsoup[34].text.replace('\r','').replace('\n',''),
                '工伤': wxsoup[37].text.replace('\r','').replace('\n',''),
                '生育': wxsoup[35].text.replace('\r','').replace('\n',''),
            }
            status=""
            if(wxsoup[33].text.replace('\r','').replace('\n','')=="正常参保"):
                status='正常'
            else:
                status='停缴'

            # 个人基本信息
            self.result_data['baseInfo'] = {
                '姓名': soup[20].text,
                '身份证号': soup[57].text,
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '城市名称': '无锡',
                '城市编号': '320200',
                '缴费时长': 0,
                '最近缴费时间': '',
                '开始缴费时间': '',
                '个人养老累计缴费': 0,
                '个人医疗累计缴费': 0,
                '五险状态': wuxianType,
                '账户状态': status,

                '个人编码':soup[19].text,
                '民族':soup[58].text.replace('\r','').replace('\n',''),
                '出生日期':soup[21].text,
                '性别':soup[22].text.replace('\r','').replace('\n',''),
                '户口性质':soup[60].text.replace('\r','').replace('\n',''),
                '个人状态':soup[24].text.replace('\r','').replace('\n',''),
                '工作日期':soup[27].text,
                '手机号码':soup[75].text,
                '户口所在地':soup[82].text,
                '现居住地址':soup[83].text
            }

            # identity
            self.result['identity'] = {
                "task_name": "无锡",
                "target_name": soup[20].text,
                "target_id": self.result_meta['身份证'],
                "status": status
            }

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task(SessionData()))
    client.run()

    # 610402198001307528   771002
