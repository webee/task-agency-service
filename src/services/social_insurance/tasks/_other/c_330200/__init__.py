import time
import requests
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError
from services.commons import AbsFetchTask

MAIN_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/index.jsp'
LOGIN_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/rzxt/nbhrssLogin.action'
INFO_URL='https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/query/query-grxx.jsp'
VC_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/comm/yzm.jsp?r='
CHECK_VC_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/comm/checkYzm.jsp'


class Task(AbsFetchTask):
   task_info = dict(
        city_name="宁波",
        help="""<li>如您未在社保网站查询过您的社保信息，请到宁波社保网上服务平台完成“注册”然后再登录。</li>
            <li>如有问题请拨打12333。</li>
            """
    )
   def _get_common_headers(self):
        return { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36'}

   def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_name, self._unit_login)

   def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

   def _check_login_params(self, params):
       assert params is not None, '缺少参数'
       assert '身份证号' in params, '缺少身份证号'
       assert '密码' in params, '缺少密码'
       # other check

   def _params_handler(self, params: dict):
       if not (self.is_start and not params):
           meta = self.prepared_meta
           if '身份证号' not in params:
               params['身份证号'] = meta.get('身份证号')
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
           elif pr['key'] == '密码' and '密码' in meta:
               continue
           elif pr['key'] == 'other':
               continue
           res.append(pr)
       return res

   def _unit_login(self, params = None):
       err_msg = None
       if not self.is_start or params:
           try:
               self._check_login_params(params=params)
               id_num = params['身份证号']
               pwd = params['密码']
               yzm = params["yzm"]
               resp = self.s.post(CHECK_VC_URL, data={
                   'yzm' : yzm,
                   'client' : 'NBHRSS_WEB'
               })
               soup = BeautifulSoup(resp.content, 'html.parser')
               resp = self.s.post(LOGIN_URL, data={
                   'id': id_num,
                   'password': pwd,
                   'phone': '',
                   'client': 'NBHRSS_WEB'
               })
               soup = BeautifulSoup(resp.content, 'html.parser')

               self.result_key = id_num
               self.result_meta['身份证号'] = id_num
               self.result_meta['密码'] = pwd
               self.result_identity['task_name'] = '宁波'
               self.result_identity['target_id'] = id_num

               return

           except Exception as e:
                err_msg = str(e)
       raise AskForParamsError([
           dict(key='身份证号', name='身份证号', cls='input', value=params.get('身份证号', '')),
           dict(key='密码', name='密码', cls='input:password', value=params.get('密码', ''))
       ], err_msg)

   def _new_vc(self):
       vc_url = VC_URL + str(int(time.time() * 1000))
       resp = self.s.get(vc_url)
       return dict(content = resp.content, content_type = resp.headers['Content-Type'])


if __name__ == "__main__":
    from services.client import TaskTestClient
    client = TaskTestClient(Task())
    client.run()
