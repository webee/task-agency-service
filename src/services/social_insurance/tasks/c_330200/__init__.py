import time
import requests
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError


MAIN_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/index.jsp'
LOGIN_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/rzxt/nbhrssLogin.action'
VC_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/comm/yzm.jsp?r='
CHECK_VC_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/comm/checkYzm.jsp'


class Task(AbsTaskUnitSessionTask):

   def _update_session_data(self):
       super()._update_session_data()
       self.state["cookies"] = self.s.cookies

   def _query(self, params: dict):
       t = params.get("t")
       if t == "vc":
           return self._new_vc()

   def _prepare(self):
       state: dict = self.state
       self.s = requests.Session()
       cookie = state.get('cookies')
       if cookie:
           self.s.cookies = cookie
       self.s.headers.update({
           'Accept-Encoding': 'gzip, deflate, sdch, br',
           'Accept-Language': 'zh-CN,zh;q=0.8',
           'Cache-Control': 'max-age=0',
           'Connection': 'keep-alive',
           'Host': 'rzxt.nbhrss.gov.cn',
           'Upgrade-Insecure-Requests': '1',
           'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36'
       })
       result: dict = self.result
       result.setdefault('meta', {})
       result.setdefault('data', {})

   def _setup_task_units(self):
       self._add_unit(self._unit_vo)

   def _check_vo_params(self, params):
       assert params is not None, '缺少参数'
       assert 'yzm' in params, '缺少验证码'

   def _unit_vo(self, params = None):
       err_msg = None
       if not self.is_start or params:
           try:
               self._check_vo_params(params=params)
               yzm = params["yzm"]
               resp = self.s.post(CHECK_VC_URL, data={
                   'yzm' : yzm,
                   'client' : 'NBHRSS_WEB'
               })
               data = resp.json()
           except Exception as e:
               err_msg = str(e)

       vc = self._new_vc()
       raise AskForParamsError({
           dict(key='yzm', name='验证码', cls='data:image', data = vc, quit = {'t' : 'yzm'}),
       }, err_msg=err_msg)


   def _new_vc(self):
       vc_url = VC_URL + str(int(time.time() * 1000))
       resp = self.s.get(vc_url)
       return dict(content = resp.content, content_type = resp.headers['Content-Type'])


   def _check_login_params(self, params):
       assert params is not None,'缺少参数'
       assert 'id' in params, '缺少社保卡号/社会保障号/身份证号'
       assert 'password' in params, '缺少密码'

   def _unit_login(self, params = None):
       err_msg = None
       if not self.is_start or params:
           try:
               self._check_vo_params(params)

           except:
               pass
       pass

if __name__ == "__main__":
    from services.client import TaskTestClient
    client = TaskTestClient(Task())
    client.run()
