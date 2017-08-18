import re
import time
import datetime
import requests
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError

LOGIN_URL = 'http://www.bjrbj.gov.cn/csibiz/indinfo/login_check'
VC_URL = 'http://www.bjrbj.gov.cn/csibiz/indinfo/validationCodeServlet.do'
MAIN_URL = 'http://www.bjrbj.gov.cn/csibiz/indinfo/index.jsp'
USER_INFO_URL = "http://www.bjrbj.gov.cn/csibiz/indinfo/search/ind/indNewInfoSearchAction"
DETAILED_LIST_URL = "http://www.bjrbj.gov.cn/csibiz/indinfo/search/ind/indPaySearchAction!"


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
        self._add_unit(self._unit_fetch_user_info, self._unit_login)
        self._add_unit(self._unit_get_payment_details, self._unit_login)


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
        assert 'j_username' in params, '缺少身份证号'
        assert 'j_password' in params, '缺少密码'
        assert 'safecode' in params, '缺少验证码'
        # other check

    # 初始化/登录
    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                j_username = params['j_username']
                j_password = params['j_password']
                safecode = params['safecode']

                resp = self.s.post(LOGIN_URL, data=dict(
                    j_username=j_username,
                    j_password=j_password,
                    safecode=safecode,
                    type=1,
                    flag=3
                ))
                if(resp.url != 'http://www.bjrbj.gov.cn/csibiz/indinfo/index.jsp'):
                    data = BeautifulSoup(resp.content, "html.parser")
                    errormsg = data.findAll("table")[3].findAll("font")[0].text.replace("\r", "").replace("\n", "").replace("\t", "")
                    raise Exception(errormsg)

                self.result['key'] = j_username
                self.result['meta'] = {
                    '身份证编号': j_username,
                    '密码': j_password
                }
                return
            except Exception as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='other', name='[{"tabName":"城市职工","tabCode":"1","isEnable":"1"},{"tabName":"城市居民","tabCode":"2","isEnable":"0"}]', cls='tab'),
            dict(key='j_username', name='身份证号', cls='input', tabCode="1"),
            dict(key='j_password', name='密码', cls='input:password', tabCode="1"),
            dict(key='safecode', name='验证码', cls='data:image', query={'t': 'vc'}, tabCode="1"),
            dict(key='cityName', name='城市Code', cls='input:hidden', value='北京市'),
            dict(key='cityCode', name='城市名称', cls='input:hidden', value='110100')
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
            companyName = re.findall(r"单位名称：(.+?)组织机构代码：", td0)[0]
            companyCode = re.findall(r"组织机构代码：(.+?)社会保险登记证编号：", td0)[0]
            socialCode = re.findall(r"社会保险登记证编号：(.+?)所属区县：", td0)[0]
            fromCity = td0[td0.find("所属区县：")+5:]

            td1 = table2.findAll("td")
            socialType = re.sub('\s', '', td1[1].text) + "end"
            old_age_state = {
                "养老": socialType[socialType.find('[养老缴费(')+6:socialType.find(')缴费][失业缴费(')] + "参保",
                "医疗": socialType[socialType.find('[失业缴费(')+6:socialType.find(')缴费][工伤缴费(')] + "参保",
                "失业": socialType[socialType.find('[工伤缴费(')+6:socialType.find(')缴费][生育缴费(')] + "参保",
                "工伤": socialType[socialType.find('[生育缴费(')+6:socialType.find(')缴费][医保缴费(')] + "参保",
                "生育": socialType[socialType.find('[医保缴费(')+6:socialType.find(')缴费]end')] + "参保"
            }

            data["baseInfo"] = {
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
                '户口所在地地址': td1[24].text,
                '户口所在地邮政编码': td1[26].text,
                '居住地（联系）地址': td1[28].text,
                '居住地（联系）邮政编码': td1[30].text,
                '选择邮寄社会保险对账单地址': td1[32].text,
                '对账单邮政编码': td1[34].text,
                '获取对账单方式': td1[36].text,
                '电子邮件地址': td1[38].text,
                '文化程度': td1[40].text,
                '参保人电话': td1[42].text,
                '参保人手机': td1[44].text,
                '申报月均工资收入（元）': td1[46].text,
                '证件类型': td1[48].text,
                '证件号码': td1[50].text,
                '委托代发银行名称': td1[52].text,
                '委托代发银行账号': td1[54].text,
                '缴费人员类别': td1[56].text,
                '医疗参保人员类别': td1[58].text,
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

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    # 获取用户明细
    def _unit_fetch_user_DETAILED(self, page_type,  year):
        try:
            resp = self.s.post(DETAILED_LIST_URL + page_type + '?searchYear=' + str(year) + '&time=' + str(int(round(time.time()*1000))))
            soup = BeautifulSoup(str(resp.content, 'utf-8').replace('\r', '').replace('\t', '').replace('\n', '').replace('&nbsp;', '').replace('</tr>  </tr>', '</tr>'), "html.parser")
            return soup
        except Exception as e:
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
                # 根据类型获取解析后的页面
                soup = self._unit_fetch_user_DETAILED('oldage', year)

                table = soup.findAll("table")[0]
                # 数据行
                trs = table.findAll("tr")
                # 缴费时间
                date = time.strftime('%Y-%m', time.localtime(time.time()))
                for tr in trs:
                    if tr != trs[0] and tr != trs[1]:
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
        except Exception as e:
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
                # 根据类型获取解析后的页面
                soup = self._unit_fetch_user_DETAILED('medicalcare', year)

                table = soup.findAll("table")[0]
                # 数据行
                trs = table.findAll("tr")
                # 缴费时间
                date = time.strftime('%Y-%m', time.localtime(time.time()))

                for tr in trs:
                    if tr != trs[0] and tr != trs[1]:
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
        except Exception as e:
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
                # 根据类型获取解析后的页面
                soup = self._unit_fetch_user_DETAILED('injuries', year)

                table = soup.findAll("table")[0]
                # 数据行
                trs = table.findAll("tr")
                # 缴费时间
                date = time.strftime('%Y-%m', time.localtime(time.time()))

                for tr in trs:
                    if tr != trs[0] and tr != trs[1]:

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
        except Exception as e:
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
                # 根据类型获取解析后的页面
                soup = self._unit_fetch_user_DETAILED('maternity', year)

                table = soup.findAll("table")[0]
                # 数据行
                trs = table.findAll("tr")
                # 缴费时间
                date = time.strftime('%Y-%m', time.localtime(time.time()))

                for tr in trs:
                    if tr != trs[0] and tr != trs[1]:
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
        except Exception as e:
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
                # 根据类型获取解析后的页面
                soup = self._unit_fetch_user_DETAILED('unemployment', year)

                table = soup.findAll("table")[0]
                # 数据行
                trs = table.findAll("tr")
                # 缴费时间
                date = time.strftime('%Y-%m', time.localtime(time.time()))

                for tr in trs:
                    if tr != trs[0] and tr != trs[1]:
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
        except Exception as e:
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

        except Exception as e:
            raise PreconditionNotSatisfiedError(e)

    # 验证码
    def _new_vc(self):
        resp = self.s.get(VC_URL)
        return dict(cls="data:image", content=resp.content)


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()
