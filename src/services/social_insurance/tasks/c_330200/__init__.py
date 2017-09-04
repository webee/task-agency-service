#宁波市人力资源和社会保障局   登录成功  内容截取都是空  js封装比较复杂（以后再做）
from  datetime  import  *
import time
import re
import requests
from urllib import parse
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError

MAIN_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/query/query-grxx.jsp'
LOGIN_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/rzxt/nbhrssLogin.action'
VCChECK_URl='https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/comm/checkYzm.jsp'
VC_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/comm/yzm.jsp?r='

class Task(AbsTaskUnitSessionTask):
    # noinspection PyAttributeOutsideInit
    def _prepare(self):
        state: dict = self.state
        self.s = requests.Session()
        cookies = state.get('cookies')
        if cookies:
            self.s.cookies = cookies
        self.s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36'
        })

        # result
        result: dict = self.result
        result.setdefault('meta', {})
        result.setdefault('data', {})
        result.setdefault('identity',{})

    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_name, self._unit_login)

    def _update_session_data(self):
        super()._update_session_data()
        self.state['cookies'] = self.s.cookies

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert 'id_num' in params, '缺少身份证号'
        #assert 'account_num' in params, '缺少职工姓名'
        assert 'password' in params,'缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check

    def _unit_login(self, params=None):
        err_msg = None
        params
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params['id_num']
                #account_num = params['account_num']
                password=params['password']
                vc = params['vc']
                resp=self.s.post(VCChECK_URl,data=dict(
                    yzm=vc,
                    client='NBHRSS_WEB'))
                soup = BeautifulSoup(resp.content, 'html.parser')
                if soup.text.__contains__('1'):
                    raise Exception('验证码错误')

                resp = self.s.post(LOGIN_URL,data = dict(
                    client='NBHRSS_WEB',
                    id=id_num,
                    password=password,
                    phone=''
                ))
                soup = BeautifulSoup(resp.content, 'html.parser')

                if soup.text.find('msg')>0:
                    return_message=soup.text.split(':')[1].split(',')[0]
                    raise Exception(return_message)
                else:
                    print("登录成功！")

                self.result['key'] = '%s.%s' % ('real', id_num)
                self.result['meta'] = {
                    'task': 'real',
                    'id_num': id_num
                }
                return
            except Exception as e:
                err_msg = str(e)

        vc = self._new_vc()
        raise AskForParamsError([
            dict(key='id_num', name='社保卡号/社会保障号/身份证号', cls='input'),
            #dict(key='account_num', name='职工姓名', cls='input'),
            dict(key='password',name='密码',cls='input'),
            dict(key='vc', name='验证码', cls='data:image', data=vc, query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch_name(self):
        try:
            data = self.result['data']
            resp = self.s.get(MAIN_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')

            name = soup.select('#xm')[0]['value']
            data['name'] = name

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        vc_url = VC_URL + datetime.now().strftime('%a %b %d %Y %H:%M:%S')
        resp = self.s.get(vc_url)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()
