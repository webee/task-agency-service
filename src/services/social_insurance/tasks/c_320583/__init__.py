import time
import json
import datetime
import requests
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError

MAIN_URL = 'http://sbzx.ks.gov.cn:81/webPages/grjb.aspx'
LOGIN_URL = 'http://sbzx.ks.gov.cn:81/webPages/grxxcxdl.aspx'
USER_INFO_URL = "http://sbzx.ks.gov.cn:81/webPages/grjb.aspx"
DETAILED_LIST_URL = "http://sbzx.ks.gov.cn:81/webPages/"


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
        assert 'txtSocial' in params, '缺少社保编号'
        assert 'txtIdCard' in params, '缺少身份证号'
        # other check

    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                txtSocial = params['txtSocial']
                txtIdCard = params['txtIdCard']
                self.s = requests.Session()

                data = {
                    '__VIEWSTATE': '/wEPDwUKMTE5OTkyNjE3N2QYAQUeX19Db250cm9sc1JlcXVpcmVQb3N0QmFja0tleV9fFgEFDEltYWdlQnV0dG9uMawyoMUnhYzdZ/CYEuU6Zub34jdm',
                    '__EVENTVALIDATION': '/wEWBQKio5e8AQK4hdLODgLSwpnTCAKHvOeyCgKSoqqWD7P5DqrQCdEsyF4CuQgkhTVStKAL',
                    'txtSocial': txtSocial,
                    'txtIdCard': txtIdCard,
                    'btn': '登 录'
                }
                resp = self.s.post(LOGIN_URL, data=data)
                if resp.url != MAIN_URL:
                    raise Exception("登录失败！请重新登录")

                self.result['key'] = txtIdCard
                self.result['meta'] = {
                    '身份证编号': txtIdCard,
                    '社保编号': txtSocial
                }
                return
            except Exception as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='txtIdCard', name='身份证号', cls='input'),
            dict(key='txtSocial', name='社保编号', cls='input'),
            dict(key='cityCode', name='城市Code', cls='input:hidden', value='昆山市'),
            dict(key='cityName', name='城市名称', cls='input:hidden', value='320583')
        ], err_msg)

    # 获取用户基本信息
    def _unit_fetch_user_info(self):
        try:
            data = self.result['data']
            resp = self.s.post(USER_INFO_URL)
            soup = BeautifulSoup(str(resp.content, 'utf-8'), 'html.parser')
            result = soup.findAll('table')
            table = result[23]
            tds = table.findAll('td')

            data["baseInfo"] = {
                "姓名": tds[2].text,
                "社保编号": tds[4].text,
                "单位名称": tds[6].text,
                "出生年月": tds[8].text,
                "开始缴费时间": tds[10].text,
                "人员状态": tds[12].text,
                "身份证号": self.result['key'],
                "更新时间": datetime.datetime.now().strftime('%Y-%m-%d'),
                "城市名称": '昆山市',
                "城市编号": '320583',
                "缴费时长": '',
                "最近缴费时间": '',
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

    # 缴费明细渲染方法
    def _unit_fetch_user_DETAILED(self, url):
        try:
            resp = self.s.post(url)
            soup = BeautifulSoup(str(resp.content, 'utf-8'), "html.parser")
            return soup
        except Exception as e:
            raise PreconditionNotSatisfiedError(e)

    # 养老
    def _unit_fetch_user_old_age(self):
        data = self.result['data']
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
            soup = self._unit_fetch_user_DETAILED(DETAILED_LIST_URL + "yljf.aspx?pageIndex=1&id=" + data["baseInfo"]["社保编号"])
            # 获取指定div下table
            result = soup.find("div", {"id": "ctl00_ContentPlaceHolder1_showInfo"}).findAll("table")[0]
            # 拿table中的tr进行循环
            trs = result.findAll('tr')

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
                if trs[0] == tr or trs[1] == tr:
                    continue
                # 查找该行所有td
                tds = tr.findAll('td')
                try:
                    # 需要爬取的数据id从1开始
                    if int(tds[1].text.strip()) > 0:
                        # 获取当前年份
                        year = tds[1].text[0:4]
                        # 获取当前月份
                        month = tds[1].text[0:4] + "-" + tds[1].text[4:6]
                        # 正常年份累计到年份数据源中
                        if year not in years:
                            years.append(year)

                        # 获取表单的第一个时间为最新缴费时间
                        if num == 3:
                            self.old_age_lately_data = tds[1].text
                        # 获取最早参保时间
                        if trs.__len__() == num:
                            self.old_age_lately_start_data = tds[1].text
                        # 个人缴费累金额
                        self.my_self_old_age = self.my_self_old_age + float(tds[5].text.strip())

                        # 定义数据结构
                        obj = {
                            "year": year,
                            "data": {
                                "缴费时间": month,
                                "缴费类型": tds[2].text.strip(),
                                "缴费基数": tds[3].text.strip(),
                                "公司缴费": tds[4].next,
                                "个人缴费": tds[5].text.strip(),
                                "缴费单位": tds[6].text.strip(),
                            }
                        }

                        # 正常应缴有与补缴进行分区存储
                        if tds[8].text == '正常结算' or tds[8].text == '异地转入' or tds[8].text == '补缴结算':
                            # 累计正常缴费的缴费月数
                            self.old_age_month = self.old_age_month + 1
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
                    data["old_age"]["data"][str(year)] = {}
                    for month in tempNormal:
                        try:
                            data["old_age"]["data"][str(year)][str(month["缴费时间"][5:])].append(month)
                        except:
                            data["old_age"]["data"][str(year)][str(month["缴费时间"][5:])] = [month]

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
                        data["old_age"]["data"][str(year)] = {}
                        for month in tempDoubt:
                            try:
                                data["old_age"]["data"][str(year)][str(month["缴费时间"][5:])].append(month)
                            except:
                                data["old_age"]["data"][str(year)][str(month["缴费时间"][5:])] = [month]
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
            soup = self._unit_fetch_user_DETAILED(
                DETAILED_LIST_URL + "ybjf.aspx?pageIndex=1&type=yb&id=" + data["baseInfo"]["社保编号"])
            # 获取指定div下table
            result = soup.find("div", {"id": "ctl00_ContentPlaceHolder1_showInfo"}).findAll("table")[0]
            # 拿table中的tr进行循环
            trs = result.findAll('tr')

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
                if trs[0] == tr or trs[1] == tr:
                    continue
                # 查找该行所有td
                tds = tr.findAll('td')
                try:
                    # 需要爬取的数据id从1开始
                    if int(tds[1].text.strip()) > 0:
                        # 获取当前年份
                        year = tds[1].text[0:4]
                        # 获取当前月份
                        month = tds[1].text[0:4] + "-" + tds[1].text[4:6]
                        # 正常年份累计到年份数据源中
                        if year not in years:
                            years.append(year)

                        # 获取表单的第一个时间为最新缴费时间
                        if num == 3:
                            self.medical_care_lately_data = tds[1].text
                        # 获取最早参保时间
                        if trs.__len__() == num:
                            self.medical_care_lately_start_data = tds[1].text
                        # 个人缴费累金额
                        self.my_self_medical_care = self.my_self_medical_care + float(tds[5].text.strip())

                        # 定义数据结构
                        obj = {
                            "year": year,
                            "data": {
                                "缴费时间": month,
                                "缴费类型": tds[2].text.strip(),
                                "缴费基数": tds[3].text.strip(),
                                "公司缴费": tds[4].text.strip(),
                                "个人缴费": tds[5].text.strip(),
                                "缴费单位": '-',
                            }
                        }

                        # 正常应缴有与补缴进行分区存储
                        if tds[2].text.strip() == '基本医疗':
                            # 累计正常缴费的缴费月数
                            self.medical_care_month = self.medical_care_month + 1
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
                    data["medical_care"]["data"][str(year)] = {}
                    for month in tempNormal:
                        try:
                            data["medical_care"]["data"][str(year)][str(month["缴费时间"][5:])].append(month)
                        except:
                            data["medical_care"]["data"][str(year)][str(month["缴费时间"][5:])] = [month]

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
                        for month in tempNormal:
                            try:
                                data["medical_care"]["data"][str(year)][str(month["缴费时间"][5:])].append(month)
                            except:
                                data["medical_care"]["data"][str(year)][str(month["缴费时间"][5:])] = [month]
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
            soup = self._unit_fetch_user_DETAILED(
                DETAILED_LIST_URL + "ybjf.aspx?pageIndex=1&type=gs&id=" + data["baseInfo"]["社保编号"])
            # 获取指定div下table
            result = soup.find("div", {"id": "ctl00_ContentPlaceHolder1_showInfo"}).findAll("table")[0]
            # 拿table中的tr进行循环
            trs = result.findAll('tr')

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
                if trs[0] == tr or trs[1] == tr:
                    continue
                # 查找该行所有td
                tds = tr.findAll('td')
                try:
                    # 需要爬取的数据id从1开始
                    if int(tds[1].text.strip()) > 0:
                        # 获取当前年份
                        year = tds[1].text[0:4]
                        # 获取当前月份
                        month = tds[1].text[0:4] + "-" + tds[1].text[4:6]
                        # 正常年份累计到年份数据源中
                        if year not in years:
                            years.append(year)

                        # 获取表单的第一个时间为最新缴费时间
                        if num == 3:
                            self.injuries_lately_data = tds[1].text
                        # 获取最早参保时间
                        if trs.__len__() == num:
                            self.injuries_lately_start_data = tds[1].text
                        # 定义数据结构
                        obj = {
                            "year": year,
                            "data": {
                                "缴费时间": month,
                                "缴费类型": tds[2].text.strip(),
                                "缴费基数": tds[3].text.strip(),
                                "公司缴费": tds[4].text.strip(),
                                "个人缴费": tds[5].text.strip(),
                                "缴费单位": tds[6].text.strip(),
                            }
                        }

                        # 正常应缴有与补缴进行分区存储
                        if tds[7].text.strip() == '正常结算':
                            # 累计正常缴费的缴费月数
                            self.injuries_month = self.injuries_month + 1
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
                    data["injuries"]["data"][str(year)] = {}
                    for month in tempNormal:
                        try:
                            data["injuries"]["data"][str(year)][str(month["缴费时间"][5:])].append(month)
                        except:
                            data["injuries"]["data"][str(year)][str(month["缴费时间"][5:])] = [month]

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
                        data["injuries"]["data"][str(year)] = {}
                        for month in tempNormal:
                            try:
                                data["injuries"]["data"][str(year)][str(month["缴费时间"][5:])].append(month)
                            except:
                                data["injuries"]["data"][str(year)][str(month["缴费时间"][5:])] = [month]
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
            soup = self._unit_fetch_user_DETAILED(
                DETAILED_LIST_URL + "ybjf.aspx?pageIndex=1&type=shengyu&id=" + data["baseInfo"]["社保编号"])
            # 获取指定div下table
            result = soup.find("div", {"id": "ctl00_ContentPlaceHolder1_showInfo"}).findAll("table")[0]
            # 拿table中的tr进行循环
            trs = result.findAll('tr')

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
                if trs[0] == tr or trs[1] == tr:
                    continue
                # 查找该行所有td
                tds = tr.findAll('td')
                try:
                    # 需要爬取的数据id从1开始
                    if int(tds[1].text.strip()) > 0:
                        # 获取当前年份
                        year = tds[1].text[0:4]
                        # 获取当前月份
                        month = tds[1].text[0:4] + "-" + tds[1].text[4:6]
                        # 正常年份累计到年份数据源中
                        if year not in years:
                            years.append(year)

                        # 获取表单的第一个时间为最新缴费时间
                        if num == 3:
                            self.maternity_lately_data = tds[1].text
                        # 获取最早参保时间
                        if trs.__len__() == num:
                            self.maternity_lately_start_data = tds[1].text
                        # 定义数据结构
                        obj = {
                            "year": year,
                            "data": {
                                "缴费时间": month,
                                "缴费类型": tds[2].text.strip(),
                                "缴费基数": tds[3].text.strip(),
                                "公司缴费": tds[4].text.strip(),
                                "个人缴费": tds[5].text.strip(),
                                "缴费单位": tds[6].text.strip(),
                            }
                        }

                        # 正常应缴有与补缴进行分区存储
                        if tds[7].text.strip() == '正常结算':
                            # 累计正常缴费的缴费月数
                            self.maternity_month = self.maternity_month + 1
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
                    data["injuries"]["data"][str(year)] = {}
                    for month in tempNormal:
                        try:
                            data["injuries"]["data"][str(year)][str(month["缴费时间"][5:])].append(month)
                        except:
                            data["injuries"]["data"][str(year)][str(month["缴费时间"][5:])] = [month]

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
                        for month in tempNormal:
                            try:
                                data["maternity"]["data"][str(year)][str(month["缴费时间"][5:])].append(month)
                            except:
                                data["maternity"]["data"][str(year)][str(month["缴费时间"][5:])] = [month]
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
            soup = self._unit_fetch_user_DETAILED(
                DETAILED_LIST_URL + "ybjf.aspx?pageIndex=1&type=shiye&id=" + data["baseInfo"]["社保编号"])
            # 获取指定div下table
            result = soup.find("div", {"id": "ctl00_ContentPlaceHolder1_showInfo"}).findAll("table")[0]
            # 拿table中的tr进行循环
            trs = result.findAll('tr')

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
                if trs[0] == tr or trs[1] == tr:
                    continue
                # 查找该行所有td
                tds = tr.findAll('td')
                try:
                    # 需要爬取的数据id从1开始
                    if int(tds[1].text.strip()) > 0:
                        # 获取当前年份
                        year = tds[1].text[0:4]
                        # 获取当前月份
                        month = tds[1].text[0:4] + "-" + tds[1].text[4:6]
                        # 正常年份累计到年份数据源中
                        if year not in years:
                            years.append(year)

                        # 获取表单的第一个时间为最新缴费时间
                        if num == 3:
                            self.unemployment_lately_data = tds[1].text
                        # 获取最早参保时间
                        if trs.__len__() == num:
                            self.unemployment_lately_start_data = tds[1].text
                        # 定义数据结构
                        obj = {
                            "year": year,
                            "data": {
                                "缴费时间": month,
                                "缴费类型": tds[2].text.strip(),
                                "缴费基数": tds[3].text.strip(),
                                "公司缴费": tds[4].text.strip(),
                                "个人缴费": tds[5].text.strip(),
                                "缴费单位": tds[6].text.strip(),
                            }
                        }
                        # 正常应缴有与补缴进行分区存储
                        if tds[7].text.strip() == '正常结算':
                            # 累计正常缴费的缴费月数
                            self.unemployment_month = self.unemployment_month + 1
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
                    for month in tempNormal:
                        try:
                            data["unemployment"]["data"][str(year)][str(month["缴费时间"][5:])].append(month)
                        except:
                            data["unemployment"]["data"][str(year)][str(month["缴费时间"][5:])] = [month]

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
                        for month in tempNormal:
                            try:
                                data["unemployment"]["data"][str(year)][str(month["缴费时间"][5:])].append(month)
                            except:
                                data["unemployment"]["data"][str(year)][str(month["缴费时间"][5:])] = [month]
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


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()
