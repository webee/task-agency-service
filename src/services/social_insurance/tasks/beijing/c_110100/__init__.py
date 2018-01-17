import re
import time
import datetime
import requests
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, InvalidConditionError
from services.commons import AbsFetchTask

LOGIN_PAGE_URL = 'http://www.bjrbj.gov.cn/csibiz/indinfo/login.jsp'
LOGIN_URL = 'http://www.bjrbj.gov.cn/csibiz/indinfo/login_check'
VC_URL = 'http://www.bjrbj.gov.cn/csibiz/indinfo/validationCodeServlet.do'
MAIN_URL = 'http://www.bjrbj.gov.cn/csibiz/indinfo/index.jsp'
USER_INFO_URL = "http://www.bjrbj.gov.cn/csibiz/indinfo/search/ind/indNewInfoSearchAction"
DETAILED_LIST_URL = "http://www.bjrbj.gov.cn/csibiz/indinfo/search/ind/indPaySearchAction!"
MEDICAL_TREATMENT_URL = "http://www.bjrbj.gov.cn/csibiz/indinfo/search/ind/indMedicalSearchAction!queryMedicalInfo"
SMS_URL = "http://www.bjrbj.gov.cn/csibiz/indinfo/passwordSetAction!getTelSafeCode"


class Task(AbsFetchTask):

    task_info = dict(
        city_name="北京市",
        expect_time=10,
        sms_time=120,
        help="""
        <li>若您尚未登录过请登录北京社保官网点击新用户注册，按新用户帮助其中的步骤完成登录密码的设置。</li>
        <li>注册时填写的手机号信息，方便您在登录时收取短信验证码。</li>
        <li>若您无法正常登录，可以查看相关帮助，或者拨打96102。</li>
        """,
        developers=[{'name':'赵伟', 'email':'zw1@qinqinxiaobao.com'}]
    )

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36'
        }

    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_user_info, self._unit_login)
        self._add_unit(self._unit_get_payment_details, self._unit_login)
        self._add_unit(self._unit_fetch_user_medical_treatment, self._unit_login)

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()
        elif t == 'SMS':
            return self._new_SMS(params["data"])

    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert 'j_username' in params, '缺少身份证号'
        assert 'j_password' in params, '缺少密码'
        assert 'safecode' in params, '缺少验证码'
        assert 'i_phone' in params, '缺少短信验证码'

        j_username_re = r'(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)'
        assert re.findall(j_username_re, params['j_username']), '请输入有效的身份证编号'
        assert 8 <= len(params['j_password']) <= 20, '请输入不少于8位的合法登录密码'
        assert len(params['safecode']) >= 4, '请重新输入附加码'
        assert len(params['i_phone']) >= 4, '请输入短信验证码'

        # other check

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if 'j_username' not in params:
                params['j_username'] = meta.get('身份证编号')
            if 'j_password' not in params:
                params['j_password'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == 'j_username' and '身份证编号' in meta:
                continue
            elif pr['key'] == 'j_password' and '密码' in meta:
                continue
            elif pr['key'] == 'other':
                continue
            # if pr['key'] == 'other':
            #     continue
            res.append(pr)
        return res

    # 初始化/登录
    def _unit_login(self, params=None, from_error=False):
        err_msg = None
        resp = self.s.get(LOGIN_PAGE_URL)
        n = datetime.datetime.now() + datetime.timedelta(days=1)
        # if 1 <= n.day <= 8 or from_error:
        #     soup = BeautifulSoup(resp.content, 'html.parser')
        #     if not soup.find('form'):
        #         # 可能暂停维护了
        #         raise TaskNotAvailableError(soup.find('td').text)
        #     if from_error:
        #         return
        if 1 <= n.day <= 6 or from_error:
            raise TaskNotAvailableError("社保局官网正在例行维护")

        if params:
            try:
                self._check_login_params(params)
                j_username = params['j_username']
                j_password = params['j_password']
                safecode = params['safecode']
                i_phone = params['i_phone']

                resp = self.s.post(LOGIN_URL, data=dict(
                    j_username=j_username,
                    j_password=j_password,
                    safecode=safecode,
                    type=1,
                    flag=3,
                    i_phone=i_phone
                ))
                if resp.url != 'http://www.bjrbj.gov.cn/csibiz/indinfo/index.jsp':
                    data = BeautifulSoup(resp.content, "html.parser")
                    try:
                        errormsg = data.findAll("table")[3].findAll("font")[0].text.replace("\r", "").replace("\n", "").replace("\t", "")
                    except IndexError:
                        errormsg = data.find("body").find("font").text
                    except:
                        errormsg = "服务器繁忙，请稍后重试"

                    raise InvalidParamsError(errormsg)

                self.result['key'] = j_username
                self.result['meta'] = {
                    '身份证编号': j_username,
                    '密码': j_password
                }
                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)
            except Exception as e:
                self._unit_login(params, from_error=True)
                raise

        raise AskForParamsError([
            dict(key='other', name='[{"tabName":"城市职工","tabCode":"1","isEnable":"1"},{"tabName":"城市居民","tabCode":"2","isEnable":"0"}]', cls='tab'),
            dict(key='j_username', name='身份证号', cls='input', tabCode="1", value=params.get('j_username', '')),
            dict(key='j_password', name='密码', cls='input:password', tabCode="1", value=params.get('j_password', '')),
            dict(key='safecode', name='附加码', cls='data:image', query={'t': 'vc'}, tabCode="1", value=params.get('safecode', '')),
            dict(key='i_phone', name='验证码', cls='data:SMS', query={'t': 'SMS'}, tabCode="1", value=''),
        ], err_msg)

    # 获取用户基础信息
    def _unit_fetch_user_info(self):
        try:
            data = self.result['data']
            resp = self.s.post(USER_INFO_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')

            result = soup.find('form', {'id': 'printForm'})
            table1 = result.findAll("table")[0]
            table2 = result.findAll("table")[1]

            td0 = re.sub('\s', '', table1.text)
            companyName = re.findall(r"单位名称：(.+?)统一社会信用代码（组织机构代码）：", td0)
            if len(companyName) > 0:
                companyName = companyName[0]
            else:
                companyName = ''
            companyCode = re.findall(r"统一社会信用代码（组织机构代码）：(.+?)社会保险登记号：", td0)
            if len(companyCode) > 0:
                companyCode = companyCode[0]
            else:
                companyCode = ''
            socialCode = re.findall(r"社会保险登记号：(.+?)所属区县：", td0)
            if len(socialCode) > 0:
                socialCode = socialCode[0]
            else:
                socialCode = ''
            fromCity = td0[td0.find("所属区县：")+5:]

            td1 = table2.findAll("td")

            socialType = re.sub('\s', '', td1[1].text)
            socialType = socialType.replace("[", "").replace("]", ",")
            socialType = socialType.split(",")
            old_age_state = {
                "养老": "",
                "医疗": "",
                "失业": "",
                "工伤": "",
                "生育": ""
            }
            for item in socialType:
                if "养老" in item:
                    old_age_state["养老"] = item.replace("养老缴费", "")
                if "医保" in item:
                    old_age_state["医疗"] = item.replace("医保缴费", "")
                if "失业" in item:
                    old_age_state["失业"] = item.replace("失业缴费", "")
                if "工伤" in item:
                    old_age_state["工伤"] = item.replace("工伤缴费", "")
                if "生育" in item:
                    old_age_state["生育"] = item.replace("生育缴费", "")

            data["baseInfo"] = {
                "单位名称": companyName,
                "组织机构代码": companyCode,
                "社会保险登记证编号": socialCode,
                "所属区县": fromCity,
                "姓名": td1[4].text,
                "身份证号": td1[6].text,
                "更新时间": datetime.datetime.now().strftime('%Y-%m-%d'),
                '城市名称': '北京市',
                '城市编号': '110100',
                '缴费时长': '',
                '最近缴费时间': '',
                '开始缴费时间': '',
                '个人养老累计缴费': '',
                '个人医疗累计缴费': '',
                '五险状态': old_age_state,
                '性别': td1[8].text,
                '出生日期': td1[10].text,
                '民族': td1[12].text,
                '国家/地区': td1[14].text,
                '个人身份': td1[16].text,
                '参加工作日期': td1[18].text,
                '户口所在区县街乡': td1[20].text,
                '户口性质': td1[22].text,
                '户口所在地': td1[24].text,
                '户口所在地邮政编码': td1[26].text,
                '居住地（联系）地址': td1[28].text,
                '居住地（联系）邮政编码': td1[30].text,
                '选择邮寄社会保险对账单地址': td1[32].text,
                '对账单邮政编码': td1[34].text,
                '获取对账单方式': td1[36].text,
                '电子邮件地址': td1[38].text,
                '文化程度': td1[40].text,
                '电话': td1[42].text,
                '手机号': td1[44].text,
                '申报月均工资收入（元）': td1[46].text,
                '证件类型': td1[48].text,
                '证件号码': td1[50].text,
                '委托代发银行名称': td1[52].text,
                '委托代发银行账号': td1[54].text,
                '用工形式': td1[56].text,
                '人员类别': td1[58].text,
                '离退休类别': td1[60].text,
                '离退休日期': td1[62].text,
                '定点医疗机构1': td1[64].text,
                '定点医疗机构2': td1[66].text,
                '定点医疗机构3': td1[68].text,
                '定点医疗机构4': td1[70].text,
                '定点医疗机构5': td1[72].text,
                '是否患有特殊病': td1[74].text,
                '护照号码': td1[77].text,
                '外国人居留证号码': td1[79].text,
                '外国人证件类型': td1[81].text,
                '外国人证件号码': td1[83].text
            }

            # 养老（正常数据与其他补缴信息）
            data["old_age"] = {
                "data": {}
            }

            # 医疗（正常数据与其他补缴信息）
            data["medical_care"] = {
                "data": {}
            }
            # 工伤（正常数据与其他补缴信息）
            data["injuries"] = {
                "data": {}
            }
            # 生育（正常数据与其他补缴信息）
            data["maternity"] = {
                "data": {}
            }
            # 失业（正常数据与其他补缴信息）
            data["unemployment"] = {
                "data": {}
            }

            paymentStart = "停缴"
            if old_age_state["养老"].find("正常") > -1:
                paymentStart = "正常"
            elif old_age_state["医疗"].find("正常") > -1:
                paymentStart = "正常"
            elif old_age_state["失业"].find("正常") > -1:
                paymentStart = "正常"
            elif old_age_state["工伤"].find("正常") > -1:
                paymentStart = "正常"
            elif old_age_state["生育"].find("正常") > -1:
                paymentStart = "正常"

                # 设置identity
            identity = self.result['identity']
            identity.update({
                'task_name': '北京市',
                'target_name': td1[4].text,
                'target_id': td1[6].text,
                'status': paymentStart,
            })

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    # 获取用户明细
    def _unit_fetch_user_DETAILED(self, page_type,  year):
        try:
            resp = self.s.post(DETAILED_LIST_URL + page_type + '?searchYear=' + str(year) + '&time=' + str(int(round(time.time()*1000))))
            soup = BeautifulSoup(str(resp.content, 'utf-8').replace('\r', '').replace('\t', '').replace('\n', '').replace('&nbsp;', '').replace('</tr>  </tr>', '</tr>'), "html.parser")
            return soup
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    # 养老
    def _unit_fetch_user_old_age(self, start_job):
        data = self.result['data']
        # 统计养老实际缴费月数
        self.old_age_month = 0
        # 统计个人缴费养老金额
        self.my_self_old_age = 0
        # 最近参保时间
        self.old_age_lately_data = '199201'

        try:
            nowTime = int(time.strftime('%Y', time.localtime(time.time())))

            for year in range(nowTime, int(start_job) - 1, -1):
                data["old_age"]["data"][str(year)] = {}
                try:
                    # 根据类型获取解析后的页面
                    soup = self._unit_fetch_user_DETAILED('oldage', year)
                except:
                    continue

                table = soup.findAll("table")[0]
                hasErrorMessage = table.find("ul", {"class": "errorMessage"})
                if hasErrorMessage:
                    nowTime = nowTime - 1
                    continue
                # 数据行
                trs = table.findAll("tr")
                # 缴费时间
                date = time.strftime('%Y-%m', time.localtime(time.time()))
                for tr in trs:
                    if tr.text != trs[0].text and tr.text != trs[1].text:
                        td = tr.findAll("td")

                        if td[1].text == "-":
                            continue
                        # 最近参保时间
                        if td[0].text[0:4] == str(nowTime):
                            self.old_age_lately_data = td[0].text.replace("-", "")

                        obj = {}
                        if tr.findAll("td").__len__() == 6:
                            date = td[0].text
                            obj = {
                                 "缴费时间": date,
                                 "缴费类型": re.sub('\s', '', td[1].text),
                                 "缴费基数": re.sub('\s', '', td[2].text),
                                 "公司缴费": re.sub('\s', '', td[3].text),
                                 "个人缴费": re.sub('\s', '', td[4].text),
                                 "缴费单位": re.sub('\s', '', td[5].text),
                            }
                            self.old_age_month = self.old_age_month + 1
                            try:
                                self.my_self_old_age = self.my_self_old_age + float(td[4].text)
                            except:
                                pass

                        if tr.findAll("td").__len__() == 5:
                            obj = {
                                "缴费时间": date,
                                "缴费类型": re.sub('\s', '', td[0].text),
                                "缴费基数": re.sub('\s', '', td[1].text),
                                "公司缴费": re.sub('\s', '', td[2].text),
                                "个人缴费": re.sub('\s', '', td[3].text),
                                "缴费单位": re.sub('\s', '', td[4].text),
                            }
                            try:
                                self.my_self_old_age = self.my_self_old_age + float(td[3].text)
                            except:
                                pass

                        try:
                            data["old_age"]["data"][str(year)][str(date[5:])].append(obj)
                        except:
                            data["old_age"]["data"][str(year)][str(date[5:])] = [obj]
                pass
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    # 医疗
    def _unit_fetch_user_medical_care(self, start_job):
        data = self.result['data']
        # 统计养老实际缴费月数
        self.medical_care_month = 0
        # 统计个人缴费养老金额
        self.my_self_medical_care = 0
        # 最近参保时间
        self.medical_care_lately_data = '199201'

        try:
            nowTime = int(time.strftime('%Y', time.localtime(time.time())))
            for year in range(nowTime, int(start_job) - 1, -1):
                data["medical_care"]["data"][str(year)] = {}
                try:
                    # 根据类型获取解析后的页面
                    soup = self._unit_fetch_user_DETAILED('medicalcare', year)
                except:
                    continue

                table = soup.findAll("table")[0]
                hasErrorMessage = table.find("ul", {"class": "errorMessage"})
                if hasErrorMessage:
                    nowTime = nowTime - 1
                    continue
                # 数据行
                trs = table.findAll("tr")
                # 缴费时间
                date = time.strftime('%Y-%m', time.localtime(time.time()))

                for tr in trs:
                    if tr.text != trs[0].text and tr.text != trs[1].text:
                        td = tr.findAll("td")

                        if td[1].text == "-":
                            continue

                        # 最近参保时间
                        if td[0].text[0:4] == str(nowTime):
                            self.medical_care_lately_data = td[0].text.replace("-", "")

                        obj = {}
                        if tr.findAll("td").__len__() == 6:
                            date = td[0].text
                            obj = {
                                 "缴费时间": date,
                                 "缴费类型": re.sub('\s', '', td[1].text),
                                 "缴费基数": re.sub('\s', '', td[2].text),
                                 "公司缴费": re.sub('\s', '', td[3].text),
                                 "个人缴费": re.sub('\s', '', td[4].text),
                                 "缴费单位": re.sub('\s', '', td[5].text),
                            }
                            self.medical_care_month = self.medical_care_month + 1
                            try:
                                self.my_self_medical_care = self.my_self_medical_care + float(td[4].text)
                            except:
                                pass

                        if tr.findAll("td").__len__() == 5:
                            obj = {
                                "缴费时间": date,
                                "缴费类型": re.sub('\s', '', td[0].text),
                                "缴费基数": re.sub('\s', '', td[1].text),
                                "公司缴费": re.sub('\s', '', td[2].text),
                                "个人缴费": re.sub('\s', '', td[3].text),
                                "缴费单位": re.sub('\s', '', td[4].text),
                            }
                            try:
                                self.my_self_medical_care = self.my_self_medical_care + float(td[3].text)
                            except:
                                pass

                        try:
                            data["medical_care"]["data"][str(year)][str(date[5:])].append(obj)
                        except:
                            data["medical_care"]["data"][str(year)][str(date[5:])] = [obj]
                pass
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    # 工伤
    def _unit_fetch_user_injuries(self, start_job):
        data = self.result['data']
        # 统计养老实际缴费月数
        self.injuries_month = 0
        # 最近参保时间
        self.injuries_lately_data = '199201'

        try:
            nowTime = int(time.strftime('%Y', time.localtime(time.time())))
            for year in range(nowTime, int(start_job) - 1, -1):
                data["injuries"]["data"][str(year)] = {}
                try:
                    # 根据类型获取解析后的页面
                    soup = self._unit_fetch_user_DETAILED('injuries', year)
                except:
                    continue

                table = soup.findAll("table")[0]
                hasErrorMessage = table.find("ul", {"class": "errorMessage"})
                if hasErrorMessage:
                    nowTime = nowTime - 1
                    continue
                # 数据行
                trs = table.findAll("tr")
                # 缴费时间
                date = time.strftime('%Y-%m', time.localtime(time.time()))

                for tr in trs:
                    if tr.text != trs[0].text and tr.text != trs[1].text:

                        td = tr.findAll("td")
                        if td[1].text == "-":
                            continue
                        # 最近参保时间
                        if td[0].text[0:4] == str(nowTime):
                            self.injuries_lately_data = td[0].text.replace("-", "")

                        obj = {}
                        if tr.findAll("td").__len__() == 3:
                            date = td[0].text
                            obj = {
                                 "缴费时间": date,
                                 "缴费类型": '-',
                                 "缴费基数": re.sub('\s', '', td[1].text),
                                 "公司缴费": re.sub('\s', '', td[2].text),
                                 "个人缴费": '-',
                                 "缴费单位": '-',
                            }
                            self.injuries_month = self.injuries_month + 1
                        if tr.findAll("td").__len__() == 2:
                            obj = {
                                "缴费时间": date,
                                "缴费类型": '-',
                                "缴费基数": re.sub('\s', '', td[0].text),
                                "公司缴费": re.sub('\s', '', td[1].text),
                                "个人缴费": '-',
                                "缴费单位": '-',
                            }
                        try:
                            data["injuries"]["data"][str(year)][str(date[5:])].append(obj)
                        except:
                            data["injuries"]["data"][str(year)][str(date[5:])] = [obj]
                pass
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    # 生育
    def _unit_fetch_user_maternity(self, start_job):
        data = self.result['data']
        # 统计养老实际缴费月数
        self.maternity_month = 0
        # 最近参保时间
        self.maternity_lately_data = '199201'

        try:
            nowTime = int(time.strftime('%Y', time.localtime(time.time())))
            for year in range(nowTime, int(start_job) - 1, -1):
                data["maternity"]["data"][str(year)] = {}
                try:
                    # 根据类型获取解析后的页面
                    soup = self._unit_fetch_user_DETAILED('maternity', year)
                except:
                    continue

                table = soup.findAll("table")[0]
                hasErrorMessage = table.find("ul", {"class": "errorMessage"})
                if hasErrorMessage:
                    nowTime = nowTime - 1
                    continue
                # 数据行
                trs = table.findAll("tr")
                # 缴费时间
                date = time.strftime('%Y-%m', time.localtime(time.time()))

                for tr in trs:
                    if tr.text != trs[0].text and tr.text != trs[1].text:
                        td = tr.findAll("td")

                        if td[1].text == "-":
                            continue

                        # 最近参保时间
                        if td[0].text[0:4] == str(nowTime):
                            self.maternity_lately_data = td[0].text.replace("-", "")
                        obj = {}
                        if tr.findAll("td").__len__() == 3:
                            date = td[0].text
                            obj = {
                                 "缴费时间": date,
                                 "缴费类型": '-',
                                 "缴费基数": re.sub('\s', '', td[1].text),
                                 "公司缴费": re.sub('\s', '', td[2].text),
                                 "个人缴费": '-',
                                 "缴费单位": '-',
                            }
                            self.maternity_month = self.maternity_month + 1
                        if tr.findAll("td").__len__() == 2:
                            obj = {
                                "缴费时间": date,
                                "缴费类型": '-',
                                "缴费基数": re.sub('\s', '', td[0].text),
                                "公司缴费": re.sub('\s', '', td[1].text),
                                "个人缴费": '-',
                                "缴费单位": '-',
                            }

                        try:
                            data["maternity"]["data"][str(year)][str(date[5:])].append(obj)
                        except:
                            data["maternity"]["data"][str(year)][str(date[5:])] = [obj]
                pass
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    # 失业
    def _unit_fetch_user_unemployment(self, start_job):
        data = self.result['data']
        # 统计养老实际缴费月数
        self.unemployment_month = 0
        # 最近参保时间
        self.unemployment_lately_data = '199201'

        try:
            nowTime = int(time.strftime('%Y', time.localtime(time.time())))
            for year in range(nowTime, int(start_job) - 1, -1):
                data["unemployment"]["data"][str(year)] = {}
                try:
                    # 根据类型获取解析后的页面
                    soup = self._unit_fetch_user_DETAILED('unemployment', year)
                except:
                    continue

                table = soup.findAll("table")[0]
                hasErrorMessage = table.find("ul", {"class": "errorMessage"})
                if hasErrorMessage:
                    nowTime = nowTime - 1
                    continue
                # 数据行
                trs = table.findAll("tr")
                # 缴费时间
                date = time.strftime('%Y-%m', time.localtime(time.time()))

                for tr in trs:
                    if tr.text != trs[0].text and tr.text != trs[1].text:
                        td = tr.findAll("td")

                        if td[1].text == "-":
                            continue

                        # 最近参保时间
                        if td[0].text[0:4] == str(nowTime):
                            self.unemployment_lately_data = td[0].text.replace("-", "")
                        obj = {}
                        if tr.findAll("td").__len__() == 4:
                            date = td[0].text
                            obj = {
                                 "缴费时间": date,
                                 "缴费类型": '-',
                                 "缴费基数": re.sub('\s', '', td[1].text),
                                 "公司缴费": re.sub('\s', '', td[2].text),
                                 "个人缴费": re.sub('\s', '', td[3].text),
                                 "缴费单位": '-',
                            }
                            self.unemployment_month = self.unemployment_month + 1

                        if tr.findAll("td").__len__() == 3:
                            obj = {
                                "缴费时间": date,
                                "缴费类型": '-',
                                "缴费基数": re.sub('\s', '', td[0].text),
                                "公司缴费": re.sub('\s', '', td[1].text),
                                "个人缴费": re.sub('\s', '', td[2].text),
                                "缴费单位": '-',
                            }

                        try:
                            data["unemployment"]["data"][str(year)][str(date[5:])].append(obj)
                        except:
                            data["unemployment"]["data"][str(year)][str(date[5:])] = [obj]
                pass
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    # 缴费明细main方法
    def _unit_get_payment_details(self):
        try:
            data = self.result['data']
            # 养老明细
            self._unit_fetch_user_old_age(data["baseInfo"]["参加工作日期"][0:4])
            # 医疗明细
            self._unit_fetch_user_medical_care(data["baseInfo"]["参加工作日期"][0:4])
            # 工伤明细
            self._unit_fetch_user_injuries(data["baseInfo"]["参加工作日期"][0:4])
            # 生育明细
            self._unit_fetch_user_maternity(data["baseInfo"]["参加工作日期"][0:4])
            # 失业明细
            self._unit_fetch_user_unemployment(data["baseInfo"]["参加工作日期"][0:4])

            # 五险所有缴费时间
            social_payment_duration = [self.old_age_month,
                                       self.medical_care_month,
                                       self.injuries_month,
                                       self.maternity_month,
                                       self.unemployment_month]

            # 五险最近缴费时间
            latest_time = [self.old_age_lately_data.strip(),
                           self.medical_care_lately_data.strip(),
                           self.injuries_lately_data.strip(),
                           self.maternity_lately_data.strip(),
                           self.unemployment_lately_data.strip()]

            data["baseInfo"]["缴费时长"] = str(max(social_payment_duration))
            data["baseInfo"]["最近缴费时间"] = str(max(latest_time))
            data["baseInfo"]["开始缴费时间"] = data["baseInfo"]["参加工作日期"][0:6]
            data["baseInfo"]["个人养老累计缴费"] = str(self.my_self_old_age)
            data["baseInfo"]["个人医疗累计缴费"] = str(self.my_self_medical_care)

        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    # 医疗待遇
    def _unit_fetch_user_medical_treatment(self):
        data = self.result['data']
        try:
            resp = self.s.post(MEDICAL_TREATMENT_URL)
            soup = BeautifulSoup(str(resp.content, 'utf-8'), "html.parser")
            result = soup.find('div', {'class': 'tab'})
            # 数据行
            tds = result.findAll("td")
            data["medical_treatment"] = {
                "单位名称": tds[4].text[5:],
                "姓名": tds[5].text[3:],
                "单位": tds[6].text[3:],
                re.sub('\s', '', tds[8].text): re.sub('\s', '', tds[9].text),
                re.sub('\s', '', tds[10].text): re.sub('\s', '', tds[11].text),
                re.sub('\s', '', tds[12].text): re.sub('\s', '', tds[13].text),
                re.sub('\s', '', tds[14].text): re.sub('\s', '', tds[15].text),
                re.sub('\s', '', tds[16].text): re.sub('\s', '', tds[17].text),
                "门诊": str(float(re.sub('\s', '', tds[9].text))+float(re.sub('\s', '', tds[11].text))),
                "住院": str(float(re.sub('\s', '', tds[15].text))+float(re.sub('\s', '', tds[17].text)))
            }
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    # （图片）验证码
    def _new_vc(self):
        resp = self.s.get(VC_URL)
        return dict(cls='data:image', content=resp.content, content_type=resp.headers.get('Content-Type'))

    # （短信）验证码
    def _new_SMS(self, params):
        if self.prepared_meta:
            j_username = self.prepared_meta["身份证编号"]
            j_password = self.prepared_meta["密码"]
        else:
            j_username = ''
            j_password = ''

        resp = self.s.post(SMS_URL, data=dict(
            idCode=params.get('j_username', j_username),
            logPass=params.get('j_password', j_password),
            safeCode=params.get('safecode', '')
        ))
        return dict(cls='data:SMS', content=resp.text)


if __name__ == '__main__':
    
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()