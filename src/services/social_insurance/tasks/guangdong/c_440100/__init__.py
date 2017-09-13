from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask

from bs4 import BeautifulSoup
import html
import os
import time
from services.webdriver import new_driver, DriverRequestsCoordinator, DriverType
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json

LOGIN_URL = "http://gzlss.hrssgz.gov.cn/cas/login"
VC_URL = "http://gzlss.hrssgz.gov.cn/cas/captcha.jpg"
USER_AGENT="Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36"
User_BaseInfo="http://gzlss.hrssgz.gov.cn/gzlss_web/business/authentication/menu/getMenusByParentId.xhtml?parentId=SECOND-ZZCXUN"


class value_is_number(object):

    def __init__(self, locator):
        self.locator = locator

    def __call__(self, driver):
        element = driver.find_element(*self.locator)
        val = element.get_attribute('value')
        return val and val.isnumeric()

class Task(AbsFetchTask):
    task_info = dict(
        city_name="广州",
        help="""
        <li>个人用户第一次忘记密码，需要到各办事窗口办理；在办事窗口补充完整相关信息（如电子邮箱地址）以后，忘记密码功能才能使用。</li>
        """
    )

    def _get_common_headers(self):
        return {
            'User-Agent':USER_AGENT,
            # 'Accept-Encoding':'gzip, deflate, sdch',
            # 'X-Requested-With': 'XMLHttpRequest',
            # 'Host':'gzlss.hrssgz.gov.cn'
        }

    def _prepare(self,data=None):
        """恢复状态，初始化结果"""
        super()._prepare(data)

        # state
        # state: dict = self.state
        # TODO: restore from state

        # result
        # result: dict = self.result
        # TODO: restore from result
        self.dsc = DriverRequestsCoordinator(s=self.s, create_driver=self._create_chrome_driver)

    def _create_chrome_driver(self):
        driver = new_driver(user_agent=USER_AGENT, driver_type=DriverType.CHROME)
        return  driver

    def _create_driver(self):
        driver = new_driver(user_agent=USER_AGENT)
        # 不加载验证码
        script = """
        var page = this;
        page.onResourceRequested = function(requestData, networkRequest) {
            var match = requestData.url.match(/captcha.jpg/g);
            if (match != null) {
                //console.log('Request (#' + requestData.id + '): ' + JSON.stringify(requestData));
                //networkRequest.cancel(); // or .abort()
                networkRequest.abort();
            }
        };
        """
        driver.execute('executePhantomScript', {'script': script, 'args': []})
        return driver

    def _query(self, params: dict):
        """任务状态查询"""
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()
            # pass

    def _new_vc(self):
        resp = self.s.get(VC_URL)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '账号' not in params:
                params['账号'] = meta.get('账号')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '账号' and '账号' in meta:
                continue
            elif pr['key'] == '密码' and '密码' in meta:
                continue
            res.append(pr)
        return res

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '账号' in params, '缺少账号'
        assert '密码' in params, '缺少密码'
        # other check
        账号 = params['账号']
        密码 = params['密码']
        if len(密码) < 4:
            raise InvalidParamsError('账号或密码错误')
        if len(账号) < 15:
            raise InvalidParamsError('账号或密码错误')

    def _loadJs(self):
        import execjs
        resps = self.s.get("http://gzlss.hrssgz.gov.cn/cas/login")
        modlus = BeautifulSoup(resps.content).findAll('script')[2].text.split('=')[3].split(';')[0].replace('"', '')
        jsstrs = self.s.get("http://gzlss.hrssgz.gov.cn/cas/third/jquery-1.5.2.min.js")
        jsstr = self.s.get("http://gzlss.hrssgz.gov.cn/cas/third/security.js")
        ctx = execjs.compile(jsstr.text + jsstrs.text)
        key = ctx.call("RSAUtils.getKeyPair", '010001', '', modlus)

        resp = self.s.get("http://gzlss.hrssgz.gov.cn/cas/login")
        lt = BeautifulSoup(resp.content, 'html.parser').find('input', {'name': 'lt'})['value']
        datas = {
            'usertype': "2",
            'lt': lt,
            #'username': params.get('账号'),
            #'password': params.get('密码'),
            '_eventId': 'submit'
        }

        resps = self.s.post(
            "http://gzlss.hrssgz.gov.cn/cas/login?service=http://gzlss.hrssgz.gov.cn:80/gzlss_web/business/tomain/main.xhtml",
            datas)
        raise InvalidParamsError(resps.text)

    def _unit_login(self, params=None):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)

                id_num=params['账号']
                pass_word=params['密码']
                vc = params['vc']

                self._do_login(id_num, pass_word, vc)

                #  登录成功
                # 保存到meta
                self.result_key = id_num
                self.result_meta['账号'] = id_num
                self.result_meta['密码'] = pass_word

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='账号', name='账号', cls='input', value=params.get('账号', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _do_login(self, username, password, vc):
        """使用web driver模拟登录过程"""
        with self.dsc.get_driver_ctx() as driver:
            # 打开登录页
            driver.get(LOGIN_URL)

            username_input = driver.find_element_by_xpath('//*[@id="loginName"]')
            password_input = driver.find_element_by_xpath('//*[@id="loginPassword"]')
            vc_input = driver.find_element_by_xpath('//*[@id="validateCode"]')
            user_type=driver.find_element_by_xpath('//*[@id="usertype2"]')
            submit_btn = driver.find_element_by_xpath('//*[@id="submitbt"]')

            # 用户名
            username_input.clear()
            username_input.send_keys(username)

            # 密码
            password_input.clear()
            password_input.send_keys(password)

            # 验证码
            vc_input.clear()
            vc_input.send_keys(vc)

            user_type.click()

            # 提交
            submit_btn.click()

            if not driver.current_url =='http://gzlss.hrssgz.gov.cn/gzlss_web/business/tomain/main.xhtml':
                raise InvalidParamsError('登录失败，请重新登录！')

            # 登录成功
            # 保存登录后的页面内容供抓取单元解析使用
            self.g.login_page_html = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
            self.g.current_url = driver.current_url

    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            soup=self.s.get(User_BaseInfo)
            s=json.loads(soup.text)
            perURl=s[8]['url']
            res=self.s.get("http://gzlss.hrssgz.gov.cn/gzlss_web"+perURl)
            redata=BeautifulSoup(res.text,'html.parser').findAll('table',{'class':'comitTable'})[0]
            redata2 = BeautifulSoup(res.text,'html.parser').findAll('table', {'class': 'comitTable'})[1]

            # 个人基本信息
            self.result_data['baseInfo']={
                '姓名':redata.find('input',{'id':'aac003ss'})['value'],
                '身份证号':redata.find('input',{'id':'aac002ss'})['value'],
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '城市名称': '广州市',
                '城市编号': '440100',
                '缴费时长':'',
                '最近缴费时间': '',
                '开始缴费时间': '',
                '个人养老累计缴费': '',
                '个人医疗累计缴费': '',

                '个人编号': redata.find('input', {'id': 'aac001'})['value'],
                '性别':redata.find('input',{'id':'aac004ss'})['value'],
                '民族':redata2.find('select',{'id':'aac005'}).find(selected="selected").text.replace('\r','').replace('\n','').replace('\t',''),
                '户口性质':redata.find('input',{'id':'aac009ss'})['value'],
                '出生日期':redata.find('input',{'id':'aac006ss'})['value'],
                '单位名称':redata.find('input',{'id':'aab069ss'})['value'],
                '地址':redata2.find('input',{'id':'bab306'})['value'],
                '电子邮箱':redata2.find('input',{'id':'bbc019'})['value']
            }

            # identity信息
            self.result_identity.update({
                "task_name": "广州",
                "target_name": redata.find('input',{'id':'aac003ss'})['value'],
                "target_id": self.result_meta['账号'],
                "status": ""
            })

            # 社保明细
            # 养老保险明细
            self.result_data['old_age'] = {"data": {}}
            dataBaseE = self.result_data['old_age']["data"]
            modelE = {}

            # 医疗保险明细
            self.result_data['medical_care'] = {"data": {}}
            dataBaseH = self.result_data['medical_care']["data"]
            modelH = {}

            # 失业保险明细
            self.result_data['unemployment'] = {"data": {}}
            dataBaseI = self.result_data['unemployment']["data"]
            modelI = {}

            # 工伤保险明细
            self.result_data['injuries'] = {"data": {}}
            dataBaseC=self.result_data['injuries']["data"]
            modelC={}

            # 生育保险明细
            self.result_data['maternity'] = {"data": {}}
            dataBaseB = self.result_data['maternity']["data"]
            modelB = {}

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    meta = {'账号': '441225199102281010', '密码': 'wtz969462'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()

    # 441225199102281010  wtz969462
