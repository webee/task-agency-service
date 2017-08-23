#成都社保查询：
#Code：510100
#地址：https://gr.cdhrss.gov.cn:442/cdwsjb/login.jsp
#账号：028732390
#密码：ld1254732520!

import time
import requests
import json
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError


MAIN_URL = 'https://gr.cdhrss.gov.cn:442/cdwsjb/personal/personalHomeAction!query.do'
LOGIN_URL = 'https://gr.cdhrss.gov.cn:442/cdwsjb/netHallLoginAction!personalLogin.do'#'https://gr.cdhrss.gov.cn:442/cdwsjb/netHallHomeAction!getViewArticleListForLogin.do'
MXHEARD_URL='https://gr.cdhrss.gov.cn:442/cdwsjb/personal/query/queryPersonPaymentInfoAction.do'
MX_URL='https://gr.cdhrss.gov.cn:442/cdwsjb/personal/query/queryPersonPaymentInfoAction!queryPayment.do'

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
        self._add_unit(self._unit_fetch_name, self._unit_login)

    def _update_session_data(self):
        super()._update_session_data()
        self.state['cookies'] = self.s.cookies
    def _query(self, params: dict):
        t = params.get('t')

    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert 'id_num' in params, '缺少个人编号'
        assert 'password' in params, '缺少密码'
        # other check

    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params['id_num']
                pwd = params['password']
                times=str(int(time.time() * 1000))

                resp = self.s.post(LOGIN_URL, data=dict(
                    type='',
                    checkCode='',
                    username=id_num,
                    password=pwd,
                    tm=times
                ),headers={ 'X-Requested-With': 'XMLHttpRequest'})
                data = resp.json()
                errormsg = data.get('msg')
                if errormsg:
                    raise Exception(errormsg)

                self.result['key'] = '%s.%s' % ('real', id_num)
                self.result['meta'] = {
                    'task': 'real',
                    'id_num': id_num}
                return
            except Exception as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='id_num', name='个人编号', cls='input'),
            dict(key='password', name='密码',cls='input' )
        ], err_msg)

    def _unit_fetch_name(self):
        try:
            data = self.result['data']
            resp = self.s.post(MAIN_URL,data=dict(userid=''),headers={ 'X-Requested-With': 'XMLHttpRequest'})
            soup = BeautifulSoup(resp.content, 'html.parser')
            jsons=soup.text.replace('\r\n','')
            jsonread=json.loads(jsons)
            data['baseinfo'] = {
                '个人编号': jsonread['fieldData']['aac001'],
                '社会保障号': jsonread['fieldData']['aac002'],
                '参保单位': jsonread['fieldData']['aab069'],
                '姓名': jsonread['fieldData']['aac003'],
                '人员状态': jsonread['fieldData']['aac008'],
                '缴费状态': jsonread['fieldData']['aac031'],
                '参保经办机构': jsonread['fieldData']['yab003']
            }

            #明细头
            resp=self.s.get(MXHEARD_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            #typeheards=soup.select('.ui-state-default slick-header-column')
            typeheards=['缴费月份','单位名称','缴费基数','单位缴费金额','个人缴费金额','单位缴费比例','个人缴费比例','实收时间','划入账户金额','险种类型']

            #明细(险种比较多)arrtype={'01':'基本养老保险','02':'失业保险','03':'基本医疗保险','04':'工伤保险','05':'生育保险'}
            arrtype={'01':'old_age','02':'unemployment','03':'medical_care','04':'injuries','05':'maternity'}
            for k,v in arrtype.items():
                data1 ={
                    "dto['aae041']": '191501',
                    "dto['aae042']": time.time(),
                    "dto['aae140_md5list']":'',
                    "dto['aae140']": k}
                data[v] = {}
                data[v]['data'] = {}
                resp = self.s.post(MX_URL, data=data1)
                soup = BeautifulSoup(resp.content, 'html.parser')
                jsons = soup.text.replace('\r\n', '')
                jsonread = json.loads(jsons)
                jsonlist=jsonread['lists']['dg_payment']['list']
                yearkeys=''
                for i in range(0,len(jsonlist)) :
                    dicold=jsonlist[i]
                    dicnew={
                        typeheards[0]:dicold['aae002'],
                        typeheards[1]: dicold['aab004'],
                        typeheards[2]: dicold['yac004'],
                        typeheards[3]: dicold['dwjfje'],
                        typeheards[4]: dicold['grjfje'],
                        typeheards[5]: dicold['aaa042'],
                        typeheards[6]: dicold['aaa041'],
                        typeheards[7]: dicold['grjfrq'],
                        typeheards[8]: dicold['hrzhje'],
                        typeheards[9]: dicold['aae140']
                    }
                    yearday= dicold['aae002']
                    if yearkeys!=yearday[:4] or yearkeys=='':
                        yearkeys=yearday[:4]
                        data[v]['data'][yearkeys]={}
                    arr = []
                    months = ''
                    for (key, value) in data[v]['data'][yearkeys].items():
                        if key == yearday[-2:]:
                            months = yearday[-2:]
                            arr.append(value)
                        else:
                            print(key)

                    arr.append(dicnew)
                    if len(months) > 0:
                        data[v]['data'][yearkeys][months] = arr
                    else:
                       data[v]['data'][yearkeys].setdefault(yearday[-2:],dicnew)


            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()
