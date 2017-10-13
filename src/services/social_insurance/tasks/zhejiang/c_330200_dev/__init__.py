
import time
import random
import json,requests
from PIL import Image
import io
import datetime
from services.webdriver import new_driver, DriverRequestsCoordinator,DriverType
from bs4 import BeautifulSoup
from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class value_is_number(object):
    """判断元素value是数字"""
    def __init__(self, locator):
        self.locator = locator

    def __call__(self, driver):
        element = driver.find_element(*self.locator)
        val = element.get_attribute('value')
        return val and val.isnumeric()

USER_AGENT = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0"

MAIN_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/index.jsp'
INFO_URL='https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/query/query-grxx.jsp'
VC_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/comm/yzm.jsp?r='
YL_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/query/query-ylbx.jsp'
YIL_URL='https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/query/query-yilbx.jsp'

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

   def _prepare(self, data=None):
        super()._prepare(data)
        self.dsc = DriverRequestsCoordinator(s=self.s, create_driver=self._create_driver)

   def _create_driver(self):
        driver = new_driver(user_agent=USER_AGENT,js_re_ignore='/web\/ImageCheck.jpg/g')
        driver.get(MAIN_URL)
        return driver

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

   def _unit_login(self, params:dict):
       err_msg = None
       if params:
           try:
               self._check_login_params(params)
               id_num = params['身份证号']
               pwd = params['密码']
               yzm = params['vc']
               self._do_login(id_num, pwd, yzm)

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
           dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
           dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}, value=params.get('vc', '')),
       ], err_msg)

   def _do_login(self, username, password, vc):
        """使用web driver模拟登录过程"""
        with self.dsc.get_driver_ctx() as driver:
            # 打开登录页
            driver.get(MAIN_URL)

            username_input = driver.find_element_by_xpath('//*[@id="loginid"]')
            password_input = driver.find_element_by_xpath('//*[@id="pwd"]')
            vc_input = driver.find_element_by_xpath('//*[@id="yzm"]')
            submit_btn = driver.find_element_by_xpath('//*[@id="btnLogin"]')

            # 用户名
            username_input.clear()
            username_input.send_keys(username)

            # 密码
            password_input.clear()
            password_input.send_keys(password)
            vc_input.clear()
            vc_input.send_keys(vc)
            # 提交
            submit_btn.click()
            time.sleep(3)
            #Image.open(io.BytesIO(driver.get_screenshot_as_png())).show()
            if driver.current_url == INFO_URL:
                print('登录成功')
                # 保存登录后的页面内容供抓取单元解析使用
                login_page_html = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
                self.s.soup = BeautifulSoup(login_page_html, 'html.parser')


                #realname=soup.select('#xm')[0].text
            else:
                # FIXME: 尝试处理alert
                err_msg = '登录失败，请检查输入'
                alert = driver.switch_to.alert
                try:
                    err_msg = alert.text
                    # alert.accept()
                finally:
                    raise InvalidParamsError(err_msg)
   def _yanglao(self):
       with self.dsc.get_driver_ctx() as driver:
           driver.get(YL_URL)
           time.sleep(2)
           htmls = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
           soupyl = BeautifulSoup(htmls, 'html.parser')
           mingxitable = soupyl.select('#content')
           tableinfo = mingxitable[0].find_all('tr')
           self.result_data['old_age'] = {}
           self.result_data['old_age']['data'] = {}
           arrstr=[]
           years = ''
           months = ''
           for row in tableinfo:
               arr = []
               cell = [i.text for i in row.find_all('td')]
               if len(cell)<3:
                   arrstr.extend(cell)
               elif len(cell)==4:
                   yearmonth =cell[0]
                   if years == '' or years != yearmonth[:4]:
                       years = yearmonth[:4]
                       self.result_data['old_age']['data'][years] = {}
                       if len(months) > 0:
                           if months == yearmonth[-2:]:
                               self.result_data['old_age']['data'][years][months] = {}
                   if months == '' or months != yearmonth[-2:]:
                       months = yearmonth[-2:]
                       self.result_data['old_age']['data'][years][months] = {}
                   dicts={
                       '缴费时间':cell[0],
                       '缴费类型': '',
                       '缴费基数': cell[1],
                       '公司缴费': '',
                       '个人缴费': cell[2],
                       '缴费单位': '',
                       '到账情况': cell[3]
                   }
                   arr.append(dicts)
                   self.result_data['old_age']['data'][years][months] = arr
           print(arrstr)
   def _yiliao(self):
       with self.dsc.get_driver_ctx() as driver:
           driver.get(YIL_URL)
           time.sleep(2)
           htmls = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
           soupyl = BeautifulSoup(htmls, 'html.parser')
           mingxitable = soupyl.select('#content')
           tableinfo = mingxitable[0].find_all('tr')
           self.result_data['medical_care'] = {}
           self.result_data['medical_care']['data'] = {}
           arrstr=[]
           years = ''
           months = ''
           for row in tableinfo:
               arr = []
               cell = [i.text for i in row.find_all('td')]
               if len(cell)<3:
                   arrstr.extend(cell)
               elif len(cell)==4:
                   yearmonth =cell[0]
                   if years == '' or years != yearmonth[:4]:
                       years = yearmonth[:4]
                       self.result_data['medical_care']['data'][years] = {}
                       if len(months) > 0:
                           if months == yearmonth[-2:]:
                               self.result_data['medical_care']['data'][years][months] = {}
                   if months == '' or months != yearmonth[-2:]:
                       months = yearmonth[-2:]
                       self.result_data['medical_care']['data'][years][months] = {}
                   dicts={
                       '缴费时间':cell[0],
                       '缴费类型': '',
                       '缴费基数': cell[1],
                       '公司缴费': '',
                       '个人缴费': cell[2],
                       '缴费单位': '',
                       '到账情况': cell[3]
                   }
                   arr.append(dicts)
                   self.result_data['medical_care']['data'][years][months] = arr
           print(arrstr)

   def _unit_fetch_name(self):
       """用户信息"""
       try:
           soup= self.s.soup
           self.result_data["baseInfo"] = {
               '城市名称': '宁波',
               '城市编号': '330200',
               '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
               '姓名':soup.select('#xm')[0].text,
               '性别': soup.select('#xb')[0].text,
               '身份证号': soup.select('#sfz')[0].text,
               '国籍': soup.select('#gj')[0].text,
               '社保卡号码': soup.select('#sbkh')[0].text,
               '社保卡状态': soup.select('#kzt')[0].text,
               '银行卡号码': soup.select('#yhkh')[0].text,
               '发卡日期': soup.select('#fkrq')[0].text,
               '手机号码': soup.select('#sjhm')[0].text,
               '固定号码': soup.select('#gddh')[0].text,
               '常住地址': soup.select('#czdz')[0].text,
               '邮政编码': soup.select('#yzbm')[0].text
           }
           self.result_identity['target_name'] = soup.select('#xm')[0].text
           #self.result_data["baseInfo"].setdefault()

           self._yanglao()
           self._yiliao()


           #resp=self.s.get(YL_URL)

           #token=resp.request._cookies['__rz__k']
           #datas=json.dumps({'api':'91S001','AAB301':'aab301'})
           #r=requests.post('https://app.nbhrss.gov.cn/nbykt/rest/commapi',datas,token)
           #print(r.json())






           return
       except PermissionError as e:
           raise PreconditionNotSatisfiedError(e)

   def _new_vc(self):
       vc_url = VC_URL + time.strftime('%a %b %d %Y %H:%M:%S', time.localtime())
       resp = self.s.get(vc_url)
       return dict(cls='data:image', content=resp.content, content_type=resp.headers.get('Content-Type'))

if __name__ == "__main__":
    from services.client import TaskTestClient
    meta = {'身份证号': '330227198906162713', '密码': '362415'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()
