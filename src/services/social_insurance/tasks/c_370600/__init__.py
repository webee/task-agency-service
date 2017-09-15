#烟台社保查询：
#地址：http://ytrsj.gov.cn:8081/hsp/logonDialog_withF.jsp
#账号：370302197811184822
#密码：qq781017
import time
import requests
import random
import json
import io
import base64
from tkinter import Canvas
from PIL import Image
from tkinter import Tk
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError


MAIN_URL = 'http://ytrsj.gov.cn:8081/hsp/mainFrame.jsp?&__usersession_uuid=USERSESSION_e78066c6_ba4e_44a1_99e2_803f9e1fcebf&_width=960&_height=769'
LOGIN_URL = 'http://ytrsj.gov.cn:8081/hsp/logon.do'
VC_URL = 'http://ytrsj.gov.cn:8081/hsp/genAuthCode?_='


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
        assert 'password' in params, '缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check

    def _unit_login(self, params=None):
        err_msg = None
        randoms=random.random()
        vc = self._new_vc()
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params['id_num']
                password = params['password']
                vc = params['vc']

                xmlstr='< ?xml version = "1.0" encoding = "UTF-8"? > < p > < s tempmm = "'+password+'" / > < / p >'
                resp = self.s.post(LOGIN_URL, data=dict(
                    method='writeMM2Temp',
                    _xmlString=xmlstr,
                    _random=randoms
                ),header={'Content-Type':'application/x-www-form-urlencoded;charset=UTF-8','X-Requested-With':'XMLHttpRequest'})
                soup = BeautifulSoup(resp.content, 'html.parser')

                xmlstr = '< ?xml version = "1.0" encoding = "UTF-8"? > < p > < s userid = "'+id_num+'" / > < usermm = "'+password+'" / > < s authcode = "5" / > < s yxzjlx = "A" / > < s appversion = "1.0.63" / > < s dlfs = "" / > < / p >'
                resp = self.s.post(LOGIN_URL, data=dict(
                    method='doLogon',
                    _xmlString=xmlstr,
                    _random=randoms
                ), header={'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                           'X-Requested-With': 'XMLHttpRequest'})
                soup = BeautifulSoup(resp.content, 'html.parser')
                errormsg = soup.text
                if errormsg:
                    raise Exception(errormsg)

                self.result['key'] = '%s.%s' % ('real', id_num)
                self.result['meta'] = {
                    'task': 'real',
                    'id_num': id_num,
                    'password': password
                }
                return
            except Exception as e:
                err_msg = str(e)


        raise AskForParamsError([
            dict(key='id_num', name='身份证号', cls='input'),
            dict(key='password', name='密码', cls='input'),
            dict(key='vc', name='验证码', cls='data:image', data=vc, query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch_name(self):
        try:
            data = self.result['data']
            resp = self.s.get(MAIN_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            name = soup.select('#name')[0]['value']
            data['name'] = name

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        randoms=random.random()
        vc_url = VC_URL +str(randoms) #str(int(time.time() * 1000))
        resp = self.s.post(vc_url,data=dict(_=randoms))
        soup = BeautifulSoup(resp.content, 'html.parser')
        jsons = soup.text
        jsonread = json.loads(jsons)
        root = Tk()
        # 创建一个Canvas，设置其背景色为白色
        cv = Canvas(root, bg='white', width=500, height=650)
        rt = cv.create_rectangle(10, 10, 110, 110, outline='red', stipple='gray12', fill='green')
        i=0
        for k, v in jsonread.items():
            #Image.open(io.BytesIO(base64.b64decode(v))).show()
            im = Image.open(io.BytesIO(base64.b64decode(v)))
            cv.create_image((20 * i, 200 * i), image=im)
            i=i+1
        cv.pack()
        root.mainloop()


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()
