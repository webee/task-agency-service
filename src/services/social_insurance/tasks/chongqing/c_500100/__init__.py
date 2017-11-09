import time
import json
import datetime
import base64
from bs4 import BeautifulSoup
from services.service import AskForParamsError, PreconditionNotSatisfiedError
from services.errors import InvalidParamsError, InvalidConditionError
from services.commons import AbsFetchTask

LOGIN_URL = 'http://ggfw.cqhrss.gov.cn/ggfw/LoginBLH_login.do'
VC_URL = 'http://ggfw.cqhrss.gov.cn/ggfw/validateCodeBLH_image.do'
USER_INFO_URL = "http://ggfw.cqhrss.gov.cn/ggfw/QueryBLH_main.do?code=888"
DETAILED_LIST_URL = "http://ggfw.cqhrss.gov.cn/ggfw/QueryBLH_query.do"


class Task(AbsFetchTask):
    task_info = dict(
        city_name="重庆",
        expect_time=30,
        help="""<li>初始查询密码为社会保障卡卡号的后6位</li>
        <li>如果你的个人查询密码忘记，请到社保卡业务经办机构进行密码重置</li>
        <li>数据解析需要较长的时间，请耐心等待</li>
        """
    )

    @classmethod
    def inspect(cls, params: dict):
        t = params.get('t')
        if t == 'city_name':
            return cls.task_info.get('city_name')
        return super().inspect(params)

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36'
        }

    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_user_info, self._unit_login)
        self._add_unit(self._unit_get_payment_details, self._unit_login)

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if 'sfzh' not in params:
                params['sfzh'] = meta.get('身份证编号')
            if 'password' not in params:
                params['password'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == 'sfzh' and '身份证编号' in meta:
                continue
            elif pr['key'] == 'password' and '密码' in meta:
                continue
            res.append(pr)
        return res

    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert 'sfzh' in params, '缺少身份证号'
        assert 'password' in params, '缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check

    def _unit_login(self, params=None):
        err_msg = None
        if params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                sfzh = params['sfzh']
                password = base64.b64encode(params['password'].encode(encoding="utf-8"))
                vc = params['vc']

                resp = self.s.post(LOGIN_URL, data=dict(
                    sfzh=sfzh,
                    password=password,
                    validateCode=vc
                ))
                data = resp.json()
                errormsg = data.get('message')
                if data.get('code') == '0':
                    raise InvalidParamsError(errormsg)

                self.result_key = sfzh
                self.result_meta.update({
                    '身份证编号': sfzh,
                    '密码': params['password']
                })
                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='sfzh', name='身份证号', cls='input', value=params.get('sfzh', '')),
            dict(key='password', name='密码', cls='input:password', value=params.get('password', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}, value=params.get('vc', '')),
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
            old_age_state = None
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
                    self.old_age_lately_start_data = tds[7].text.strip()
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
                "社会保障号": personNum,
                "性别": sex,
                "民族": mz,
                "出生日期": birthDay,
                "组织机构代码": CompanyCode,
                "户口性质": hkxz,
                "个人身份": sf,
                "单位名称": Company,
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

            # 设置identity
            identity = self.result['identity']
            identity.update({
                'task_name': '重庆市',
                'target_name': name,
                'target_id': self.result['meta']["身份证编号"],
                'status': "",
            })

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

            self.old_age_month = 0
            self.medical_care_month = 0
            self.injuries_month = 0
            self.maternity_month = 0
            self.unemployment_month = 0

            nowTime = time.strftime('%Y%m', time.localtime(time.time()))

            self.old_age_lately_data = nowTime
            self.medical_care_lately_data = nowTime
            self.injuries_lately_data = nowTime
            self.maternity_lately_data = nowTime
            self.unemployment_lately_data = nowTime

            self.my_self_old_age = 0
            self.my_self_medical_care = 0

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    # 获取用户明细
    def _unit_fetch_user_DETAILED(self, bizType, year):
        try:
            resp = self.s.post(DETAILED_LIST_URL, data={
                'code': bizType,
                'year': year,
                'pageSize': 200
            })
            return resp.content
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

        isStart = True
        try:
            nowTime = int(time.strftime('%Y', time.localtime(time.time())))
            for year in range(nowTime, int(start_job)-1, -1):
                time.sleep(0.8)
                # 根据类型获取解析后的页面
                content = self._unit_fetch_user_DETAILED("015", year)
                # 返回结果
                result = json.loads(content)
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
                            "缴费时间": item.get('xssj', ''),
                            "缴费类型": item.get('jflx', ''),
                            "缴费基数": item.get('jfjs', ''),
                            "公司缴费": "",
                            "个人缴费": item.get('grjfje', ''),
                            "缴费单位": item.get('dwmc', ''),
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
                time.sleep(0.8)
                # 根据类型获取解析后的页面
                content = self._unit_fetch_user_DETAILED("023", year)
                # 返回结果
                result = json.loads(content)
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
                           "缴费时间": item.get("xssj", ''),
                           "缴费类型": item.get("jflx", ''),
                           "缴费基数": item.get("jfjs", ''),
                           "公司缴费": '',
                           "个人缴费": item.get('grjfje', ''),
                           "缴费单位": item.get("dwmc", ''),
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
                time.sleep(0.8)
                # 根据类型获取解析后的页面
                content = self._unit_fetch_user_DETAILED("052", year)
                # 返回结果
                result = json.loads(content)
                if result["code"] == '1':
                    data["injuries"]["data"][str(year)] = {}

                    isStart = True
                    # 循环行
                    for item in result["result"]:
                        # 定义数据结构
                        obj = {
                           "缴费时间": item.get("xssj", ''),
                           "缴费类型": item.get("jflx", ''),
                           "缴费基数": item.get("jfjs", ''),
                           "公司缴费": '',
                           "个人缴费": item.get('grjfje', ''),
                           "缴费单位": item.get("dwmc", ''),
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
                time.sleep(0.8)
                # 根据类型获取解析后的页面
                content = self._unit_fetch_user_DETAILED("062", year)
                # 返回结果
                result = json.loads(content)
                if result["code"] == '1':
                    data["maternity"]["data"][str(year)] = {}
                    isStart = True
                    # 循环行
                    for item in result["result"]:
                        # 定义数据结构
                        obj = {
                           "缴费时间": item.get("xssj", ''),
                           "缴费类型": item.get("jflx", ''),
                           "缴费基数": item.get("jfjs", ''),
                           "公司缴费": '',
                           "个人缴费": item.get('grjfje', ''),
                           "缴费单位": item.get("dwmc", ''),
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
                time.sleep(0.8)
                # 根据类型获取解析后的页面
                content = self._unit_fetch_user_DETAILED("043", year)
                # 返回结果
                result = json.loads(content)
                if result["code"] == '1':
                    data["unemployment"]["data"][str(year)] = {}
                    isStart = True
                    # 循环行
                    for item in result["result"]:
                        # 定义数据结构
                        obj = {
                           "缴费时间": item.get("xssj", ''),
                           "缴费类型": item.get("jflx", ''),
                           "缴费基数": item.get("jfjs", ''),
                           "公司缴费": '',
                           "个人缴费": item.get('grjfje', ''),
                           "缴费单位": item.get("dwmc", ''),
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

        except InvalidConditionError as e:
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

            temp_latest_start_time = []
            for item in latest_start_time:
                if item:
                    temp_latest_start_time.append(item)
            # 养老明细
            if self.old_age_lately_start_data:
                self._unit_fetch_user_old_age(min(temp_latest_start_time)[0:4])
            # 医疗明细
            if self.medical_care_lately_start_data:
                self._unit_fetch_user_medical_care(min(temp_latest_start_time)[0:4])
            # 工伤明细
            if self.injuries_lately_start_data:
                self._unit_fetch_user_injuries(min(temp_latest_start_time)[0:4])
            # 生育明细
            if self.maternity_lately_start_data:
                self._unit_fetch_user_maternity(min(temp_latest_start_time)[0:4])
            # 失业明细
            if self.unemployment_lately_start_data:
                self._unit_fetch_user_unemployment(min(temp_latest_start_time)[0:4])

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
            data["baseInfo"]["开始缴费时间"] = str(min(temp_latest_start_time))
            data["baseInfo"]["个人养老累计缴费"] = str(self.my_self_old_age)
            data["baseInfo"]["个人医疗累计缴费"] = str(self.my_self_medical_care)

        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    # 刷新验证码
    def _new_vc(self):
        resp = self.s.get(VC_URL)
        return dict(cls='data:image', content=resp.content, content_type=resp.headers.get('Content-Type'))


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()
