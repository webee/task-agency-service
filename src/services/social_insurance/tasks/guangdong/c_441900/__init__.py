import time, datetime
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask
from bs4 import BeautifulSoup

LOGIN_URL = 'https://grcx.dgsi.gov.cn/action/LoginAction'  # https://grcx.dgsi.gov.cn/
VC_URL = 'https://grcx.dgsi.gov.cn/pages/checkimage.JSP'
INFOR_URL = 'https://grcx.dgsi.gov.cn/action/MainAction?'


class Task(AbsFetchTask):
    task_info = dict(
        city_name="东莞",

        developers=[{'name': '卜圆圆', 'email': 'byy@qinqinxiaobao.com'}]
    )

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1'}

    def _query(self, params: dict):
        """任务状态查询"""
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '身份证号' in params, '缺少身份证号'
        assert '密码' in params, '缺少密码'
        # other check
        身份证号 = params['身份证号']
        密码 = params['密码']
        if len(密码) < 4:
            raise InvalidParamsError('密码错误')
        if len(身份证号) < 15:
            raise InvalidParamsError('身份证号错误')

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '身份证号' not in params:
                params['身份证号'] = meta.get('身份证号')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '身份证号' and '身份证号' in meta:
                continue
            elif pr['key'] == '密码' and '密码' in meta:
                continue
            elif pr['key'] == 'other':
                continue
            res.append(pr)
        return res

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                id_num = params['身份证号']
                password = params['密码']
                vc = params['vc']
                data = {
                    'ywType': 'login',
                    'SFZHM': id_num,
                    'PASSWORD': password,
                    'imagecheck': vc
                }
                resp = self.s.post(LOGIN_URL, verify=False, data=data, timeout=20)
                soup = BeautifulSoup(resp.content, 'html.parser')
                successinfo = soup.findAll('td')
                if len(successinfo) > 0:
                    successinfo = successinfo[4].text
                else:
                    successinfo = ''
                if successinfo:
                    return_message = successinfo
                    raise InvalidParamsError(return_message)
                else:
                    print("登录成功！")

                self.result_key = id_num
                # 保存到meta
                self.result_meta['身份证号'] = id_num
                self.result_meta['密码'] = params.get('密码')
                self.result_identity['task_name'] = '东莞'
                self.result_identity['target_id'] = id_num
                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input', placeholder='身份证号', value=params.get('身份证号', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            # 基本信息
            resp = self.s.get(INFOR_URL + 'menuid=105702&ActionType=grzlxg', verify=False, timeout=20)
            soup = BeautifulSoup(resp.content, 'html.parser')
            tables = soup.findAll('td')
            data = self.result_data
            data['baseInfo'] = {
                '城市名称': '东莞',
                '城市编号': '441900',
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '身份证号': self.result_meta['身份证号'],
                '姓名': tables[1].text.replace('\xa0', ''),
                '性别': tables[5].text.replace('\xa0', ''),
                '出生日期': tables[7].text.replace('\xa0', ''),
                '参加工作日期': tables[9].text.replace('\xa0', ''),
                '手机号码': soup.findAll('input')[2].attrs['value']
            }
            # 参保状态
            resp = self.s.get(INFOR_URL + 'menuid=106203&ActionType=q_grcbxxcx', verify=False, timeout=20)
            soup = BeautifulSoup(resp.content, 'html.parser')
            tbody = soup.findAll('tbody')[1]
            rows = tbody.find_all('tr')
            fivdic = {}
            ljmonth = []
            fristtime = []
            for row in rows:
                cell = [i.text.replace('保险', '').replace('基本', '').replace(' ', '') for i in row.find_all('td')]
                fivdic.setdefault(cell[1], cell[2])
                fristtime.append(cell[3])
                ljmonth.append(int(cell[4]))
            data['baseInfo'].setdefault('五险状态', fivdic)
            data['baseInfo'].setdefault('缴费时长', max(ljmonth))
            data['baseInfo'].setdefault('开始缴费时间', min(fristtime))
            self.result_identity['target_name'] = data['baseInfo']['姓名']
            if '参保缴费' in fivdic.values():
                self.result_identity['status'] = '正常'
            else:
                self.result_identity['status'] = '停缴'
            # 缴费明细menuid=206206&ActionType=q_grcbxzjfmxcx_tj
            # 五险明细
            # 五险arrtype={'110':'基本养老保险','210':'失业保险','310':'基本医疗保险','410':'工伤保险','510':'生育保险'}
            arrtype = {'110': 'old_age', '210': 'unemployment', '310': 'medical_care', '410': 'injuries',
                       '510': 'maternity'}
            ylsum = 0.00
            yilsum = 0.00
            arrMaxtime = []
            for k, v in arrtype.items():  # 类型
                data[v] = {}
                data[v]['data'] = {}
                for i in range(int(min(fristtime)[:4]), datetime.datetime.now().year + 1, 3):  # 年
                    resp = self.s.get(INFOR_URL + 'ActionType=q_grcbxzjfmxcx&xzlx=' + str(k) + '&ksjfsj=' + str(
                        i) + '01&jsjfsj=' + str(i + 2) + '12', verify=False, timeout=20)
                    soup = BeautifulSoup(resp.content, 'html.parser')
                    tbody = soup.findAll('tbody')
                    if not tbody:
                        continue
                    rows = tbody[0].find_all('tr')
                    for row in rows:
                        cell = [i.text.replace(' ', '') for i in row.find_all('td')]
                        if cell[0] != '合计':
                            monthkeyslist = cell[2].split('-')
                            statatime = monthkeyslist[0]
                            endtime = monthkeyslist[1]
                            monthcount = (int(endtime[:4]) - int(statatime[:4])) * 12 + (
                            int(endtime[-2:]) - int(statatime[-2:])) + 1
                            for y in range(-1, monthcount - 1):
                                arrs = []
                                nowtime = datetime.date(int(statatime[:4]) + (int(statatime[-2:]) + y) // 12,
                                                        (int(statatime[-2:]) + y) % 12 + 1, 1).strftime('%Y-%m-%d')
                                strtimemonth = nowtime[:7].replace('-', '')
                                yearkeys = strtimemonth
                                dic = {
                                    '缴费时间': yearkeys,
                                    '险种名称': cell[4],
                                    '缴费基数': float(cell[5].replace(',', '')),
                                    '个人缴费': float(cell[7].replace(',', '')) / monthcount,
                                    '单位编号': cell[4],
                                    '缴费单位': cell[1],
                                    '缴费类型': cell[3],
                                    '公司缴费': float(cell[6].replace(',', '')) / monthcount
                                }
                                years = yearkeys[:4]
                                months = yearkeys[-2:]
                                if v == 'old_age':
                                    ylsum = ylsum + float(cell[7]) / monthcount
                                if v == 'medical_care':
                                    yilsum = yilsum + float(cell[7]) / monthcount
                                if years not in data[v]['data'].keys():
                                    data[v]['data'][years] = {}
                                if months not in data[v]['data'][years].keys():
                                    data[v]['data'][years][months] = {}
                                else:
                                    arrs = data[v]['data'][years][months]
                                arrs.append(dic)
                                data[v]['data'][years][months] = arrs
                if v == 'old_age':
                    data['baseInfo'].setdefault('个人养老累计缴费', ylsum)
                if v == 'medical_care':
                    data['baseInfo'].setdefault('个人医疗累计缴费', yilsum)
                arrMaxtime.append(max(data[v]['data']) + max(data[v]['data'][max(data[v]['data'])]))
                time.sleep(1)
            data['baseInfo'].setdefault('最近缴费时间', min(arrMaxtime))
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        resp = self.s.get('https://grcx.dgsi.gov.cn/', verify=False, timeout=20)
        resp = self.s.get(VC_URL, verify=False, timeout=25)
        return dict(content=resp.content)


if __name__ == '__main__':
    from services.client import TaskTestClient

    meta = {'身份证号': '140321198209121213', '密码': '20160414'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()

# 身份证号：513901198603293354   密码：20171226  身份证号：140321198209121213  密码：20160414
