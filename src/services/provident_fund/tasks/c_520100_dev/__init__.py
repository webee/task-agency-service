# cff---贵阳--贵州省省会   公积金信息

import time
import requests
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError

MAIN_URL = r'http://222.85.152.60/PersonBaseInfo.do?method=view'
LOGIN_URL = r"http://222.85.152.60/checklogin.do?method=login"
VC_URL = r"http://222.85.152.60/verifycode.sm?prefix=netdisk&verify="+time.strftime("%Y%m%d%H%M%S")+""


class Task(AbsTaskUnitSessionTask):

    def _prepare(self):
        state: dict = self.state
        self.s = requests.Session()
        cookies = state.get('cookies')
        if cookies:
            self.s.cookies = cookies
        self.s.headers.update({
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                'Accept-Encoding':'gzip, deflate',
                'Host': '222.85.152.60',
        })

        # result
        result: dict = self.result
        result.setdefault('key',{})
        result.setdefault('meta', {})
        result.setdefault('data', {})
        result.setdefault('detail', {})

    def _update_session_data(self):
        super()._update_session_data()
        self.state['cookies'] = self.s.cookies

    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_name, self._unit_login)

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert 'id_num' in params, '缺少身份证号'
        assert 'account_pass' in params, '缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check

    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                #self._check_login_params(params)
                id_num = params['id_num']
                account_pass = params['account_pass']
                vc = params['vc']

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
                html = str(resp.content, 'utf-8')

                self.result['key'] = id_num
                self.result['meta'] = {
                    '身份证号': id_num,
                    '登录密码': account_pass
                }
                return
            except Exception as e:
                err_msg = str(e)

        vc = self._new_vc()
        raise AskForParamsError([
            dict(key='id_num', name='身份证号', cls='input'),
            dict(key='account_pass', name='密码', cls='input'),
            dict(key='vc', name='验证码', cls='data:image', data=vc, query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch_name(self):
        try:
            resp = self.s.get(MAIN_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            datas = soup.select('.table-content')

            self.result['data']['baseInfo']={
            '个人公积金帐号':datas[0].findAll("td")[1].text,
            '姓名':datas[0].findAll("td")[3].text,
            '身份证号':datas[0].findAll("td")[5].text,

            '性别':datas[1].findAll("td")[1].text,
            '手机号':datas[1].findAll("td")[3].text,
            '卡号':datas[1].findAll("td")[5].text,

            '工资基数':datas[3].findAll("td")[1].text.replace('￥','').replace('元',''),
            '月应缴额':datas[3].findAll("td")[3].text.replace('￥','').replace('元',''),

            '单位缴存比例':datas[4].findAll("td")[1].text,
            '职工缴存比例':datas[4].findAll("td")[3].text,

            '单位月应缴存额':datas[5].findAll("td")[1].text.replace('￥','').replace('元',''),
            '职工月应缴存额':datas[5].findAll("td")[3].text.replace('￥','').replace('元',''),

            '开户日期':datas[7].findAll("td")[1].text,
            '汇缴状态': datas[8].findAll("td")[1].text,
            '当前余额': datas[9].findAll("td")[3].text.replace('￥','').replace('元',''),

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

            resp2 = self.s.get("http://222.85.152.60/PersonAccountsList.do?method=list")
            soup2 = BeautifulSoup(resp2.content, 'html.parser')
            data_list = soup2.find('table', {'id': 'extjsp_div_data_table_0'})
            trs = data_list.findAll("tr")

            for tr in range(len(trs)):
                tds=trs[tr].findAll("td")
                self.result['detail'][tds[0].text.replace('.','-')] = {
                    '时间':tds[0].text,
                    '处理类型':tds[1].text,
                    '汇缴年月': tds[2].text,
                    '收入':tds[3].text.replace(',',''),
                    '支出':tds[4].text.replace(',',''),
                    '余额': tds[5].text.replace(',','')
                }
                #self.result['data'].append(self.result['detail'][tds[0].text.replace('.','-')])

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        vc_url = VC_URL + str(int(time.time() * 1000))
        resp = self.s.get(vc_url)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()

    # 342221198809032031  099535
