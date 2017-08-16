import time
import json
import datetime
import requests
import base64
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError

LOGIN_URL = 'http://ggfw.cqhrss.gov.cn/ggfw/LoginBLH_login.do'
VC_URL = 'http://ggfw.cqhrss.gov.cn/ggfw/validateCodeBLH_image.do'
USER_INFO_URL = "http://ggfw.cqhrss.gov.cn/ggfw/QueryBLH_main.do?code=888"
DETAILED_LIST_URL = "http://ggfw.cqhrss.gov.cn/ggfw/QueryBLH_query.do"


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
        assert 'sfzh' in params, '缺少身份证号'
        assert 'password' in params, '缺少密码'
        assert 'validateCode' in params, '缺少验证码'
        # other check

    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                sfzh = params['sfzh']
                password = base64.b64encode(params['password'].encode(encoding="utf-8"))
                validateCode = params['validateCode']

                resp = self.s.post(LOGIN_URL, data=dict(
                    sfzh=sfzh,
                    password=password,
                    validateCode=validateCode
                ))
                data = resp.json()
                errormsg = data.get('message')
                if data.get('code') != '3':
                    raise Exception(errormsg)

                self.result['key'] = sfzh
                self.result['meta'] = {
                    '身份证编号': sfzh,
                    '密码': params['password']
                }
                return
            except Exception as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='sfzh', name='身份证号', cls='input'),
            dict(key='password', name='密码', cls='input:password'),
            dict(key='validateCode', name='验证码', cls='data:image', query={'t': 'vc'}),
            dict(key='cityCode', name='城市Code', cls='input:hidden', value={'code': '重庆市'}),
            dict(key='cityName', name='城市名称', cls='input:hidden', value={'code': '500100'})
        ], err_msg)

    # 获取用户基本信息
    def _unit_fetch_user_info(self):
        try:
            data = self.result['data']
            resp = self.s.post(USER_INFO_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            # 基本信息三个table表单
            tables = soup.findAll('table')

            # 姓名
            name = None
            # 个人编号
            personNum = None
            # 性别
            sex = None
            # 民族
            mz = None
            # 身份证编号
            idCard = None
            # 出生年月
            birthDay = None
            # 所在公司编号
            CompanyCode = None
            # 户口性质
            hkxz = None
            # 个人身份
            sf = None
            # 所在公司
            Company = None
            i = 0
            for table in tables:
                tds = table.findAll('td')
                if i == 0:
                    name = tds[1].text.strip()
                    personNum = tds[3].text.strip()
                    sex = tds[5].text.strip()
                    mz = tds[7].text.strip()
                    idCard = tds[9].text.strip()
                    startTime = tds[11].text.strip()
                    birthDay = tds[13].text.strip()
                    CompanyCode = tds[15].text.strip()
                    hkxz = tds[17].text.strip()
                    sf = tds[19].text.strip()
                elif i == 1:
                    Company = tds[2].text.strip()
                elif i == 2:
                    self.old_age_lately_start_data = tds[7].text
                    self.medical_care_lately_start_data = tds[8].text.strip()
                    self.injuries_lately_start_data = tds[9].text.strip()
                    self.maternity_lately_start_data = tds[10].text.strip()
                    self.unemployment_lately_start_data = tds[11].text.strip()

                    old_age_state = {
                        "养老": tds[13].text.strip(),
                        "医疗": tds[14].text.strip(),
                        "失业": tds[15].text.strip(),
                        "工伤": tds[16].text.strip(),
                        "生育": tds[17].text.strip()
                    }
                i = i + 1

            data["baseInfo"] = {
                "姓名": name,
                "社保编号": personNum,
                "性别": sex,
                "民族": mz,
                "出生年月": birthDay,
                "所在公司编号": CompanyCode,
                "户口性质": hkxz,
                "个人身份": sf,
                "所在公司": Company,
                "身份证号": idCard,
                "五险状态": old_age_state,
                "更新时间": datetime.datetime.now().strftime('%Y-%m-%d'),
                "城市名称": '重庆市',
                "城市编号": '500100',
                "缴费时长": '',
                "最近缴费时间": '',
                "开始缴费时间": '',
                "个人养老累计缴费": '',
                "个人医疗累计缴费": ''
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
    def _unit_fetch_user_DETAILED(self, bizType, year):
        try:
            resp = self.s.post(DETAILED_LIST_URL, data={
                'code': bizType,
                'year': year,
                'pageSize': 200
            })
            soup = BeautifulSoup(str(resp.content, 'utf-8'), "html.parser")
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

        isStart = True
        try:
            nowTime = int(time.strftime('%Y', time.localtime(time.time())))
            for year in range(nowTime, int(start_job)-1, -1):
                # 根据类型获取解析后的页面
                soup = self._unit_fetch_user_DETAILED("015", year)
                num = 0
                # 返回结果
                result = json.loads(str(soup))
                if result["code"] == '1':
                    data["old_age"]["data"][str(year)] = {}
                    # 循环行
                    for item in result["result"]:
                        # 个人缴费金额
                        grjfje = item.get('grjfje', '0')
                        # 个人缴费累金额
                        self.my_self_old_age = self.my_self_old_age + float(grjfje)
                        # 定义数据结构
                        obj = {
                            "year": year,
                            "data": {
                                "缴费时间": item["xssj"],
                                "缴费类型": item["jflx"],
                                "缴费基数": item["jfjs"],
                                "公司缴费": "-",
                                "个人缴费": grjfje,
                                "缴费单位": item["dwmc"],
                            }
                        }

                        if item["jfbz"] == "已实缴":
                            if nowTime == year and isStart:
                                self.old_age_lately_data = item["xssj"].replace("-", "")
                                isStart = False
                            # 累计正常缴费的缴费月数
                            self.old_age_month = self.old_age_month + 1
                            # 苏州目前账号来看每个月只会生成一条数据，
                            # normal.append(obj)
                            try:
                                data["old_age"]["data"][str(year)][str(item["xssj"][5:])].append(obj)
                            except:
                                data["old_age"]["data"][str(year)][str(item["xssj"][5:])] = [obj]
                        # else:
                        #     doubt.append(obj)
                        #     data["old_age"]["bizDoubtData"][str(year)][str(item["xssj"][5:])] = obj

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
                # 根据类型获取解析后的页面
                soup = self._unit_fetch_user_DETAILED("023", year)
                num = 0
                # 返回结果
                result = json.loads(str(soup))
                if result["code"] == '1':
                    data["medical_care"]["data"][str(year)] = {}

                    isStart = True
                    # 循环行
                    for item in result["result"]:
                        # 个人缴费金额
                        grjfje = item.get('grjfje', '0')
                        # 个人缴费累金额
                        self.my_self_medical_care = self.my_self_medical_care + float(grjfje)
                        # 定义数据结构
                        obj = {
                            "year": year,
                            "data": {
                                "缴费时间": item["xssj"],
                                "缴费类型": item["jflx"],
                                "缴费基数": item["jfjs"],
                                "公司缴费": "-",
                                "个人缴费": grjfje,
                                "缴费单位": item["dwmc"],
                            }
                        }

                        if item["fkkm"] == "基本医疗保险" and item["jfbz"] == "已实缴":
                            if nowTime == year and isStart:
                                self.medical_care_lately_data = item["xssj"].replace("-", "")
                                isStart = False
                            # 累计正常缴费的缴费月数
                            self.medical_care_month = self.medical_care_month + 1
                            # 苏州目前账号来看每个月只会生成一条数据，
                            # normal.append(obj)
                            try:
                                data["medical_care"]["data"][str(year)][str(item["xssj"][5:])].append(obj)
                            except:
                                data["medical_care"]["data"][str(year)][str(item["xssj"][5:])] = [obj]
                        elif item["fkkm"] == "大额医疗保险" and item["jfbz"] == "已实缴":
                            try:
                                data["medical_care"]["data"][str(year)][str(item["xssj"][5:])].append(obj)
                            except:
                                data["medical_care"]["data"][str(year)][str(item["xssj"][5:])] = [obj]

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
                # 根据类型获取解析后的页面
                soup = self._unit_fetch_user_DETAILED("052", year)
                num = 0
                # 返回结果
                result = json.loads(str(soup))
                if result["code"] == '1':
                    data["injuries"]["data"][str(year)] = {}

                    isStart = True
                    # 循环行
                    for item in result["result"]:
                        # 个人缴费金额
                        grjfje = item.get('grjfje', '0')
                        # 定义数据结构
                        obj = {
                            "year": year,
                            "data": {
                                "缴费时间": item["xssj"],
                                "缴费类型": item["jflx"],
                                "缴费基数": item["jfjs"],
                                "公司缴费": "-",
                                "个人缴费": "-",
                                "缴费单位": item["dwmc"],
                            }
                        }

                        if item["jfbj"] == "足额缴费":
                            if nowTime == year and isStart:
                                self.injuries_lately_data = item["xssj"].replace("-", "")
                                isStart = False
                            # 累计正常缴费的缴费月数
                            self.injuries_month = self.injuries_month + 1
                            # 苏州目前账号来看每个月只会生成一条数据，
                            # normal.append(obj)
                            try:
                                data["injuries"]["data"][str(year)][str(item["xssj"][5:])].append(obj)
                            except:
                                data["injuries"]["data"][str(year)][str(item["xssj"][5:])] = [obj]
                            # else:
                            #     doubt.append(obj)
                            #     data["injuries"]["bizDoubtData"][str(year)][str(item["xssj"][5:])] = obj

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
                # 根据类型获取解析后的页面
                soup = self._unit_fetch_user_DETAILED("062", year)
                num = 0
                # 返回结果
                result = json.loads(str(soup))
                if result["code"] == '1':
                    data["maternity"]["data"][str(year)] = {}
                    isStart = True
                    # 循环行
                    for item in result["result"]:
                        # 个人缴费金额
                        grjfje = item.get('grjfje', '0')
                        # 定义数据结构
                        obj = {
                            "year": year,
                            "data": {
                                "缴费时间": item["xssj"],
                                "缴费类型": item["jflx"],
                                "缴费基数": item["jfjs"],
                                "公司缴费": "-",
                                "个人缴费": "-",
                                "缴费单位": item["dwmc"],
                            }
                        }

                        if item["jfbj"] == "已实缴":
                            if nowTime == year and isStart:
                                self.maternity_lately_data = item["xssj"].replace("-", "")
                                isStart = False
                            # 累计正常缴费的缴费月数
                            self.maternity_month = self.maternity_month + 1
                            # 苏州目前账号来看每个月只会生成一条数据，
                            # normal.append(obj)
                            try:
                                data["maternity"]["data"][str(year)][str(item["xssj"][5:])].append(obj)
                            except:
                                data["maternity"]["data"][str(year)][str(item["xssj"][5:])] = [obj]
                            # else:
                            #     doubt.append(obj)
                            #     data["maternity"]["bizDoubtData"][str(year)][str(item["xssj"][5:])] = obj

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
                # 根据类型获取解析后的页面
                soup = self._unit_fetch_user_DETAILED("043", year)
                num = 0
                # 返回结果
                result = json.loads(str(soup))
                if result["code"] == '1':
                    data["unemployment"]["data"][str(year)] = {}
                    isStart = True
                    # 循环行
                    for item in result["result"]:
                        # 个人缴费金额
                        grjfje = item.get('grjfje', '0')
                        # 定义数据结构
                        obj = {
                            "year": year,
                            "data": {
                                "缴费时间": item["xssj"],
                                "缴费类型": item["jflx"],
                                "缴费基数": item["jfjs"],
                                "公司缴费": "-",
                                "个人缴费": "-",
                                "缴费单位": item["dwmc"],
                            }
                        }

                        if item["jfbj"] == "足额缴费":
                            if nowTime == year and isStart:
                                self.unemployment_lately_data = item["xssj"].replace("-", "")
                                isStart = False
                            # 累计正常缴费的缴费月数
                            self.unemployment_month = self.unemployment_month + 1
                            # 苏州目前账号来看每个月只会生成一条数据，
                            # normal.append(obj)
                            try:
                                data["unemployment"]["data"][str(year)][str(item["xssj"][5:])].append(obj)
                            except:
                                data["unemployment"]["data"][str(year)][str(item["xssj"][5:])] = [obj]
                            # else:
                            #     doubt.append(obj)
                            #     data["unemployment"]["bizDoubtData"][str(year)][str(item["xssj"][5:])] = obj

        except Exception as e:
            raise PreconditionNotSatisfiedError(e)

    # 缴费明细main方法
    def _unit_get_payment_details(self):
        try:
            # 五险开始缴费时间
            latest_start_time = [self.old_age_lately_start_data,
                                 self.medical_care_lately_start_data,
                                 self.injuries_lately_start_data,
                                 self.maternity_lately_start_data,
                                 self.unemployment_lately_start_data]

            data = self.result['data']
            # 养老明细
            self._unit_fetch_user_old_age(min(latest_start_time)[0:4])
            # 医疗明细
            self._unit_fetch_user_medical_care(min(latest_start_time)[0:4])
            # 工伤明细
            self._unit_fetch_user_injuries(min(latest_start_time)[0:4])
            # 生育明细
            self._unit_fetch_user_maternity(min(latest_start_time)[0:4])
            # 失业明细
            self._unit_fetch_user_unemployment(min(latest_start_time)[0:4])

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
            data["baseInfo"]["开始缴费时间"] = str(min(latest_start_time))
            data["baseInfo"]["个人养老累计缴费"] = str(self.my_self_old_age)
            data["baseInfo"]["个人医疗累计缴费"] = str(self.my_self_medical_care)

        except Exception as e:
            raise PreconditionNotSatisfiedError(e)

    # 刷新验证码
    def _new_vc(self):
        resp = self.s.get(VC_URL)
        return dict(cls="data:image", content=resp.content)


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()
