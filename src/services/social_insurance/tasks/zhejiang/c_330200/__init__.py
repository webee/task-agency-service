import time
import random
import json, requests
from PIL import Image
import io
import datetime
from services.webdriver import new_driver, DriverRequestsCoordinator, DriverType
from bs4 import BeautifulSoup
from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.common.proxy import Proxy
from selenium.webdriver.common.proxy import ProxyType


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
INFO_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/query/query-grxx.jsp'
VC_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/comm/yzm.jsp?r='
YL_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/query/query-ylbx.jsp'
YIL_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/query/query-yilbx.jsp'
GS_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/query/query-gsbx.jsp'
SY_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/query/query-sybx.jsp'
SHY_URL = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/query/query-shybx.jsp'
CVC_URL='https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/comm/checkYzm.jsp'
LOGIN_URL='https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/rzxt/nbhrssLogin.action'


class Task(AbsFetchTask):
    task_info = dict(
        city_name="宁波",
        help="""<li>如您未在社保网站查询过您的社保信息，请到宁波社保网上服务平台完成“注册”然后再登录。</li>
            <li>如有问题请拨打12333。</li>
            """,
        developers=[{'name':'卜圆圆','email':'byy@qinqinxiaobao.com'}]
    )

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36'}

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
        driver = new_driver(user_agent=USER_AGENT, js_re_ignore='/web\/ImageCheck.jpg/g')
        proxy = webdriver.Proxy()
        proxy.proxy_type = ProxyType.DIRECT
        proxy.add_to_capabilities(webdriver.DesiredCapabilities.PHANTOMJS)
        driver.start_session(webdriver.DesiredCapabilities.PHANTOMJS)
        # 以前遇到过driver.get(url)一直不返回，但也不报错的问题，这时程序会卡住，设置超时选项能解决这个问题。
        driver.set_page_load_timeout(13)
        # 设置10秒脚本超时时间
        driver.set_script_timeout(13)
        driver.get(MAIN_URL)
        return driver

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '身份证号' in params, '缺少身份证号'
        assert '密码' in params, '缺少密码'
        # other check
        身份证号 = params['身份证号']
        密码 = params['密码']

        if len(身份证号) == 0:
            raise InvalidParamsError('身份证号为空，请输入身份证号')
        elif len(身份证号) < 15:
            raise InvalidParamsError('身份证号不正确，请重新输入')

        if len(密码) == 0:
            raise InvalidParamsError('密码为空，请输入密码！')
        elif len(密码) < 6:
            raise InvalidParamsError('密码不正确，请重新输入！')
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

    def _unit_login(self, params: dict):
        err_msg = None
        params
        if params:
            try:
                self._check_login_params(params)
                id_num = params['身份证号']
                pwd = params['密码']
                yzm = params['vc']
                #self._do_login(id_num, pwd, yzm)
                resp = self.s.post(CVC_URL, data=dict(
                    client='NBHRSS_WEB',
                    yzm=yzm))
                soup = BeautifulSoup(resp.content, 'html.parser')
                infors = json.loads(soup.text)
                if infors['result']=='0':
                    resp = self.s.post(LOGIN_URL, data=dict(
                        id=id_num,
                        password=pwd,
                        client='NBHRSS_WEB',
                        phone=''))
                    soup = BeautifulSoup(resp.content, 'html.parser')
                    infor = json.loads(soup.text)
                    if infor['ret']=='1':
                        print("登录成功！")
                        inforr=json.loads(infor['result'])
                        self.g.access_token=inforr['access_token']
                        self.result_data["baseInfo"] = {
                            '城市名称': '宁波',
                            '城市编号': '330200',
                            '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                            '姓名': inforr['xm'],
                            '身份证号': inforr['sfz'],
                            '社会保障卡号码': inforr['sbkh']
                        }
                        self.result_identity['target_name'] = inforr['xm']
                    elif infor['msg']=='E1001':
                        raise InvalidParamsError('请去官网进行账号升级！')
                    else:
                        raise InvalidParamsError(infor['msg'])
                else:
                    raise InvalidParamsError('验证码错误！')

                self.result_key = id_num
                self.result_meta['身份证号'] = id_num
                self.result_meta['密码'] = pwd
                self.result_identity['task_name'] = '宁波'
                self.result_identity['target_id'] = id_num

                return
            except (AssertionError, InvalidParamsError) as e:
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
            time.sleep(8)
            # Image.open(io.BytesIO(driver.get_screenshot_as_png())).show()
            if driver.current_url == INFO_URL:
                print('登录成功')
                # 保存登录后的页面内容供抓取单元解析使用
                login_page_html = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
                self.s.soup = BeautifulSoup(login_page_html, 'html.parser')


                # realname=soup.select('#xm')[0].text
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
            time.sleep(3)
            htmls = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
            soupyl = BeautifulSoup(htmls, 'html.parser')
            mingxitable = soupyl.select('#content')
            tableinfo = mingxitable[0].find_all('tr')
            self.result_data['old_age'] = {}
            self.result_data['old_age']['data'] = {}
            arrstr = []
            years = ''
            months = ''
            maxtime=''
            y=1
            for row in tableinfo:
                arr = []
                cell = [i.text for i in row.find_all('td')]
                if len(cell) < 3:
                    arrstr.extend(cell)
                elif len(cell) == 4:
                    yearmonth = cell[0]
                    if years == '' or years != yearmonth[:4]:
                        years = yearmonth[:4]
                        self.result_data['old_age']['data'][years] = {}
                        if len(months) > 0:
                            if months == yearmonth[-2:]:
                                self.result_data['old_age']['data'][years][months] = {}
                    if months == '' or months != yearmonth[-2:]:
                        months = yearmonth[-2:]
                        self.result_data['old_age']['data'][years][months] = {}
                    dicts = {
                        '缴费时间': cell[0],
                        '缴费类型': '',
                        '缴费基数': cell[1],
                        '公司缴费': '',
                        '个人缴费': cell[2],
                        '缴费单位': '',
                        '到账情况': cell[3]
                    }
                    if y==1:
                        maxtime=cell[0]
                    y=y+1
                    arr.append(dicts)
                    self.result_data['old_age']['data'][years][months] = arr
            # print(arrstr)
            if len(arrstr) > 2:
                self.result_data["baseInfo"].setdefault('单位名称', arrstr[2].replace('单位名称：', ''))
            nowyears = time.strftime("%Y", time.localtime())
            if len(arrstr)>8:
                jfscolder = int(arrstr[10].replace('至本年末实际缴费月数：', ''))
                ljjfolder = float(arrstr[9].replace('至本年末账户累计储存额：', ''))
            else:
                jfscolder=0
                ljjfolder=0.00
            if nowyears in self.result_data['old_age']['data'].keys():
                for k, v in self.result_data['old_age']['data'][nowyears].items():
                    jfscolder = jfscolder + 1
                    ljjfolder = ljjfolder + float(v[0]['个人缴费'])
            self.result_data["baseInfo"].setdefault('缴费时长', jfscolder)
            self.result_data["baseInfo"].setdefault('个人养老累计缴费', ljjfolder)
            self.result_data["baseInfo"].setdefault('最近缴费时间',maxtime)
            if len(self.result_data['old_age']['data'])>0:
                ksjfsj = min(self.result_data['old_age']['data'])
                self.result_data["baseInfo"].setdefault('开始缴费时间', ksjfsj + min(self.result_data['old_age']['data'][ksjfsj]))
            else:
                self.result_data["baseInfo"].setdefault('开始缴费时间','')
            if len(arrstr) > 3:
                cbzt = arrstr[3].replace('参保状态：', '')
            else:
                cbzt ='未知'
            if cbzt == '参保缴费':
                cbzt = '正常参保'
            else:
                cbzt = '停缴'
            self.result_identity['status'] = cbzt
            self.g.Fivestatus = {'养老': cbzt}

    def _yiliao(self):
        with self.dsc.get_driver_ctx() as driver:
            driver.get(YIL_URL)
            time.sleep(3)
            htmls = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
            soupyl = BeautifulSoup(htmls, 'html.parser')
            mingxitable = soupyl.select('#content')
            tableinfo = mingxitable[0].find_all('tr')
            self.result_data['medical_care'] = {}
            self.result_data['medical_care']['data'] = {}
            arrstr = []
            years = ''
            months = ''
            for row in tableinfo:
                arr = []
                cell = [i.text for i in row.find_all('td')]
                if len(cell) < 3:
                    arrstr.extend(cell)
                elif len(cell) == 4:
                    yearmonth = cell[0]
                    if years == '' or years != yearmonth[:4]:
                        years = yearmonth[:4]
                        self.result_data['medical_care']['data'][years] = {}
                        if len(months) > 0:
                            if months == yearmonth[-2:]:
                                self.result_data['medical_care']['data'][years][months] = {}
                    if months == '' or months != yearmonth[-2:]:
                        months = yearmonth[-2:]
                        self.result_data['medical_care']['data'][years][months] = {}
                    dicts = {
                        '缴费时间': cell[0],
                        '缴费类型': '',
                        '缴费基数': cell[1],
                        '公司缴费': '',
                        '个人缴费': cell[2],
                        '缴费单位': '',
                        '到账情况': cell[3]
                    }
                    arr.append(dicts)
                    self.result_data['medical_care']['data'][years][months] = arr
            # print(arrstr)
            nowyears = time.strftime("%Y", time.localtime())
            if len(arrstr)>10:
                ljjfolder = float(arrstr[11].replace('个人账户余额：', ''))
            else:
                ljjfolder = 0.00
            if nowyears in self.result_data['old_age']['data'].keys():
                for k, v in self.result_data['old_age']['data'][nowyears].items():
                    ljjfolder = ljjfolder + float(v[0]['个人缴费'])
            self.result_data["baseInfo"].setdefault('个人医疗累计缴费', ljjfolder)
            if len(arrstr) >4:
                cbzt = arrstr[4].replace('参保状态：', '')
            else:
                cbzt ='未知'
            if cbzt == '参保缴费':
                cbzt = '正常参保'
            else:
                cbzt = '停缴'
            self.g.Fivestatus.setdefault('医疗', cbzt)

    def _gongshang(self):
        with self.dsc.get_driver_ctx() as driver:
            driver.get(GS_URL)
            time.sleep(3)
            htmls = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
            soupyl = BeautifulSoup(htmls, 'html.parser')
            mingxitable = soupyl.select('#content')
            tableinfo = mingxitable[0].find_all('tr')
            arrstr = []
            for row in tableinfo:
                arr = []
                cell = [i.text for i in row.find_all('td')]
                if len(cell) < 3:
                    arrstr.extend(cell)
            if len(arrstr) > 3:
                cbzt = arrstr[3].replace('参保状态：', '')
            else:
                cbzt ='未知'
            if cbzt == '参保缴费':
                cbzt = '正常参保'
            else:
                cbzt = '停缴'
            self.g.Fivestatus.setdefault('工伤', cbzt)

    def _shiye(self):
        with self.dsc.get_driver_ctx() as driver:
            driver.get(SY_URL)
            time.sleep(3)
            htmls = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
            soupyl = BeautifulSoup(htmls, 'html.parser')
            mingxitable = soupyl.select('#content')
            tableinfo = mingxitable[0].find_all('tr')
            arrstr = []
            for row in tableinfo:
                arr = []
                cell = [i.text for i in row.find_all('td')]
                if len(cell) < 3:
                    arrstr.extend(cell)
            if len(arrstr) > 3:
                cbzt = arrstr[3].replace('参保状态：', '')
            else:
                cbzt ='未知'
            if cbzt == '参保缴费':
                cbzt = '正常参保'
            else:
                cbzt = '停缴'
            self.g.Fivestatus.setdefault('失业', cbzt)

    def _shengyu(self):
        with self.dsc.get_driver_ctx() as driver:
            driver.get(SHY_URL)
            time.sleep(3)
            htmls = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
            soupyl = BeautifulSoup(htmls, 'html.parser')
            mingxitable = soupyl.select('#content')
            tableinfo = mingxitable[0].find_all('tr')
            arrstr = []
            for row in tableinfo:
                arr = []
                cell = [i.text for i in row.find_all('td')]
                if len(cell) < 3:
                    arrstr.extend(cell)
            if len(arrstr) > 3:
                cbzt = arrstr[3].replace('参保状态：', '')
            else:
                cbzt ='未知'
            if cbzt == '参保缴费':
                cbzt = '正常参保'
            else:
                cbzt = '停缴'
            self.g.Fivestatus.setdefault('生育', cbzt)

    def _unit_fetch_name(self):
        """用户信息"""
        try:
            respss=self.s.get('https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/query/query-grxx.jsp')

            urls = 'https://app.nbhrss.gov.cn/nbykt/rest/commapi?access_token=' + self.g.access_token + '&api=10S006&bustype=01&refresh=true&client=NBHRSS_WEB'
            resp = self.s.get(urls)

            urls='https://app.nbhrss.gov.cn/nbykt/rest/commapi?access_token='+self.g.access_token+'&api=10S005&bustype=01&refresh=true&client=NBHRSS_WEB'
            resp=self.s.get(urls)
            soup =BeautifulSoup(resp.content, 'html.parser')
            infor = json.loads(soup.text)
            infors=json.loads(infor['result'])
            if infors['AAC004']=='1':
                xb='男'
            elif infors['AAC004']=='2':
                xb='女'
            else:
                xb = '未说明性别'
            if infors['AAZ502']=='1':
                kt='正常有卡状态'
            elif infors['AAZ502']=='2':
                kt='正式挂失状态'
            elif infors['AAZ502']=='4':
                kt = '临时挂失状态'
            else:
                kt=''
            self.result_data['baseInfo']['性别']=xb
            if 'AZA103' in infors.keys():
                self.result_data['baseInfo']['国籍'] = infors['AZA103']
            self.result_data['baseInfo']['社保卡状态'] = kt
            if 'AAE010' in infors.keys():
                self.result_data['baseInfo']['银行账号'] = infors['AAE010']
            if 'AAZ503' in infors.keys():
                self.result_data['baseInfo']['发卡日期'] = infors['AAZ503']
            if 'AAE004' in infors.keys():
                self.result_data['baseInfo']['手机号'] = infors['AAE004']
            if 'AAE005' in infors.keys():
                self.result_data['baseInfo']['固定号码'] = infors['AAE005']
            if 'AAE006' in infors.keys():
                self.result_data['baseInfo']['常住地址'] = infors['AAE006']
            if 'AAZ220' in infors.keys():
                self.result_data['baseInfo']['邮编'] = infors['AAZ220']

            urls = 'https://app.nbhrss.gov.cn/nbykt/rest/commapi?access_token=' + self.g.access_token + '&api=10S005&bustype=01&refresh=true&client=NBHRSS_WEB'
            resp = self.s.get(urls)
            Fivestatus = {}
          #   #养老状态
            resp=self.s.get('https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/query/query-ylbx.jsp')

            #第一次
            ylurl = 'https://app.nbhrss.gov.cn/nbykt/rest/commapi?access_token=' + self.g.access_token + '&api=91S099&bustype=01&refresh=true&client=NBHRSS_WEB'
            resp = self.s.get(ylurl)

            # 第二次
            ylurl = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/rzxt/getTimeOut.action'
            resp = self.s.post(ylurl)

            # 第三次
            ylurl = 'https://app.nbhrss.gov.cn/nbykt/rest/commapi?access_token=' + self.g.access_token + '&api=91S001&bustype=01&refresh=true&param={"AAB301":"330200"}&client=NBHRSS_WEB'
            resp = self.s.get(ylurl)
            soupyl = BeautifulSoup(resp.content, 'html.parser')
            ylinfo = json.loads(soupyl.text)
            if ylinfo['ret'] == '1':
                ylinfos = json.loads(ylinfo['result'])
                cbzt = ylinfos['AAC008']  # arrstr[3].replace('参保状态：', '')
                Fivestatus={'养老': cbzt}
                if cbzt == '参保缴费':
                    cbzt = '正常参保'
                else:
                    cbzt = '停缴'
                self.result_data["baseInfo"].setdefault('单位名称',ylinfos['AAB004'])

          #养老第四次
            ylurls='https://app.nbhrss.gov.cn/nbykt/rest/commapi?access_token='+self.g.access_token+'&api=91S002&bustype=01&param={"AAB301":"330200","PAGENO":1,"PAGESIZE":10000}&client=NBHRSS_WEB'
            resps=self.s.get(ylurls)
            soupyls = BeautifulSoup(resps.content, 'html.parser')
            ylinfos=json.loads(soupyls.text)
            if ylinfos['ret']=='1':
                ylinfof=json.loads(ylinfos['result'])
                self.result_data['old_age'] = {}
                self.result_data['old_age']['data'] = {}
                years = ''
                months = ''
                maxtime = ''
                y = 1
                for i in range(0, len(ylinfof['COSTLIST']['COST'])):
                    arr = []
                    cell = ylinfof['COSTLIST']['COST'][i]
                    # if len(cell) < 3:
                    #     arrstr.extend(cell)
                    # elif len(cell) == 4:
                    yearmonth = cell['AAE002']
                    if years == '' or years != yearmonth[:4]:
                        years = yearmonth[:4]
                        self.result_data['old_age']['data'][years] = {}
                        if len(months) > 0:
                            if months == yearmonth[-2:]:
                                self.result_data['old_age']['data'][years][months] = {}
                    if months == '' or months != yearmonth[-2:]:
                        months = yearmonth[-2:]
                        self.result_data['old_age']['data'][years][months] = {}
                    dicts = {
                        '缴费时间': cell['AAE002'],
                        '缴费类型': '',
                        '缴费基数': cell['AAE180'],
                        '公司缴费': '',
                        '个人缴费': cell['AAE022'],
                        '缴费单位': '',
                        '到账情况': cell['AAE078']
                    }
                    if y == 1:
                        maxtime = cell['AAE002']
                        y = 2
                    arr.append(dicts)
                    self.result_data['old_age']['data'][years][months] = arr

                nowyears = time.strftime("%Y", time.localtime())
                #第五次
                ylurl = 'https://app.nbhrss.gov.cn/nbykt/rest/commapi?access_token=' + self.g.access_token + '&api=91S003&bustype=01&refresh=true&param={"AAB301":"330200"}&client=NBHRSS_WEB'
                resp = self.s.get(ylurl)
                soupyl = BeautifulSoup(resp.content, 'html.parser')
                ylinfo = json.loads(soupyl.text)
                if ylinfo['ret'] == '1':
                    ylinfos = json.loads(ylinfo['result'])
                    if len(ylinfos['COSTLIST']['COST']) > 1:
                        jfscolder = int(ylinfos['COSTLIST']['COST'][0]['AAE091'])  # arrstr[10].replace('至本年末实际缴费月数：', '')
                        ljjfolder = float(ylinfos['COSTLIST']['COST'][0]['AAE382'])  # arrstr[9].replace('至本年末账户累计储存额：', '')
                    else:
                        jfscolder = 0
                        ljjfolder = 0.00
                else:
                    jfscolder = 0
                    ljjfolder = 0.00
                if nowyears in self.result_data['old_age']['data'].keys():
                    for k, v in self.result_data['old_age']['data'][nowyears].items():
                        jfscolder = jfscolder + 1
                        ljjfolder = ljjfolder + float(v[0]['个人缴费'])
                self.result_data["baseInfo"].setdefault('缴费时长', jfscolder)
                self.result_data["baseInfo"].setdefault('个人养老累计缴费', ljjfolder)
                self.result_data["baseInfo"].setdefault('最近缴费时间', maxtime)
                if len(self.result_data['old_age']['data']) > 0:
                    ksjfsj = min(self.result_data['old_age']['data'])
                    self.result_data["baseInfo"].setdefault('开始缴费时间',
                                                            ksjfsj + min(self.result_data['old_age']['data'][ksjfsj]))
                else:
                    self.result_data["baseInfo"].setdefault('开始缴费时间', '')

            #医疗
            resp = self.s.get('https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/web/pages/query/query-yilbx.jsp')
            # 第一次
            ylurl = 'https://app.nbhrss.gov.cn/nbykt/rest/commapi?access_token=' + self.g.access_token + '&api=91S099&bustype=01&refresh=true&client=NBHRSS_WEB'
            resp = self.s.get(ylurl)

            # 第二次
            ylurl = 'https://rzxt.nbhrss.gov.cn/nbsbk-rzxt/rzxt/getTimeOut.action'
            resp = self.s.post(ylurl)

            # 第三次
            ylurl = 'https://app.nbhrss.gov.cn/nbykt/rest/commapi?access_token=' + self.g.access_token + '&api=91S011&bustype=01&refresh=true&param={"AAB301":"330200"}&client=NBHRSS_WEB'
            resp = self.s.get(ylurl)
            soupyl = BeautifulSoup(resp.content, 'html.parser')
            ylinfo = json.loads(soupyl.text)
            ylinfos = json.loads(ylinfo['result'])
            cbzt = ylinfos['AAC008']  # arrstr[3].replace('参保状态：', '')
            # if cbzt == '参保缴费':
            #     cbzt = '正常参保'
            # else:
            #     cbzt = '停缴'
            Fivestatus.setdefault('医疗',cbzt)

            # 第四次
            ylurls = 'https://app.nbhrss.gov.cn/nbykt/rest/commapi?access_token=' + self.g.access_token + '&api=91S012&bustype=01&param={"AAB301":"330200","PAGENO":1,"PAGESIZE":10000}&client=NBHRSS_WEB'
            resps = self.s.get(ylurls)
            soupyls = BeautifulSoup(resps.content, 'html.parser')
            ylinfos = json.loads(soupyls.text)
            if ylinfos['ret']=='1':
                ylinfof = json.loads(ylinfos['result'])
                self.result_data['medical_care'] = {}
                self.result_data['medical_care']['data'] = {}
                years = ''
                months = ''
                for i in range(0, len(ylinfof['COSTLIST']['COST'])):
                    arr = []
                    cell = ylinfof['COSTLIST']['COST'][i]
                    yearmonth = cell['AAE002']
                    if years == '' or years != yearmonth[:4]:
                        years = yearmonth[:4]
                        self.result_data['medical_care']['data'][years] = {}
                        if len(months) > 0:
                            if months == yearmonth[-2:]:
                                self.result_data['medical_care']['data'][years][months] = {}
                    if months == '' or months != yearmonth[-2:]:
                        months = yearmonth[-2:]
                        self.result_data['medical_care']['data'][years][months] = {}
                    dicts = {
                        '缴费时间': cell['AAE002'],
                        '缴费类型': '',
                        '缴费基数': cell['AAE180'],
                        '公司缴费': '',
                        '个人缴费': cell['AAE022'],
                        '缴费单位': '',
                        '到账情况': cell['AAE078']
                    }
                    arr.append(dicts)
                    self.result_data['medical_care']['data'][years][months] = arr
                # print(arrstr)

                nowyears = time.strftime("%Y", time.localtime())
                ylurl = 'https://app.nbhrss.gov.cn/nbykt/rest/commapi?access_token=' + self.g.access_token + '&api=91S013&bustype=01&refresh=true&param={"AAB301":"330200"}&client=NBHRSS_WEB'
                resp = self.s.get(ylurl)
                soupyl = BeautifulSoup(resp.content, 'html.parser')
                ylinfo = json.loads(soupyl.text)
                if ylinfo['ret'] == '1':
                    ylinfos = json.loads(ylinfo['result'])
                    if len(ylinfos) > 1:
                        ljjfolder = float(ylinfos['AKC087'])  # arrstr[9].replace('至本年末账户累计储存额：', '')
                    else:
                        ljjfolder = 0.00
                else:
                    ljjfolder = 0.00
                if nowyears in self.result_data['old_age']['data'].keys():
                    for k, v in self.result_data['old_age']['data'][nowyears].items():
                        ljjfolder = ljjfolder + float(v[0]['个人缴费'])
                self.result_data["baseInfo"].setdefault('个人医疗累计缴费', ljjfolder)

            # 工伤
            ylurl = 'https://app.nbhrss.gov.cn/nbykt/rest/commapi?access_token=' + self.g.access_token + '&api=91S018&bustype=01&refresh=true&param={"AAB301":"330200"}&client=NBHRSS_WEB'
            resp = self.s.get(ylurl)
            soupyl = BeautifulSoup(resp.content, 'html.parser')
            ylinfo = json.loads(soupyl.text)
            if ylinfo['ret'] == '1':
                ylinfos = json.loads(ylinfo['result'])
                cbzt = ylinfos['AAC008']  # arrstr[3].replace('参保状态：', '')
                # if cbzt == '参保缴费':
                #     cbzt = '正常参保'
                # else:
                #     cbzt = '停缴'
                Fivestatus.setdefault('工伤', cbzt)

            # 生育
            ylurl = 'https://app.nbhrss.gov.cn/nbykt/rest/commapi?access_token=' + self.g.access_token + '&api=91S019&bustype=01&refresh=true&param={"AAB301":"330200"}&client=NBHRSS_WEB'
            resp = self.s.get(ylurl)
            soupyl = BeautifulSoup(resp.content, 'html.parser')
            ylinfo = json.loads(soupyl.text)
            if ylinfo['ret'] == '1':
                ylinfos = json.loads(ylinfo['result'])
                cbzt = ylinfos['AAC008']  # arrstr[3].replace('参保状态：', '')
                # if cbzt == '参保缴费':
                #     cbzt = '正常参保'
                # else:
                #     cbzt = '停缴'
                Fivestatus.setdefault('生育', cbzt)

            #失业
            ylurl = 'https://app.nbhrss.gov.cn/nbykt/rest/commapi?access_token=' + self.g.access_token + '&api=91S020&bustype=01&refresh=true&param={"AAB301":"330200"}&client=NBHRSS_WEB'
            resp = self.s.get(ylurl)
            soupyl = BeautifulSoup(resp.content, 'html.parser')
            ylinfo = json.loads(soupyl.text)
            if ylinfo['ret'] == '1':
                ylinfos = json.loads(ylinfo['result'])
                cbzt = ylinfos['AAC008']  # arrstr[3].replace('参保状态：', '')
                # if cbzt == '参保缴费':
                #     cbzt = '正常参保'
                # else:
                #     cbzt = '停缴'
                Fivestatus.setdefault('失业', cbzt)
            # self.result_data["baseInfo"] = {
            #     '城市名称': '宁波',
            #     '城市编号': '330200',
            #     '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
            #     '姓名': soup.select('#xm')[0].text,
            #     '性别': soup.select('#xb')[0].text,
            #     '身份证号': soup.select('#sfz')[0].text,
            #     '国籍': soup.select('#gj')[0].text,
            #     '社会保障卡号码': soup.select('#sbkh')[0].text,
            #     '社保卡状态': soup.select('#kzt')[0].text,
            #     '银行账号': soup.select('#yhkh')[0].text,
            #     '发卡日期': soup.select('#fkrq')[0].text,
            #     '手机号': soup.select('#sjhm')[0].text,
            #     '固定号码': soup.select('#gddh')[0].text,
            #     '常住地址': soup.select('#czdz')[0].text,
            #     '邮编': soup.select('#yzbm')[0].text
            # }



            # self._yanglao()
            # self._yiliao()
            # self._gongshang()
            # self._shiye()
            # self._shengyu()
            self.result_data["baseInfo"].setdefault('五险状态', Fivestatus)
            if '参保缴费' in Fivestatus.values():
                self.result_identity['status'] = '正常'
            else:
                self.result_identity['status'] = '停缴'
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        vc_url = VC_URL + time.strftime('%a %b %d %Y %H:%M:%S', time.localtime())
        resp = self.s.get(vc_url)
        return dict(cls='data:image', content=resp.content, content_type=resp.headers.get('Content-Type'))


if __name__ == "__main__":
    from services.client import TaskTestClient

    meta = {'身份证号': '330522198506175712', '密码': '023243'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()
    #'身份证号': '330282198707218248', '密码': 'sqf1769981270'
#'身份证号': '330227198906162713', '密码': '362415'  身份证号': '362330198408045478', '密码': '19841984 '身份证号': '320924197906206491', '密码': '810998''身份证号': '330227198906162713', '密码': '362415''身份证号': '360427196807192017', '密码': '717174'