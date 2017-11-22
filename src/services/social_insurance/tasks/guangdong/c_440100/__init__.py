from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError, InvalidConditionError
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
import re
import datetime

LOGIN_URL = "http://gzlss.hrssgz.gov.cn/cas/login"
VC_URL = "http://gzlss.hrssgz.gov.cn/cas/captcha.jpg"
USER_AGENT="Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36"
User_BaseInfo="http://gzlss.hrssgz.gov.cn/gzlss_web/business/authentication/menu/getMenusByParentId.xhtml?parentId=SECOND-ZZCXUN"
# Medical_URL="http://gzlss.hrssgz.gov.cn/gzlss_web/business/authentication/menu/getMenusByParentId.xhtml?parentId=SECOND-ZZHUCX"
Search_URL="http://gzlss.hrssgz.gov.cn/gzlss_web/business/front/foundationcentre/getPersonPayHistoryInfoByPage.xhtml?querylog=true&businessocde=SBGRJFLSCX&visitterminal=PC"
Sixian_URL="http://gzlss.hrssgz.gov.cn/gzlss_web/business/front/foundationcentre/viewPage/viewPersonPayHistoryInfo.xhtml?xzType=1&startStr=&endStr=&querylog=true&businessocde=291QB-GRJFLS&visitterminal=PC&aac001="
Yiliao_URL="http://gzlss.hrssgz.gov.cn/gzlss_web/business/front/foundationcentre/getHealthcarePersonPayHistorySumup.xhtml?query=1&querylog=true&businessocde=291QB_YBGRJFLSCX&visitterminal=PC&aac001="

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
        <li>由于目前缴费历史的查询量较多，为减轻广州社保系统压力，限制每人每天只能查询5次，敬请谅解！</li>
        """,

        developers=[{'name': '程菲菲', 'email': 'feifei_cheng@chinahrs.net'}]
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
        self.result_data['baseInfo']={}
        # state
        # state: dict = self.state
        # TODO: restore from state

        # result
        # result: dict = self.result
        # TODO: restore from result
        self.dsc = DriverRequestsCoordinator(s=self.s, create_driver=self._create_driver)

    def _create_chrome_driver(self):
        driver = new_driver(user_agent=USER_AGENT, driver_type=DriverType.CHROME)
        return  driver

    def _create_driver(self):
        driver = new_driver(user_agent=USER_AGENT, js_re_ignore='/cas\/captcha.jpg/g')
        # 随便访问一个相同host的地址，方便之后设置cookie
        driver.get('http://gzlss.hrssgz.gov.cn/xxxx')
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

            # 登录
            driver.find_element_by_xpath('//*[@id="submitbt"]').click()

            if driver.current_url.startswith('http://gzlss.hrssgz.gov.cn/cas/login'):
                err_msg = '登录失败，请重新登录！'
                try:
                    err_msg = driver.find_element_by_xpath('//*[@id="*.errors"]').text
                finally:
                    raise InvalidParamsError(err_msg)

            # 登录成功

    def _to_replace(self,con):
        res=con.replace('\r','').replace('\n','').replace('\t','')
        return res

    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            s=json.loads(self.s.get(User_BaseInfo).text)   # 个人信息导航
            s2=s[0]['url']
            res=self.s.get("http://gzlss.hrssgz.gov.cn/gzlss_web"+s2)   # 个人基础信息

            if(len(BeautifulSoup(res.text,'html.parser').findAll('table',{'class':'comitTable'}))<=0):
                raise TaskNotAvailableError("网络异常，请重新登录")
                return

            redata=BeautifulSoup(res.text,'html.parser').findAll('table',{'class':'comitTable'})[0]   # 姓名等信息
            redata2 = BeautifulSoup(res.text,'html.parser').findAll('table', {'class': 'comitTable'})[1]   #民族等信息


            # 社保明细
            userNum=BeautifulSoup(self.s.get(Search_URL).text,'html.parser').find('select',{'id':'aac001'}).text.replace('\n','')   # 员工编号
            sixian=BeautifulSoup(self.s.get(Sixian_URL+userNum).text,'html.parser').find('table').findAll("tr",{'class':'table_white_data'})

            # 医疗保险明细
            permedicalTotal=0.0
            HmoneyCount=0
            paraURL = "&startStr=199001&endStr=" + time.strftime('%Y%m', time.localtime()) + ""  # 医疗保险地址参数
            yiliao = BeautifulSoup(self.s.get(Yiliao_URL + userNum + paraURL).text, 'html.parser')
            a = yiliao.find('table', {'id': 'tableDataList'}).find('script').text
            if "请明天再查" in a:
                raise TaskNotAvailableError("您今天的缴费历史查询已经达到5次，请明天再查。")

            self.result_data['medical_care'] = {"data": {}}
            dataBaseH = self.result_data['medical_care']["data"]
            modelH = {}

            si_status=""
            sidata = yiliao.find('table', {'id': 'tableDataList'})
            if 'alert' not in sidata.text:
                if len(sidata.findAll("tr"))>1:
                    si_status = self._to_replace(sidata.findAll("tr")[1].findAll("td")[10].text)[0:2]  # 缴存状态
                    si_com = self._to_replace(sidata.findAll("tr")[2].findAll("td")[3].text)  # 缴费单位
                    yiliaoData = sidata.findAll("tr", {'temp': '职工社会医疗保险'})

                    for a in range(len(yiliaoData)):
                        td = yiliaoData[a].findAll("td")
                        permedicalTotal += float(re.findall(r"\d+\.?\d*", td[7].text)[0])

                        yearH = self._to_replace(td[1].text)[0:4]
                        monthH = self._to_replace(td[1].text)[4:6]
                        rangNum = int(self._to_replace(td[3].text))
                        HmoneyCount += rangNum
                        for a1 in range(-1, rangNum - 1):
                            nowtime = datetime.date(int(yearH) + (int(monthH) + a1) // 12, (int(monthH) + a1) % 12 + 1,1).strftime('%Y%m')
                            modelH = {
                                '缴费单位': si_com,
                                '缴费类型': si_status,
                                '缴费时间': nowtime,
                                '缴费基数': self._to_replace(td[9].text),
                                '政府资助': re.findall(r"\d+\.?\d*", td[8].text)[0],
                                '公司缴费': float(re.findall(r"\d+\.?\d*", td[6].text)[0]) / rangNum,
                                '个人缴费': float(re.findall(r"\d+\.?\d*", td[7].text)[0]) / rangNum
                            }
                            dataBaseH.setdefault(nowtime[0:4], {})
                            dataBaseH[nowtime[0:4]].setdefault(nowtime[4:6], [])
                            dataBaseH[nowtime[0:4]][nowtime[4:6]].append(modelH)
                else:
                    raise TaskNotImplementedError("未查询到数据！")
            else:
                errormsg2=sidata.text.split('(')[1].split(')')[0]
                raise TaskNotImplementedError(errormsg2)


            # 养老保险明细
            self.result_data['old_age'] = {"data": {}}
            dataBaseE = self.result_data['old_age']["data"]
            modelE = {}
            peroldTotal=0.0
            for b in range(len(sixian) - 3):
                td2 = sixian[b].findAll("td")
                if(td2[5].text.strip()!=''):
                    peroldTotal += float(td2[5].text)

                    yearE = td2[0].text[0:4]
                    monthE = td2[0].text[4:6]
                    rangNumE = int(td2[2].text)
                    for b1 in range(-1, rangNumE - 1):
                        nowtime2 = datetime.date(int(yearE) + (int(monthE) + b1) // 12, (int(monthE) + b1) % 12 + 1,1).strftime('%Y%m')
                        modelE = {
                            '缴费单位': td2[11].text,
                            '缴费类型': td2[12].text,
                            '缴费时间': nowtime2,
                            '缴费基数': td2[3].text,
                            '公司缴费': float(td2[4].text) / rangNumE,
                            '个人缴费': float(td2[5].text) / rangNumE
                        }
                        dataBaseE.setdefault(nowtime2[0:4], {})
                        dataBaseE[nowtime2[0:4]].setdefault(nowtime2[4:6], [])
                        dataBaseE[nowtime2[0:4]][nowtime2[4:6]].append(modelE)


            # 失业保险明细
            self.result_data['unemployment'] = {"data": {}}
            dataBaseI = self.result_data['unemployment']["data"]
            modelI = {}
            for c in range(len(sixian) - 3):
                td3 = sixian[c].findAll("td")
                if(td3[0].text.strip()!=""):
                    yearI = td3[0].text[0:4]
                    monthI = td3[0].text[4:6]
                    rangNumI = int(td3[2].text)
                    for c1 in range(-1, rangNumI - 1):
                        nowtime3 = datetime.date(int(yearI) + (int(monthI) + c1) // 12, (int(monthI) + c1) % 12 + 1,
                                                 1).strftime('%Y%m')
                        modelI = {
                            '缴费单位': td3[11].text,
                            '缴费类型': td3[12].text,
                            '缴费时间': nowtime3,
                            '缴费基数': td3[3].text,
                            '公司缴费': float(td3[6].text) / rangNumI,
                            '个人缴费': float(td3[7].text) / rangNumI
                        }
                        dataBaseI.setdefault(nowtime3[0:4], {})
                        dataBaseI[nowtime3[0:4]].setdefault(nowtime3[4:6], [])
                        dataBaseI[nowtime3[0:4]][nowtime3[4:6]].append(modelI)


            # 工伤保险明细
            self.result_data['injuries'] = {"data": {}}
            dataBaseC=self.result_data['injuries']["data"]
            modelC={}
            for d in range(len(sixian) - 3):
                td4 = sixian[d].findAll("td")
                if (td4[0].text.strip() != ""):
                    yearC = td4[0].text[0:4]
                    monthC = td4[0].text[4:6]
                    rangNumC = int(td4[2].text)
                    for d1 in range(-1, rangNumC - 1):
                        nowtime4 = datetime.date(int(yearC) + (int(monthC) + d1) // 12, (int(monthC) + d1) % 12 + 1,1).strftime('%Y%m')
                        modelC = {
                            '缴费单位': td4[11].text,
                            '缴费类型': td4[12].text,
                            '缴费时间': nowtime4,
                            '缴费基数': td4[3].text,
                            '公司缴费': float(td4[8].text) / rangNumC,
                            '个人缴费': '-'
                        }
                        dataBaseC.setdefault(nowtime4[0:4], {})
                        dataBaseC[nowtime4[0:4]].setdefault(nowtime4[4:6], [])
                        dataBaseC[nowtime4[0:4]][nowtime4[4:6]].append(modelC)


            # 生育保险明细
            self.result_data['maternity'] = {"data": {}}
            dataBaseB = self.result_data['maternity']["data"]
            modelB = {}
            for f in range(len(sixian) - 3):
                td5 = sixian[f].findAll("td")
                if (td5[0].text.strip() != ""):
                    yearB = td5[0].text[0:4]
                    monthB = td5[0].text[4:6]
                    rangNumB = int(td5[2].text)
                    for f1 in range(-1, rangNumB - 1):
                        nowtime5 = datetime.date(int(yearB) + (int(monthB) + f1) // 12, (int(monthB) + f1) % 12 + 1,1).strftime('%Y%m')
                        modelB = {
                            '缴费单位': td5[11].text,
                            '缴费类型': td5[12].text,
                            '缴费时间': nowtime5,
                            '缴费基数': td5[3].text,
                            '公司缴费': float(td5[9].text) / rangNumB,
                            '个人缴费': '-'
                        }
                        dataBaseB.setdefault(nowtime5[0:4], {})
                        dataBaseB[nowtime5[0:4]].setdefault(nowtime5[4:6], [])
                        dataBaseB[nowtime5[0:4]][nowtime5[4:6]].append(modelB)


            # 大病保险明细
            dabingData = sidata.findAll("tr", {'temp': '重大疾病医疗补助'})
            self.result_data['serious_illness'] = {"data": {}}
            dataBaseQ = self.result_data['serious_illness']["data"]
            modelQ = {}

            if(len(dabingData)>0):
                for q in range(len(dabingData)):
                    td6 = dabingData[q].findAll("td")
                    if (td6[0].text.strip() != ""):
                        yearQ = self._to_replace(td[1].text)[0:4]
                        monthQ = self._to_replace(td[1].text)[4:6]
                        rangNumQ = int(self._to_replace(td[3].text))

                        for a1 in range(-1, rangNumQ - 1):
                            nowtime6 = datetime.date(int(yearQ) + (int(monthQ) + a1) // 12, (int(monthQ) + a1) % 12 + 1,1).strftime('%Y%m')
                            modelQ = {
                                '缴费单位': si_com,
                                '缴费类型': si_status,
                                '缴费时间': nowtime6,
                                '缴费基数': self._to_replace(td6[9].text),
                                '政府资助': re.findall(r"\d+\.?\d*", td6[8].text)[0],
                                '公司缴费': float(re.findall(r"\d+\.?\d*", td6[6].text)[0]) / rangNum,
                                '个人缴费': float(re.findall(r"\d+\.?\d*", td6[7].text)[0]) / rangNum
                            }
                            dataBaseQ.setdefault(nowtime6[0:4], {})
                            dataBaseQ[nowtime6[0:4]].setdefault(nowtime6[4:6], [])
                            dataBaseQ[nowtime6[0:4]][nowtime6[4:6]].append(modelQ)

            sixiantype=""
            if(len(sixian)>=4):
                sixiantype=sixian[len(sixian)-4].findAll("td")[12].text
            social_status={
                '医疗':si_status,
                '养老':sixiantype,
                '失业':sixiantype,
                '工伤':sixiantype,
                '生育':sixiantype
            }

            # 缴费时长
            EmoneyCount=sixian[len(sixian)-3].findAll("td")[1].text
            EmoneyCount2=sixian[len(sixian)-3].findAll("td")[2].text
            EmoneyCount3=sixian[len(sixian)-3].findAll("td")[3].text
            EmoneyCount4=sixian[len(sixian)-3].findAll("td")[4].text
            rescount=[EmoneyCount,EmoneyCount2,EmoneyCount3,EmoneyCount4]
            moneyCount=max(rescount)

            # 个人基本信息
            self.result_data['baseInfo'] = {
                '姓名': redata.find('input', {'id': 'aac003ss'})['value'],
                '身份证号': redata.find('input', {'id': 'aac002ss'})['value'],
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '城市名称': '广州市',
                '城市编号': '440100',
                '缴费时长': moneyCount,
                '最近缴费时间':sixian[len(sixian)-4].findAll("td")[1].text,
                '开始缴费时间': sixian[0].findAll("td")[0].text,
                '个人养老累计缴费':peroldTotal,
                '个人医疗累计缴费': permedicalTotal,
                '五险状态': social_status,
                '账户状态':social_status['养老'],

                '个人编号': redata.find('input', {'id': 'aac001'})['value'],
                # '性别': redata.find('input', {'id': 'aac004ss'})['value'],
                #'民族': redata2.find('select', {'id': 'aac005'}).find(selected="selected").text.replace('\r', '').replace('\n', '').replace('\t', ''),
                #'户口性质': redata.find('input', {'id': 'aac009ss'})['value'],
                # '出生日期': redata.find('input', {'id': 'aac006ss'})['value'],
                # '单位名称': redata.find('input', {'id': 'aab069ss'})['value'],
                # '地址': redata2.find('input', {'id': 'bab306'})['value'],
                # '电子邮箱': redata2.find('input', {'id': 'bbc019'})['value']
            }

            # identity信息
            self.result_identity.update({
                "task_name": "广州",
                "target_name": redata.find('input', {'id': 'aac003ss'})['value'],
                "target_id": self.result_meta['账号'],
                "status": social_status['养老']
            })

            # 暂时不用代码
            # siresp=self.s.get("http://gzlss.hrssgz.gov.cn/gzlss_web"+s[1]['url'])  # 四险导航
            # sdata=BeautifulSoup(siresp.text,'html.parser')   # 四险find信息
            # hs = json.loads(self.s.get(Medical_URL).text)  # 医疗保险信息
            # medDetailURL=hs[0]['url']         # 医疗
            # hresp=self.s.get("http://gzlss.hrssgz.gov.cn/gzlss_web"+medDetailURL)
            # hdata = BeautifulSoup(hresp.text, 'html.parser')  # 医疗find信息

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    meta = {'账号': '522526197612020018', '密码': 'xiao687400'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()

    #file=open("D:/789654321.html",'r')


    # 441481198701204831 '密码': taifaikcoi168

    # 440104198710011919 '密码': jy794613

    # 522526197612020018   xiao687400

    # 360722199010034554   LI3003287730

    # 430422199101085412  3003847980
