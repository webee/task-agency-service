import base64
import time
import random
import json
import execjs
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
LOGIN_PAGE_URL = 'https://seyb.szsi.gov.cn/web/ggfw/app/index.html#/ggfw/home'
LOGIN_URL = 'https://seyb.szsi.gov.cn/web/ajaxlogin.do'
VC_URL = 'https://seyb.szsi.gov.cn/web/ImageCheck.jpg'
USERINFO_URL = 'https://seyb.szsi.gov.cn/web/ajax.do'


class Task(AbsFetchTask):
    task_info = dict(
        city_name="深圳",
        help="""<li>若您尚未激活或者没有在网上查询过您的社保卡，请点击激活社保账号</li>
        <li>如果您曾经激活过社保卡，但忘记密码，请点击忘记密码</li>
        <li>如办理社保卡时，没有登记手机号码或者更换手机号码，请本人携带身份证原件和新手机到社保分中心柜台办理注册手机变更业务。</li>
        """,
        developers=[{'name': '卜圆圆', 'email': 'byy@qinqinxiaobao.com'}]
    )

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3100.0 Safari/537.36'}

    def _query(self, params: dict):
        """任务状态查询"""
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()
        pass

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
        driver.set_page_load_timeout(20)
        # 设置10秒脚本超时时间
        driver.set_script_timeout(20)
        driver.get(LOGIN_PAGE_URL)

        return driver

    def _create_chrome_driver(self):
        driver = new_driver(user_agent=USER_AGENT, driver_type=DriverType.CHROME)
        return driver

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_userinfo, self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '用户名' in params, '缺少用户名'
        assert '密码' in params, '缺少密码'
        # other check
        用户名 = params['用户名']
        密码 = params['密码']

        if len(用户名) == 0:
            raise InvalidParamsError('用户名为空，请输入用户名')
        elif len(用户名) < 5:
            raise InvalidParamsError('用户名不正确，请重新输入')

        if len(密码) == 0:
            raise InvalidParamsError('密码为空，请输入密码！')
        elif len(密码) < 6:
            raise InvalidParamsError('密码不正确，请重新输入！')

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '用户名' not in params:
                params['用户名'] = meta.get('用户名')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '用户名' and '用户名' in meta:
                continue
            elif pr['key'] == '密码' and '密码' in meta:
                continue
            elif pr['key'] == 'other':
                continue
            res.append(pr)
        return res

    def get_js(self):
        # f = open("D:/WorkSpace/MyWorkSpace/jsdemo/js/des_rsa.js",'r',encoding='UTF-8')
        f = open("ceshi.js", 'r', encoding='UTF-8')
        line = f.readline()
        htmlstr = ''
        while line:
            htmlstr = htmlstr + line
            line = f.readline()
        return htmlstr

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                username = params['用户名']
                password = params['密码']
                vc = params['vc']
                resp=self.s.get('https://seyb.szsi.gov.cn/web/ggfw/app/index.html',timeout=20)
                skeys=resp.cookies._cookies['seyb.szsi.gov.cn']['/web/ggfw/app']['skey'].value

                jsstrs = self.s.get("https://seyb.szsi.gov.cn/web/js/comm/fw/encrypt.js",timeout=20)
                ctx = execjs.compile(jsstrs.content.decode("utf-8"))
                mmmm = ctx.call('encrypt', skeys, password)
                mmjm = ctx.call('stringToHex', mmmm)

                # jsstr = self.get_js()
                # ctxs = execjs.compile(jsstr)
                # mmmms = ctx.call('encrypt',skeys,password)
                # mmjms = ctx.call('stringToHex', mmmms)
                resp = self.s.post(LOGIN_URL, data=dict(
                    r=random.random(),
                    LOGINID=username,
                    PASSWORD=mmjm,
                    IMAGCHECK=vc,
                    OPERTYPE2=3,
                    ISBIND='false',
                    now=time.strftime('%a %b %d %Y %H:%M:%S', time.localtime()),
                    callback=''
                ))
                soup = BeautifulSoup(resp.content, 'html.parser')
                jsonread = json.loads(soup.text.replace('(','').replace(')',''))
                flag=jsonread['flag']
                errormsg = jsonread['message']
                if flag=='-1':
                    raise InvalidParamsError(errormsg)

                #self._do_login(username, password, vc)

                # 登录成功
                self.s.Token = self.s.cookies._cookies['seyb.szsi.gov.cn']['/']['Token'].value

                # 查询（点击查询）
                strr = '?r=' + str(random.random())
                resp = self.s.post(USERINFO_URL + strr, data=dict(_isModel='true',
                                                                  params='{"oper":"FrontPageAction.queryNavDimension","params":{},"datas":{"@tmpGtDatas":{"业务类型":"5"}}}'),
                                   headers={'X-Requested-With': 'XMLHttpRequest',
                                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                            'Accept': 'application / json, text / plain, * / *',
                                            'Token': self.s.Token,
                                            'Connection': 'keep - alive'}, timeout=15)
                self.s.Token = resp.cookies._cookies['seyb.szsi.gov.cn']['/']['Token'].value

                self.result_data["baseInfo"] = {
                    '城市名称': '深圳',
                    '城市编号': '440300',
                    '更新时间': time.strftime("%Y-%m-%d", time.localtime())
                }
                # 查询（点击业务查询请求三次）
                '''第一次'''
                strr = '?r=' + str(random.random())
                resp = self.s.post(USERINFO_URL + strr, data=dict(_isModel='true',
                                                                  params='{"oper":"UnitHandleCommAction.insertLogRecord","params":{},"datas":{"@tmpGtDatas":{"rightId":"500101","rightName":"参保基本信息查询","recordType":"1"}}}'),
                                   headers={'X-Requested-With': 'XMLHttpRequest',
                                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                            'Accept': 'application / json, text / plain, * / *',
                                            'Token': self.s.Token,
                                            'Connection': 'keep - alive'}, timeout=15)

                self.g.Token = resp.cookies._cookies['seyb.szsi.gov.cn']['/']['Token'].value
                '''第二次'''
                datass = dict(
                    _isModel='true',
                    params='{"oper":"CbjbxxcxAction.queryGrcbjbxx","params":{},"datas":{"ncm_gt_用户信息":{"params":{}},"ncm_gt_参保状态":{"params":{}},"ncm_gt_缴纳情况":{"params":{}}}}'
                )
                strrs = USERINFO_URL + '?r=' + str(random.random())
                resps = self.s.post(strrs, datass, headers={'X-Requested-With': 'XMLHttpRequest',
                                                            'Accept-Language': 'zh-CN,zh;q=0.8',
                                                            'Accept-Encoding': 'gzip, deflate, br',
                                                            'Connection': 'keep - alive',
                                                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                                            'Accept': 'application/json,text/plain, */*',
                                                            'Token': self.s.Token,
                                                            'Referer': 'https://seyb.szsi.gov.cn/web/ggfw/app/index.html',
                                                            'Origin': 'https://seyb.szsi.gov.cn',
                                                            'Host': 'seyb.szsi.gov.cn'}, timeout=15)
                # print(resps.text)
                soup = BeautifulSoup(resps.content, 'html.parser')
                self.s.Token = resps.cookies._cookies['seyb.szsi.gov.cn']['/']['Token'].value
                jsonread = json.loads(soup.text)
                if jsonread['flag'] != '-1':
                    userinfo = jsonread['datas']
                    fivedic = {}
                    for k, v in userinfo['ncm_gt_用户信息']['params'].items():
                        if k.find('参保状态') > 0:
                            fivedic.setdefault(k[:2], v)
                        else:
                            if k == '户籍类别':
                                self.result_data["baseInfo"].setdefault('户口性质', v)
                            else:
                                self.result_data["baseInfo"].setdefault(k, v)
                            if k == '姓名':
                                self.result_identity['target_name'] = v
                            if k == '身份证号':
                                self.result_identity['target_id'] = v
                            if k == '参保状态':
                                if v == '正常':
                                    self.result_identity['status'] = '正常缴纳'
                                else:
                                    self.result_identity['status'] = '停缴'

                    monthnum = 0
                    for k, v in userinfo['ncm_gt_缴纳情况']['params'].items():
                        if k == '养老保险累计月数':
                            self.result_data["baseInfo"].setdefault('养老实际缴费月数', v)
                        elif k == '失业保险累计月数':
                            self.result_data["baseInfo"].setdefault('失业实际缴费月数', v)
                        else:
                            self.result_data["baseInfo"].setdefault(k, v)
                        if k.find('保险累计月数') > -1:
                            if (monthnum < int(v)):
                                monthnum = int(v)

                    self.result_data["baseInfo"].setdefault('缴费时长', monthnum)
                    self.result_data["baseInfo"].setdefault('五险状态', fivedic)
                else:
                    raise InvalidParamsError('请您登录社保官网输入社保个人电脑号完成身份认证后，再做查询操作。')

                self.result_key = username

                # 保存到meta
                self.result_meta['用户名'] = username
                self.result_meta['密码'] = password

                self.result_identity['task_name'] = '深圳'

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='用户名', name='用户名', cls='input', value=params.get('用户名', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}, value=params.get('vc', '')),
        ], err_msg)

    def _do_login(self, username, password, vc):
        """使用web driver模拟登录过程"""
        with self.dsc.get_driver_ctx() as driver:
            # 打开登录页
            driver.get(LOGIN_PAGE_URL)
            # 等待lk请求
            # WebDriverWait(driver, 10).until(value_is_number((By.XPATH, '//*[@id="lk"]')))

            # 选择身份证号方式登录
            driver.find_element_by_xpath('/html/body/div[2]/div/div/div/div/div/div[2]/div[2]/div/div[1]/a').click()

            username_input = driver.find_element_by_xpath(
                '//*[@id="div_dialog_login"]/div/div/div/form/div[4]/div/div[1]/div/input')
            password_input = driver.find_element_by_xpath(
                '//*[@id="div_dialog_login"]/div/div/div/form/div[4]/div/div[2]/div/input')
            vc_input = driver.find_element_by_xpath(
                '//*[@id="div_dialog_login"]/div/div/div/form/div[4]/div/div[3]/div/input')
            submit_btn = driver.find_element_by_xpath('//*[@id="div_dialog_login"]/div/div/div/form/div[5]/input[1]')

            # 用户名
            username_input.clear()
            username_input.send_keys(username)

            # 密码
            password_input.clear()
            password_input.send_keys(password)

            vc_input.clear()
            vc_input.send_keys(vc)
            s =driver.find_element_by_tag_name('html').get_attribute('innerHTML')

            # Image.open(io.BytesIO(driver.get_screenshot_as_png())).show()
            # 提交
            submit_btn.click()
            time.sleep(5)
            login_page_html = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
            soup = BeautifulSoup(login_page_html, 'html.parser')
            # WebDriverWait(driver, 10).until(
            #     lambda driver:
            #         EC.invisibility_of_element_located((By.XPATH, 'html/body/div[2]/div/div/div/div[1]/div/div[2]/div[2]/div/div[1]/a[1]'))(driver)
            #     or EC.element_to_be_clickable((By.XPATH, '//*[@id="div_dialog_login"]/div/div/div/form/div[5]/input[1]'))(driver))
            #
            # login_btn = driver.find_element_by_xpath(
            #     'html/body/div[2]/div/div/div/div[1]/div/div[2]/div[2]/div/div[1]/a[1]')
            #
            # s = login_btn.get_attribute('style')
            # Image.open(io.BytesIO(driver.get_screenshot_as_png())).show()
            # if not s:
            #     # failed
            #     err_msg = driver.find_element_by_xpath('//*[@id="div_dialog_login"]/div/div/div/form/div[3]/font').text
            #     raise InvalidParamsError(err_msg)
            #     # TODO
            if len(soup.select('.ng-binding')[1].text) == 16:  # len(soup.findAll('a')[13].attrs)
                err_msg = soup.select('.ng-binding')[2].text
                raise InvalidParamsError(err_msg)
            else:
                # success
                print('success')
                # Image.open(io.BytesIO(driver.get_screenshot_as_png())).show()

                # 保存登录后的页面内容供抓取单元解析使用
                # login_page_html = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
                #
                # # print(login_page_html[login_page_html.find('欢迎')-5:login_page_html.find('欢迎')+15])
                # # if login_page_html.find('<a ng-show="!ncUser" ng-click="login()" style="display: none;">')==-1:
                # resp = self.s.post(LOGIN_URL, data=dict(
                #     r=random.random(),
                #     LOGINID=username,
                #     PASSWORD=login_page_html[login_page_html.find('PASSWORD=')+9:login_page_html.find('&amp;IMAGCHECK=')],
                #     IMAGCHECK=vc,
                #     OPERTYPE2=3,
                #     ISBIND='false',
                #     now=time.strftime('%a %b %d %Y %H:%M:%S', time.localtime()),
                #     callback=''
                # ))
                # soup = BeautifulSoup(resp.content, 'html.parser')
                # jsonread = json.loads(soup.text.replace('(','').replace(')',''))
                # flag=jsonread['flag']
                # errormsg = jsonread['message']
                # if flag=='-1':
                #     raise InvalidParamsError(errormsg)

    def _unit_fetch_userinfo(self):
        """用户信息"""
        try:

            '''第三次'''
            strr = '?r=' + str(random.random())
            resp = self.s.post(USERINFO_URL + strr, data=dict(_isModel='true',
                                                              params='{"oper":"QfzscxAction.queryQfzs","params":{},"datas":{"ncm_gt_欠费总数":{"params":{}}}}'),
                               headers={'X-Requested-With': 'XMLHttpRequest',
                                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                        'Accept': 'application / json, text / plain, * / *',
                                        'Token': self.g.Token,
                                        'Connection': 'keep - alive'}, timeout=15)
            self.s.Token = resp.cookies._cookies['seyb.szsi.gov.cn']['/']['Token'].value

            # TODO: 执行任务，如果没有登录，则raise PermissionError
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _unit_fetch(self):
        """五险"""
        try:
            strr = USERINFO_URL + '?r=' + str(random.random())
            resp = self.s.post(strr,
                               data=dict(_isModel='true',
                                         params='{"oper":"UnitHandleCommAction.insertLogRecord","params":{},"datas":{"@tmpGtDatas":{"rightId":"500201","rightName":"参保缴费明细查询","recordType":"1"}}}'),
                               headers={'X-Requested-With': 'XMLHttpRequest',
                                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                        'Accept': 'application / json, text / plain, * / *',
                                        'Connection': 'keep - alive', 'Token': self.s.Token})
            self.g.Token = resp.cookies._cookies['seyb.szsi.gov.cn']['/']['Token'].value

            # strr = USERINFO_URL + '?r=' + str(random.random())
            # resp = self.s.post(strr, datas, headers={'X-Requested-With': 'XMLHttpRequest',
            #                                          'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            #                                          'Accept': 'application/json,text/plain,*/*',
            #                                          'Accept-Encoding':'gzip,deflate,br',
            #                                          'Accept-Language':'zh-CN,zh;q=0.8',
            #                                          'Connection': 'keep-alive', 'Token': self.s.Token,
            #                                          'Host': 'seyb.szsi.gov.cn', 'Origin': 'https://seyb.szsi.gov.cn',
            #                                          'Referer': 'https://seyb.szsi.gov.cn/web/ggfw/app/index.html'})
            self.g.Token = self.s.Token
            # 明细(险种比较多)arrtype={'01':'基本养老保险','02':'失业保险','03':'基本医疗保险','04':'工伤保险','05':'生育保险'}
            arrtype = {'Yl': 'old_age', 'Shiye': 'unemployment', 'Yil': 'medical_care', 'Gs': 'injuries',
                       'Sy': 'maternity'}
            arrmingxi = ['ncm_glt_养老缴费明细', 'ncm_glt_失业缴费明细', 'ncm_glt_医疗缴费明细', 'ncm_glt_工伤缴费明细', 'ncm_glt_生育缴费明细']
            statetime = ''
            endtime = ''
            ii = 0
            for k, v in arrtype.items():
                self.result_data[v] = {}
                self.result_data[v]['data'] = {}
                years = ''
                months = ''
                personjfsum = 0.00
                datas = dict(
                    _isModel='true',
                    params='{"oper": "CbjfmxcxAction.queryCbjfmx' + k + '", "params": {}, "datas": {"' + arrmingxi[
                        ii] + '": {"params": {"pageSize": 10, "curPageNum": 1}, "dataset": [], "heads": [],"heads_change": []}}}'
                )
                strr = USERINFO_URL + '?r=' + str(random.random())
                resp = self.s.post(strr, datas, headers={'X-Requested-With': 'XMLHttpRequest',
                                                         'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                                         'Accept': 'application / json, text / plain, * / *',
                                                         'Connection': 'keep - alive', 'Token': self.g.Token,
                                                         'Host': 'seyb.szsi.gov.cn',
                                                         'Origin': 'https://seyb.szsi.gov.cn',
                                                         'Referer': 'https://seyb.szsi.gov.cn/web/ggfw/app/index.html'},timeout=15)
                self.g.Token = resp.cookies._cookies['seyb.szsi.gov.cn']['/']['Token'].value
                pagearr = json.loads(resp.text)
                """获取分页"""
                if pagearr['flag'] != '-1':
                    if 'datas' in pagearr.keys():
                        pagesize = pagearr["datas"][arrmingxi[ii]]['params']['pageSize']
                        rowsCount = pagearr["datas"][arrmingxi[ii]]['params']['rowsCount']
                        pagenum = rowsCount / pagesize
                        pagenums = rowsCount // pagesize
                        if pagenum > pagenums:
                            pagenums = pagenums + 1
                        for i in range(1, pagenums + 1):
                            if i != 1:
                                datas = dict(
                                    _isModel='true',
                                    params='{"oper": "CbjfmxcxAction.queryCbjfmx' + k + '", "params": {}, "datas": {"' +
                                           arrmingxi[ii] + '": {"params": {"pageSize": 10, "curPageNum": ' + str(
                                        i) + ',"maxPageSize":50,"rowsCount":' + str(
                                        rowsCount) + ',"Total_showMsg":null,"Total_showMsgCell":null,"Total_Cols":[]},"heads":[],"heads_change":[],"dataset":[]}}}'
                                )
                                strr = USERINFO_URL + '?r=' + str(random.random())
                                resp = self.s.post(strr, datas, headers={'X-Requested-With': 'XMLHttpRequest',
                                                                         'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                                                         'Accept': 'application / json, text / plain, * / *',
                                                                         'Connection': 'keep - alive',
                                                                         'Token': self.g.Token,
                                                                         'Host': 'seyb.szsi.gov.cn',
                                                                         'Origin': 'https://seyb.szsi.gov.cn',
                                                                         'Referer': 'https://seyb.szsi.gov.cn/web/ggfw/app/index.html'},timeout=15)
                                self.g.Token = resp.cookies._cookies['seyb.szsi.gov.cn']['/']['Token'].value
                            mx = json.loads(resp.text)["datas"]
                            for i in range(0, len(mx[arrmingxi[ii]]['dataset'])):
                                arr = []
                                if v == 'old_age' or v == 'medical_care':
                                    personjfsum = personjfsum + float(mx[arrmingxi[ii]]['dataset'][i]['个人缴'])
                                    # enterjfsum=enterjfsum+float(mx['dataset'][i]['单位缴'])
                                yearmonth = mx[arrmingxi[ii]]['dataset'][i]['缴费年月'].replace('年', '').replace('月', '')
                                if len(yearmonth) == 5:
                                    yearmonth = yearmonth[:4] + '0' + yearmonth[-1:]
                                if statetime == '':
                                    statetime = yearmonth
                                elif int(statetime) > int(yearmonth):
                                    statetime = yearmonth
                                if endtime == '':
                                    endtime = yearmonth
                                elif int(endtime) < int(yearmonth):
                                    endtime = yearmonth
                                if years == '' or years != yearmonth[:4]:
                                    years = yearmonth[:4]
                                    self.result_data[v]['data'][years] = {}
                                    if len(months) > 0:
                                        if months == yearmonth[-2:]:
                                            self.result_data[v]['data'][years][months] = {}
                                if months == '' or months != yearmonth[-2:]:
                                    months = yearmonth[-2:]
                                    self.result_data[v]['data'][years][months] = {}
                                mxdic = {
                                    '缴费时间': yearmonth,
                                    '缴费类型': '',
                                    '缴费基数': mx[arrmingxi[ii]]['dataset'][i]['缴费工资'],
                                    '公司缴费': mx[arrmingxi[ii]]['dataset'][i]['单位缴'],
                                    '个人缴费': mx[arrmingxi[ii]]['dataset'][i]['个人缴'],
                                    '缴费单位': mx[arrmingxi[ii]]['dataset'][i]['单位名称'],
                                    '单位编号': mx[arrmingxi[ii]]['dataset'][i]['单位编号'],
                                    '缴费合计': mx[arrmingxi[ii]]['dataset'][i]['缴费合计'],
                                    '备注': mx[arrmingxi[ii]]['dataset'][i]['备注']
                                }
                                arr.append(mxdic)
                                self.result_data[v]['data'][years][months] = arr

                        if v == 'old_age':
                            self.result_data["baseInfo"].setdefault('个人养老累计缴费', personjfsum)
                        if v == 'medical_care':
                            self.result_data["baseInfo"].setdefault('个人医疗累计缴费', personjfsum)
                ii = ii + 1
            self.result_data["baseInfo"].setdefault('最近缴费时间', endtime)
            self.result_data["baseInfo"].setdefault('开始缴费时间', statetime)
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    # 刷新验证码
    def _new_vc(self):
        resp = self.s.get(VC_URL, timeout=20)
        return dict(cls='data:image', content=resp.content, content_type=resp.headers.get('Content-Type'))


if __name__ == '__main__':
    from services.client import TaskTestClient

    meta = {'用户名': 'KevinJ', '密码': 'Zwk667515'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()

    '''有效账号'''
    # '用户名': 'xiaolan0612', '密码': 'Xiaolan0612''用户名': 'lmc13828893775', '密码': 'Luo123465'
    # '用户名':'keguangping'， 密码：'Kegp850907' '用户名': 'Xuxiayu', '密码': 'Xuxiayu143'
    # '用户名': 'ligang860119', '密码': 'ligangL860' 用户名': 'lishaofeng1989', '密码': 'Li8880165'
    # '用户名': 'gaoyingen', '密码': 'Gao1831850' '用户名': 'lmc13828893775', '密码': 'Luo123465'
    #'用户名': 'qinshaohua1983', '密码': 'Qshking1234'
