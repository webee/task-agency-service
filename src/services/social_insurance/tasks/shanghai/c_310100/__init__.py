# 上海  社保信息
import time
import requests
from bs4 import BeautifulSoup
from services.proxyIP import get_proxy_ip
from services.commons import AbsFetchTask
from services.service import AskForParamsError
from services.webdriver import new_driver, DriverRequestsCoordinator

from services.errors import InvalidParamsError, InvalidConditionError, PreconditionNotSatisfiedError

from selenium import webdriver
from selenium.webdriver.common.proxy import Proxy
from selenium.webdriver.common.proxy import ProxyType


LOGIN_URL = "http://www.12333sh.gov.cn/sbsjb/wzb/226.jsp"
LOGIN_SUCCESS_URL = "http://www.12333sh.gov.cn/sbsjb/wzb/helpinfo.jsp?id=0"
VC_URL = "http://www.12333sh.gov.cn/sbsjb/wzb/Bmblist12.jsp"
USER_AGENT = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36"


class value_is_number(object):
    def __init__(self, locator):
        self.locator = locator

    def __call__(self, driver):
        element = driver.find_element(*self.locator)
        val = element.get_attribute('value')
        return val and val.isnumeric()


class Task(AbsFetchTask):
    task_info = dict(
        city_name="上海",
        help="""<li>用户名：为参保人身份证号</li>
        <li>密码：一般为6位数字；</li>
        <li>首次申请密码或遗忘网上登录密码，本人需携带有效身份证件至就近接到社区事务受理中心或就近社保分中心自助机申请办理。</li>
        """,
        developers=[{'name': '程菲菲', 'email': 'feifei_cheng@chinahrs.net'}]
    )

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.12333sh.gov.cn',
        }

    def _prepare(self, data=None):
        super()._prepare(data)
        self.proxy = get_proxy_ip()
        self.s.proxies.update({"http": "http://" + self.proxy})
        self.result_data['baseInfo'] = {}

        self.dsc = DriverRequestsCoordinator(s=self.s, create_driver=self._create_driver)

    def _create_driver(self):
        driver = new_driver(user_agent=USER_AGENT, js_re_ignore='/sbsjb\wzb\/Bmblist12.jpg/g')
        # proxy = webdriver.Proxy()
        # proxy.proxy_type = ProxyType.MANUAL
        # proxy.http_proxy = self.proxy
        # proxy.add_to_capabilities(webdriver.DesiredCapabilities.PHANTOMJS)
        # driver.start_session(webdriver.DesiredCapabilities.PHANTOMJS)
        driver.service.service_args.append('--proxy=http://' + get_proxy_ip())
        # 随便访问一个相同host的地址，方便之后设置cookie
        driver.get('"http://www.12333sh.gov.cn/xxxx')
        return driver

    def _query(self, params: dict):
        """任务状态查询"""
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()
            # pass

    def _new_vc(self):
        ress = self.s.get("http://www.12333sh.gov.cn/sbsjb/wzb/229.jsp", timeout=10)
        resp = self.s.get(VC_URL, timeout=10)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
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
        elif len(用户名) < 15:
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
            res.append(pr)
        return res

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)

                id_num = params.get("用户名")
                account_pass = params.get("密码")
                vc = params.get("vc")

                self._do_login(id_num, account_pass, vc)

                # data = {
                #     'userid': id_num,
                #     'userpw': account_pass,
                #     'userjym': vc.encode('gbk'),
                # }
                # resp = self.s.post("http://www.12333sh.gov.cn/sbsjb/wzb/dologin.jsp", data=data)
                # # 检查是否登录成功
                # if resp.status_code != 200:
                #     raise InvalidParamsError("登录失败")
                #
                # if resp.url != LOGIN_SUCCESS_URL:
                #     soup = BeautifulSoup(resp.content, 'html.parser')
                #     spans = soup.select('tr > td > span')
                #     err_msg = "登录失败"
                #     if spans and len(spans) > 0:
                #         err_msg = spans[0].text
                #     raise InvalidParamsError(err_msg)

                # 设置key
                self.result_key = params.get('用户名')
                # 保存到meta
                self.result_meta['用户名'] = params.get('用户名')
                self.result_meta['密码'] = params.get('密码')
                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='用户名', name='用户名', cls='input', placeholder='请输入身份证号', value=params.get('用户名', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _do_login(self, username, password, vc):
        """使用web driver模拟登录过程"""
        with self.dsc.get_driver_ctx() as driver:
            # 打开登录页
            driver.get(LOGIN_URL)
            driver.get("http://www.12333sh.gov.cn/sbsjb/wzb/229.jsp")

            username_input = driver.find_element_by_xpath('//*[@id="userid"]')
            password_input = driver.find_element_by_xpath('//*[@id="userpw"]')
            vc_input = driver.find_element_by_xpath('//*[@id="userjym"]')

            # 用户名
            username_input.clear()
            username_input.send_keys(username)

            # 密码
            password_input.clear()
            password_input.send_keys(password)

            # 验证码
            vc_input.clear()
            vc_input.send_keys(vc)

            # 登录
            # driver.find_element_by_xpath('//*[@id="ckRecId20"]/form/table[1]/tbody/tr[7]/td[2]/img').click()  # /html/body/form/table/tbody/tr[6]/td[2]
            driver.execute_script('checkForm()')
            time.sleep(5)

            if driver.current_url != "http://www.12333sh.gov.cn/sbsjb/wzb/helpinfo.jsp?id=0":
                raise InvalidParamsError('登录失败，请重新登录！')

    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            resp = self.s.get("http://www.12333sh.gov.cn/sbsjb/wzb/sbsjbcx12.jsp")
            soup = BeautifulSoup(resp.content, 'html.parser')
            # years = soup.find('xml', {'id': 'dataisxxb_sum3'}).findAll("jsjs")
            details = soup.find('xml', {'id': 'dataisxxb_sum2'}).findAll("jsjs")

            if (soup.find('xml', {'id': 'dataisxxb_sum4'}).find('jsjs2') != None):
                moneyTime = soup.find('xml', {'id': 'dataisxxb_sum4'}).find('jsjs2').text
            else:
                moneyTime = len(details)

            # 社保缴费明细
            # 养老
            self.result_data['old_age'] = {
                "data": {}
            }
            dataBaseE = self.result_data['old_age']["data"]
            modelE = {}
            personmoney = 0.00

            dt = soup.findAll("jfdwinfo")

            for a in range(len(details)):
                yearE = details[a].find('jsjs1').text[0:4]
                monthE = details[a].find('jsjs1').text[4:6]

                dataBaseE.setdefault(yearE, {})
                dataBaseE[yearE].setdefault(monthE, [])

                modelE = {
                    '缴费时间': details[a].find('jsjs1').text,
                    '缴费单位': self._match_commapy(details[a].find('jsjs1').text, dt),
                    '缴费基数': details[a].find('jsjs3').text,
                    '缴费类型': '-',
                    '公司缴费': '-',
                    '个人缴费': details[a].find('jsjs4').text,

                    # '实缴金额': self._match_money(details[a].find('jsjs1').text, years[a].find('jsjs1').text,years[a].find('jsjs3').text)
                }
                personmoney += float(details[a].find('jsjs4').text)
                dataBaseE[yearE][monthE].append(modelE)

            # 医疗
            self.result_data['medical_care'] = {
                "data": {}
            }
            dataBaseH = self.result_data['medical_care']["data"]
            modelH = {}

            for b in range(len(details)):
                yearH = details[b].find('jsjs1').text[0:4]
                monthH = details[b].find('jsjs1').text[4:6]

                dataBaseH.setdefault(yearH, {})
                dataBaseH[yearH].setdefault(monthH, [])

                modelH = {
                    '缴费时间': details[b].find('jsjs1').text,
                    '缴费单位': self._match_commapy(details[b].find('jsjs1').text, dt),
                    '缴费基数': details[b].find('jsjs3').text,
                    '缴费类型': '-',
                    '公司缴费': '-',
                    '个人缴费': details[b].find('jsjs6').text,
                }
                dataBaseH[yearH][monthH].append(modelH)

            # 失业
            self.result_data['unemployment'] = {
                "data": {}
            }
            dataBaseI = self.result_data['unemployment']["data"]
            modelI = {}

            for c in range(len(details)):
                yearI = details[c].find('jsjs1').text[0:4]
                monthI = details[c].find('jsjs1').text[4:6]

                dataBaseI.setdefault(yearI, {})
                dataBaseI[yearI].setdefault(monthI, [])

                modelI = {
                    '缴费时间': details[c].find('jsjs1').text,
                    '缴费单位': self._match_commapy(details[c].find('jsjs1').text, dt),
                    '缴费基数': details[c].find('jsjs3').text,
                    '缴费类型': '-',
                    '公司缴费': '-',
                    '个人缴费': details[c].find('jsjs8').text,
                }
                dataBaseI[yearI][monthI].append(modelI)

            # 工伤
            self.result_data['injuries'] = {
                "data": {}
            }

            # 生育
            self.result_data['maternity'] = {
                "data": {}
            }

            # 大病
            self.result_data["serious_illness"] = {
                "data": {}
            }

            self.result_identity.update({
                "task_name": "上海",
                "target_name": soup.find('xm').text,
                "target_id": self.result_meta['用户名'],
                "status": ""
            })

            if (soup.find('xml', {'id': 'dataisxxb_sum4'}).find('jsjs3') != None):
                personOldMoney = soup.find('xml', {'id': 'dataisxxb_sum4'}).find('jsjs3').text
            else:
                personOldMoney = personmoney

            startTime=""
            recentTime=""
            if(len(details)!=0):
                startTime=details[0].find('jsjs1').text
                recentTime=details[len(details) - 1].find('jsjs1').text

            self.result['data']['baseInfo'] = {
                '姓名': soup.find('xm').text,
                '身份证号': self.result_meta['用户名'],
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '城市名称': '上海市',
                '城市编号': '310100',
                '缴费时长': moneyTime,
                '最近缴费时间':recentTime ,
                '开始缴费时间': startTime,
                '个人养老累计缴费': personOldMoney,
                '个人医疗累计缴费': '',
                '账户状态': ''
            }

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _match_money(self, dtime1, dtime2, fmoney):
        if (dtime1 == dtime2):
            return fmoney
        else:
            return ""

    def _match_commapy(self, dtime, dt):
        rescom = ""
        if (dt != None):
            for tr in range(len(dt)):
                trd = dt[tr].find('jfsj').text.split('-')
                if (trd[0] <= dtime <= trd[1]):
                    rescom = dt[tr].find('jfdw').text

        return rescom


if __name__ == '__main__':
    from services.client import TaskTestClient

    # client = TaskTestClient(Task(SessionData()))
    # client.run()

    meta = {'用户名': '372901198109035010', '密码': '903503'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()

    # 321322199001067241  123456       5002931643   123456
