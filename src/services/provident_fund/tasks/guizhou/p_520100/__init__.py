# cff---贵阳--贵州省省会   公积金信息

import time
import requests
from bs4 import BeautifulSoup

from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError, InvalidConditionError, \
    PreconditionNotSatisfiedError
from services.commons import AbsFetchTask

MAIN_URL = r'http://zxcx.gygjj.gov.cn/PersonBaseInfo.do?method=view'
LOGIN_URL = r"http://zxcx.gygjj.gov.cn/checklogin.do?method=login"
VC_URL = r"http://zxcx.gygjj.gov.cn/verifycode.sm?prefix=netdisk&verify="+time.strftime("%Y%m%d%H%M%S")+""


class Task(AbsFetchTask):
    task_info = dict(
        city_name="贵阳",
        help="""
            <li></li>
            """
    )

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                'Accept-Encoding':'gzip, deflate',
                'Host': 'zxcx.gygjj.gov.cn',
        }

    def _prepare(self, data=None):
        super()._prepare()
        self.result_data['baseInfo']={}
        self.result_data['detail'] = {}
        self.result_data['companyList']={}

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '身份证号' in params, '缺少身份证号'
        assert '密码' in params, '缺少密码'
        # other check
        身份证号 = params['身份证号']
        密码 = params['密码']

        if len(身份证号) == 0:
            raise InvalidParamsError('身份证号为空，请输入身份证号')
        elif len(身份证号) < 15:
            raise InvalidParamsError('身份证号不正确，请重新输入')

        if len(密码) == 0:
            raise InvalidParamsError('密码为空，请输入密码！')
        elif len(密码) < 6:
            raise InvalidParamsError('密码不正确，请重新输入！')

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
            res.append(pr)
        return res


    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params.get("身份证号")
                account_pass = params.get("密码")
                vc = params.get("vc")

                data={
                    'aaxmlrequest': 'true',
                    'logintype': 'person',
                    'spcode': '',
                    'fromtype': 'null',
                    'IsCheckVerifyCode': 'on',
                    'IdCard': id_num,
                    'PassWord': account_pass,
                    'Ed_Confirmation': vc
                }
                resp = self.s.post(LOGIN_URL, data=data)

                self.result_key = id_num
                self.result_meta['身份证号'] =id_num
                self.result_meta['密码']=account_pass

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input'),
            dict(key='密码', name='密码', cls='input'),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch(self):
        try:
            resp = self.s.get(MAIN_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            datas = soup.select('.table-content')

            self.result_data['baseInfo']={
                '公积金帐号':datas[0].findAll("td")[1].text,
                '姓名':datas[0].findAll("td")[3].text,
                '身份证号':datas[0].findAll("td")[5].text,

                '性别':datas[1].findAll("td")[1].text,
                '手机号':datas[1].findAll("td")[3].text,
                '卡号':datas[1].findAll("td")[5].text,

                '工资基数':datas[3].findAll("td")[1].text.replace('￥','').replace('元',''),

                '单位缴存比例':datas[4].findAll("td")[1].text,
                '职工缴存比例':datas[4].findAll("td")[3].text,

                '单位月应缴存额':datas[5].findAll("td")[1].text.replace('￥','').replace('元',''),
                '职工月应缴存额':datas[5].findAll("td")[3].text.replace('￥','').replace('元',''),

                '开户日期':datas[7].findAll("td")[1].text,
                '更新日期': time.strftime("%Y-%m-%d", time.localtime()),
                '城市名称': '贵阳市',
                '城市编号': '520100'

            # '汇缴状态': datas[8].findAll("td")[1].text,
            # '月应缴额':datas[3].findAll("td")[3].text.replace('￥','').replace('元',''),
            #'起缴年月':datas[7].findAll("td")[3].text,
            #'职工汇缴年月':datas[7].findAll("td")[5].text,
            #'所属管理部':datas[8].findAll("td")[3].text,
            #'是否冻结':datas[9].findAll("td")[1].text,
            #'是否贷款':datas[9].findAll("td")[5].text,
            # '单位经办人':datas[11].findAll("td")[1].text,
            # '单位法人':datas[11].findAll("td")[3].text,
            # '单位地址':datas[12].findAll("td")[1].text
            }

            #公积金明细

            resp2 = self.s.get("http://zxcx.gygjj.gov.cn/PersonAccountsList.do?method=list")
            soup2 = BeautifulSoup(resp2.content, 'html.parser')
            data_list = soup2.find('table', {'id': 'extjsp_div_data_table_0'})
            trs = data_list.findAll("tr")
            self.result_data['detail']={"data":{}}
            baseDetail = self.result_data["detail"]["data"]
            model={}
            company=soup2.findAll('table')[1].findAll('td')

            for tr in range(len(trs)):
                tds=trs[tr].findAll("td")
                years=tds[0].text[0:4]
                months=tds[0].text[5:7]
                model = {
                    '时间':tds[0].text,
                    '类型':tds[1].text,
                    '汇缴年月': tds[2].text,
                    '收入':tds[3].text.replace(',',''),
                    '支出':tds[4].text.replace(',',''),
                    '余额': tds[5].text.replace(',',''),
                    '单位名称':company[1].text.split('：')[1]
                }
                baseDetail.setdefault(years, {})
                baseDetail[years].setdefault(months, [])
                baseDetail[years][months].append(model)

            self.result_data['companyList'] = {
                "单位名称": company[1].text.split('：')[1],
                "单位登记号": company[0].text.split("：")[1],
                "所属管理部编号": "-",
                "所属管理部名称": "-",
                "当前余额": datas[9].findAll("td")[3].text.replace('￥','').replace('元',''),
                "帐户状态": datas[8].findAll("td")[1].text,
                "当年缴存金额": "-",
                "当年提取金额": "-",
                "上年结转余额": "-",
                "最后业务日期": datas[7].findAll("td")[5].text,
                "转出金额": "-"
            }

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        vc_url = VC_URL + time.strftime("%Y%m%d%H%M%S",time.localtime())
        resp = self.s.get(vc_url)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task(SessionData()))
    client.run()

    # 342221198809032031  099535
