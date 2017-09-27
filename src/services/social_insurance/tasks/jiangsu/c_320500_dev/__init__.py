import time
import json
import datetime
import requests
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask
LOGIN_URL = 'http://szsbzx.jsszhrss.gov.cn:9900/web/website/indexProcess?frameControlSubmitFunction=checkLogin'
VC_URL = 'http://szsbzx.jsszhrss.gov.cn:9900/web/website/rand.action?r='
USER_INFO_URL = "http://szsbzx.jsszhrss.gov.cn:9900/web/website/personQuery/personQueryAction.action"
DETAILED_LIST_URL = "http://szsbzx.jsszhrss.gov.cn:9900/web/website/personQuery/personQueryAction?frameControlSubmitFunction=getPagesAjax"


class Task(AbsFetchTask):
    task_info = dict(
        city_name="苏州",
        help="""<li>个人编号长度为10位，参保地为市本级、姑苏区（原沧浪区、平江区、金阊区）、高新区，不足部分前面“00”补足；参保地为吴中区，不足部分前面“02”补足；参保地为相城区，不足部分前面“03”补足。</li>
            <li>如有问题请拨打12333。</li>"""
    )
    def _get_common_headers(self):
        return { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36'}


    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_user_info, self._unit_login)
        self._add_unit(self._unit_get_payment_details, self._unit_login)


    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '身份证号' in params, '缺少身份证号'
        assert '个人编号' in params, '缺少个人编号'
        assert 'vc' in params, '缺少验证码'
        # other check
    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '身份证号' not in params:
                params['身份证号'] = meta.get('身份证号')
            if '个人编号' not in params:
                params['个人编号'] = meta.get('个人编号')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '身份证号' and '身份证号' in meta:
                continue
            elif pr['key'] == '个人编号' and '个人编号' in meta:
                continue
            res.append(pr)
        return res

    def _unit_login(self, params=None):
        err_msg = None
        if params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params['身份证号']
                account_num = params['个人编号']
                vc = params['vc']

                if account_num.__len__() != 10:
                    raise Exception("请录入10位个人编号")

                resp = self.s.post(LOGIN_URL, data=dict(
                    sfzh=id_num,
                    grbh=account_num,
                    yzcode=vc
                ))
                data = resp.json()
                errormsg = data.get('errormsg')
                if errormsg:
                    raise Exception(errormsg)

                self.result_key = id_num
                # 保存到meta
                self.result_meta ['身份证编号']= id_num
                self.result_meta['个人编号']=  account_num

                self.result_identity['task_name'] = '苏州'
                self.result_identity['target_id'] = id_num

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input'),
            dict(key='个人编号', name='个人编号', cls='input'),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'})
        ], err_msg)

    # 获取用户基本信息
    def _unit_fetch_user_info(self):
        try:
            data = self.result_data
            resp = self.s.post(USER_INFO_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            div_table = soup.find('input', {'name': 'psMsgBar'}).attrs['value']
            name = div_table.split('td')[7][1:-2]
            personNum = self.result_meta["个人编号"]
            sfzNum = self.result_meta["身份证编号"]

            data["baseInfo"] = {
                "姓名": name,
                "社保编号": personNum,
                "身份证号": sfzNum,
                "更新时间": datetime.datetime.now().strftime('%Y-%m-%d'),
                '城市名称': '苏州',
                '城市编号': '320500',
                '缴费时长': '',
                '最近缴费时间': '',
                '开始缴费时间': '',
                '个人养老累计缴费': '',
                '个人医疗累计缴费': ''
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

            # 设置identity
            self.result_identity['target_name'] = name
            self.result_identity['status']=''
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    # 获取用户明细
    def _unit_fetch_user_DETAILED(self, bizType):
        try:
            resp = self.s.post(DETAILED_LIST_URL, data={
                'xz': bizType,
                'pageIndex': 1,
                'pageCount': 99999999
            })
            soup = BeautifulSoup(json.loads(str(resp.content, 'utf-8'))["pagelistajax"], "html.parser")
            return soup
        except Exception as e:
            raise PreconditionNotSatisfiedError(e)

    # 养老
    def _unit_fetch_user_old_age(self):
        data = self.result_data
        # 统计养老实际缴费月数
        self.old_age_month = 0
        # 统计个人缴费养老金额
        self.my_self_old_age = 0
        # 最近参保时间
        self.old_age_lately_data = '199201'
        # 开始参保时间
        self.old_age_lately_start_data = '199201'

        try:
            # 根据类型获取解析后的页面
            soup = self._unit_fetch_user_DETAILED('qyylmx')
            # 拿table中的tr进行循环
            trs = soup.findAll('tr')

            # 从数据集获取年份集合
            years = []
            # 补缴费用明细数据集合
            doubt = []
            # 正常缴费明细数据集合
            normal = []

            num = 0
            # 循环行
            for tr in trs:
                num = num + 1
                if trs[0] == tr:
                    continue
                # 查找该行所有td
                tds = tr.findAll('td')
                try:
                    # 需要爬取的数据id从1开始
                    if int(tds[0].text.strip()) > 0:
                        # 获取当前年份
                        year = tds[0].text[0:4]
                        # 获取当前月份
                        month = tds[0].text[0:4] + "-" + tds[0].text[4:6]
                        # 正常年份累计到年份数据源中
                        if year not in years:
                            years.append(year)

                        # 获取表单的第一个时间为最新缴费时间
                        if num == 2:
                            self.old_age_lately_data = tds[0].text
                        # 获取最早参保时间
                        if trs.__len__() == num:
                            self.old_age_lately_start_data = tds[0].text
                        # 个人缴费累金额
                        self.my_self_old_age = self.my_self_old_age + float(tds[3].text.strip())

                        # 定义数据结构
                        obj = {
                            "year": year,
                            "data": {
                                "缴费时间": month,
                                "缴费类型": tds[6].text.strip(),
                                "缴费基数": tds[4].text.strip(),
                                "公司缴费": tds[2].text.strip(),
                                "个人缴费": tds[3].text.strip(),
                                "缴费单位": tds[1].text.strip(),
                            }
                        }
                        # 累计正常缴费的缴费月数
                        self.old_age_month = self.old_age_month + 1
                        # 苏州目前账号来看每个月只会生成一条数据，
                        normal.append(obj)
                        # # 正常应缴有与补缴进行分区存储
                        # if tds[6].text.strip() == '正常应缴':
                        #     normal.append(obj)
                        # else:
                        #     doubt.append(obj)
                except Exception as e:
                    raise PreconditionNotSatisfiedError(e)

            for year in years:
                # 正常费用明细数据集合(临时)
                tempNormal = []
                for items in normal:
                    if items["year"] == year:
                        tempNormal.append(items["data"])
                    else:
                        continue
                if tempNormal.__len__() > 0:
                    data["old_age"]["data"][str(year)] = {}
                    for item in tempNormal:
                        try:
                            data["old_age"]["data"][str(year)][str(item["缴费时间"][5:])].append(item)
                        except:
                            data["old_age"]["data"][str(year)][str(item["缴费时间"][5:])] = [item]

            if doubt.__len__() > 0:
                for year in years:
                    # 补缴费用明细数据集合(临时)
                    tempDoubt = []
                    for items in doubt:
                        if items["year"] == year:
                            tempDoubt.append(items["data"])
                        else:
                            continue
                    if tempDoubt.__len__() > 0:
                        data["old_age"]["data"][str(year)] = {}
                        data["old_age"]["data"][str(year)] = {}
                        for item in tempDoubt:
                            try:
                                data["old_age"]["data"][str(year)][str(item["缴费时间"][5:])].append(item)
                            except:
                                data["old_age"]["data"][str(year)][str(item["缴费时间"][5:])] = [item]
        except Exception as e:
            raise PreconditionNotSatisfiedError(e)

    # 医疗
    def _unit_fetch_user_medical_care(self):
        data = self.result['data']
        # 统计医疗实际缴费月数
        self.medical_care_month = 0
        # 统计个人缴费医疗金额
        self.my_self_medical_care = 0
        # 最近参保时间
        self.medical_care_lately_data = '199201'
        # 最早参保时间
        self.medical_care_lately_start_data = '199201'

        try:
            # 根据类型获取解析后的页面
            soup = self._unit_fetch_user_DETAILED('ylbx')
            # 拿table中的tr进行循环
            trs = soup.findAll('tr')

            # 从数据集获取年份集合
            years = []
            # 补缴费用明细数据集合
            doubt = []
            # 正常缴费明细数据集合
            normal = []

            num = 0
            # 循环行
            for tr in trs:
                num = num + 1
                if trs[0] == tr:
                    continue
                # 查找该行所有td
                tds = tr.findAll('td')
                try:
                    # 需要爬取的数据id从1开始
                    if int(tds[0].text.strip()) > 0:
                        # 获取当前年份
                        year = tds[0].text[0:4]
                        # 获取当前月份
                        month = tds[0].text[0:4] + "-" + tds[0].text[4:6]
                        # 正常年份累计到年份数据源中
                        if year not in years:
                            years.append(year)

                        # 获取表单的第一个时间为最新缴费时间
                        if num == 2:
                            self.medical_care_lately_data = tds[0].text
                        # 获取最早参保时间
                        if trs.__len__() == num:
                            self.medical_care_lately_start_data = tds[0].text
                        # 个人缴费累金额
                        self.my_self_medical_care = self.my_self_medical_care + float(tds[3].text.strip())

                        # 定义数据结构
                        obj = {
                            "year": year,
                            "data":{
                                "缴费时间": month,
                                "缴费类型": tds[7].text.strip(),
                                "缴费基数": tds[2].text.strip(),
                                "公司缴费": tds[4].text.strip(),
                                "个人缴费": tds[3].text.strip(),
                                "缴费单位": tds[1].text.strip(),
                            }
                        }
                        # 累计正常缴费的缴费月数
                        self.medical_care_month = self.medical_care_month + 1

                        # 苏州目前账号来看，每个月只能生成一条数据
                        normal.append(obj)
                        # # 正常应缴有与补缴进行分区存储
                        # if tds[7].text.strip() == '已到账':
                        #     normal.append(obj)
                        # else:
                        #     doubt.append(obj)
                except Exception as e:
                    raise PreconditionNotSatisfiedError(e)

            for year in years:
                # 正常费用明细数据集合(临时)
                tempNormal = []
                for items in normal:
                    if items["year"] == year:
                        tempNormal.append(items["data"])
                    else:
                        continue
                if tempNormal.__len__() > 0:
                    tempNormal.reverse()
                    data["medical_care"]["data"][str(year)] = {}
                    for item in tempNormal:
                        try:
                            data["medical_care"]["data"][str(year)][str(item["缴费时间"][5:])].append(item)
                        except:
                            data["medical_care"]["data"][str(year)][str(item["缴费时间"][5:])] = [item]

            if doubt.__len__() > 0:
                for year in years:
                    # 补缴费用明细数据集合(临时)
                    tempDoubt = []
                    for items in doubt:
                        if items["year"] == year:
                            tempDoubt.append(items["data"])
                        else:
                            continue
                    if tempDoubt.__len__() > 0:
                        tempDoubt.reverse()
                        data["medical_care"]["data"][str(year)] = {}
                        for item in tempNormal:
                            try:
                                data["medical_care"]["data"][str(year)][str(item["缴费时间"][5:])].append(item)
                            except:
                                data["medical_care"]["data"][str(year)][str(item["缴费时间"][5:])] = [item]
        except Exception as e:
            raise PreconditionNotSatisfiedError(e)

    # 工伤
    def _unit_fetch_user_injuries(self):
        data = self.result['data']
        # 统计医疗实际缴费月数
        self.injuries_month = 0
        # 最近参保时间
        self.injuries_lately_data = '199201'
        # 最早参保时间
        self.injuries_lately_start_data = '199201'

        try:
            # 根据类型获取解析后的页面
            soup = self._unit_fetch_user_DETAILED('gsbx')
            # 拿table中的tr进行循环
            trs = soup.findAll('tr')

            # 从数据集获取年份集合
            years = []
            # 补缴费用明细数据集合
            doubt = []
            # 正常缴费明细数据集合
            normal = []
            # 补缴费用明细数据集合(返回值)

            num = 0
            # 循环行
            for tr in trs:
                num = num + 1
                if trs[0] == tr:
                    continue
                # 查找该行所有td
                tds = tr.findAll('td')
                try:
                    # 需要爬取的数据id从1开始
                    if int(tds[0].text.strip()) > 0:
                        # 获取当前年份
                        year = tds[0].text[0:4]
                        # 获取当前月份
                        month = tds[0].text[0:4] + "-" + tds[0].text[4:6]
                        # 正常年份累计到年份数据源中
                        if year not in years:
                            years.append(year)

                        # 获取表单的第一个时间为最新缴费时间
                        if num == 2:
                            self.injuries_lately_data = tds[0].text
                        # 获取最早参保时间
                        if trs.__len__() == num:
                            self.injuries_lately_start_data = tds[0].text
                        # 定义数据结构
                        obj = {
                            "year": year,
                            "data": {
                                "缴费时间": month,
                                "缴费类型": tds[4].text.strip(),
                                "缴费基数": tds[2].text.strip(),
                                "公司缴费": '-',
                                "个人缴费": '-',
                                "缴费单位": tds[1].text.strip(),
                            }
                        }
                        # 累计正常缴费的缴费月数
                        self.injuries_month = self.injuries_month + 1
                        # 目前苏州账号每个月只能有一条数据
                        normal.append(obj)
                        # 正常应缴有与补缴进行分区存储
                        # if tds[4].text.strip() == '已到账':
                        #     normal.append(obj)
                        # else:
                        #     doubt.append(obj)
                except Exception as e:
                    raise PreconditionNotSatisfiedError(e)

            for year in years:
                # 正常费用明细数据集合(临时)
                tempNormal = []
                for items in normal:
                    if items["year"] == year:
                        tempNormal.append(items["data"])
                    else:
                        continue
                if tempNormal.__len__() > 0:
                    data["injuries"]["data"][str(year)] = {}
                    for item in tempNormal:
                        try:
                            data["injuries"]["data"][str(year)][str(item["缴费时间"][5:])].append(item)
                        except:
                            data["injuries"]["data"][str(year)][str(item["缴费时间"][5:])] = [item]

            if doubt.__len__() > 0:
                for year in years:
                    # 补缴费用明细数据集合(临时)
                    tempDoubt = []
                    for items in doubt:
                        if items["year"] == year:
                            tempDoubt.append(items["data"])
                        else:
                            continue
                    if tempDoubt.__len__() > 0:
                        data["injuries"]["data"][str(year)] = {}
                        for item in tempNormal:
                            try:
                                data["injuries"]["data"][str(year)][str(item["缴费时间"][5:])].append(item)
                            except:
                                data["injuries"]["data"][str(year)][str(item["缴费时间"][5:])] = [item]
        except Exception as e:
            raise PreconditionNotSatisfiedError(e)

    # 生育
    def _unit_fetch_user_maternity(self):
        data = self.result['data']
        # 统计生育实际缴费月数
        self.maternity_month = 0
        # 最近参保时间
        self.maternity_lately_data = '199201'
        # 最早参保时间
        self.maternity_lately_start_data = '199201'

        try:
            # 根据类型获取解析后的页面
            soup = self._unit_fetch_user_DETAILED('sybx')
            # 拿table中的tr进行循环
            trs = soup.findAll('tr')

            # 从数据集获取年份集合
            years = []
            # 补缴费用明细数据集合
            doubt = []
            # 正常缴费明细数据集合
            normal = []

            num = 0
            # 循环行
            for tr in trs:
                num = num + 1
                if trs[0] == tr:
                    continue
                # 查找该行所有td
                tds = tr.findAll('td')
                try:
                    # 需要爬取的数据id从1开始
                    if int(tds[0].text.strip()) > 0:
                        # 获取当前年份
                        year = tds[0].text[0:4]
                        # 获取当前月份
                        month = tds[0].text[0:4] + "-" + tds[0].text[4:6]
                        # 正常年份累计到年份数据源中
                        if year not in years:
                            years.append(year)

                        # 获取表单的第一个时间为最新缴费时间
                        if num == 2:
                            self.maternity_lately_data = tds[0].text
                        # 获取最早参保时间
                        if trs.__len__() == num:
                            self.maternity_lately_start_data = tds[0].text
                        # 定义数据结构
                        obj = {
                            "year": year,
                            "data": {
                                "缴费时间": month,
                                "缴费类型": tds[4].text.strip(),
                                "缴费基数": tds[2].text.strip(),
                                "公司缴费": '-',
                                "个人缴费": '-',
                                "缴费单位": tds[1].text.strip(),
                            }
                        }
                        # 累计正常缴费的缴费月数
                        self.maternity_month = self.maternity_month + 1
                        # 目前苏州每个月只有一条数据
                        normal.append(obj)
                        # 正常应缴有与补缴进行分区存储
                        # if tds[4].text.strip() == '已到账':
                        #     normal.append(obj)
                        # else:
                        #     doubt.append(obj)
                except Exception as e:
                    raise PreconditionNotSatisfiedError(e)

            for year in years:
                # 正常费用明细数据集合(临时)
                tempNormal = []
                for items in normal:
                    if items["year"] == year:
                        tempNormal.append(items["data"])
                    else:
                        continue
                if tempNormal.__len__() > 0:
                    tempNormal.reverse()
                    data["maternity"]["data"][str(year)] = {}
                    for item in tempNormal:
                        try:
                            data["maternity"]["data"][str(year)][str(item["缴费时间"][5:])].append(item)
                        except:
                            data["maternity"]["data"][str(year)][str(item["缴费时间"][5:])] = [item]
            if doubt.__len__() > 0:
                for year in years:
                    # 补缴费用明细数据集合(临时)
                    tempDoubt = []
                    for items in doubt:
                        if items["year"] == year:
                            tempDoubt.append(items["data"])
                        else:
                            continue
                    if tempDoubt.__len__() > 0:
                        tempDoubt.reverse()
                        data["maternity"]["data"][str(year)] = {}
                        for item in tempNormal:
                            try:
                                data["maternity"]["data"][str(year)][str(item["缴费时间"][5:])].append(item)
                            except:
                                data["maternity"]["data"][str(year)][str(item["缴费时间"][5:])] = [item]
        except Exception as e:
            raise PreconditionNotSatisfiedError(e)

    # 失业
    def _unit_fetch_user_unemployment(self):
        data = self.result['data']
        # 统计失业实际缴费月数
        self.unemployment_month = 0
        # 最近参保时间
        self.unemployment_lately_data = '199201'
        # 最早参保时间
        self.unemployment_lately_start_data = '199201'

        try:
            # 根据类型获取解析后的页面
            soup = self._unit_fetch_user_DETAILED('shiyebx')
            # 拿table中的tr进行循环
            trs = soup.findAll('tr')

            # 从数据集获取年份集合
            years = []
            # 补缴费用明细数据集合
            doubt = []
            # 正常缴费明细数据集合
            normal = []

            num = 0
            # 循环行
            for tr in trs:
                num = num + 1
                if trs[0] == tr:
                    continue
                # 查找该行所有td
                tds = tr.findAll('td')
                try:
                    # 需要爬取的数据id从1开始
                    if int(tds[0].text.strip()) > 0:
                        # 获取当前年份
                        year = tds[0].text[0:4]
                        # 获取当前月份
                        month = tds[0].text[0:4] + "-" + tds[0].text[4:6]
                        # 正常年份累计到年份数据源中
                        if year not in years:
                            years.append(year)

                        # 获取表单的第一个时间为最新缴费时间
                        if num == 2:
                            self.unemployment_lately_data = tds[0].text
                        # 获取最早参保时间
                        if trs.__len__() == num:
                            self.unemployment_lately_start_data = tds[0].text
                        # 定义数据结构
                        obj = {
                            "year": year,
                            "data": {
                                "缴费时间": month,
                                "缴费类型": tds[4].text.strip(),
                                "缴费基数": tds[2].text.strip(),
                                "公司缴费": '-',
                                "个人缴费": '-',
                                "缴费单位": tds[1].text.strip(),
                            }
                        }
                        # 累计正常缴费的缴费月数
                        self.unemployment_month = self.unemployment_month + 1
                        # 正常应缴有与补缴进行分区存储
                        if tds[4].text.strip() == '已到账':
                            normal.append(obj)
                        else:
                            doubt.append(obj)
                except Exception as e:
                    raise PreconditionNotSatisfiedError(e)

            for year in years:
                # 正常费用明细数据集合(临时)
                tempNormal = []
                for items in normal:
                    if items["year"] == year:
                        tempNormal.append(items["data"])
                    else:
                        continue
                if tempNormal.__len__() > 0:
                    tempNormal.reverse()
                    data["unemployment"]["data"][str(year)] = {}
                    for item in tempNormal:
                        try:
                            data["unemployment"]["data"][str(year)][str(item["缴费时间"][5:])].append(item)
                        except:
                            data["unemployment"]["data"][str(year)][str(item["缴费时间"][5:])] = [item]

            if doubt.__len__() > 0:
                for year in years:
                    # 补缴费用明细数据集合(临时)
                    tempDoubt = []
                    for items in doubt:
                        if items["year"] == year:
                            tempDoubt.append(items["data"])
                        else:
                            continue
                    if tempDoubt.__len__() > 0:
                        tempDoubt.reverse()
                        data["unemployment"]["data"][str(year)] = {}
                        for item in tempNormal:
                            try:
                                data["unemployment"]["data"][str(year)][str(item["缴费时间"][5:])].append(item)
                            except:
                                data["unemployment"]["data"][str(year)][str(item["缴费时间"][5:])] = [item]
        except Exception as e:
            raise PreconditionNotSatisfiedError(e)

    # 缴费明细main方法
    def _unit_get_payment_details(self):
        try:
            data = self.result['data']
            # 养老明细
            self._unit_fetch_user_old_age()
            # 医疗明细
            self._unit_fetch_user_medical_care()
            # 工伤明细
            self._unit_fetch_user_injuries()
            # 生育明细
            self._unit_fetch_user_maternity()
            # 失业明细
            self._unit_fetch_user_unemployment()

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

            # 五险开始缴费时间
            latest_start_time = [self.old_age_lately_start_data.strip(),
                                 self.medical_care_lately_start_data.strip(),
                                 self.injuries_lately_start_data.strip(),
                                 self.maternity_lately_start_data.strip(),
                                 self.unemployment_lately_start_data.strip()]

            data["baseInfo"]["缴费时长"] = str(max(social_payment_duration))
            data["baseInfo"]["最近缴费时间"] = str(max(latest_time))
            data["baseInfo"]["开始缴费时间"] = str(min(latest_start_time))
            data["baseInfo"]["个人养老累计缴费"] = str(self.my_self_old_age)
            data["baseInfo"]["个人医疗累计缴费"] = str(self.my_self_medical_care)

        except Exception as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        vc_url = VC_URL + str(int(time.time() * 1000))
        resp = self.s.get(vc_url)
        return dict(cls="data:image", content=resp.content, content_type=resp.headers['Content-Type'])


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()
