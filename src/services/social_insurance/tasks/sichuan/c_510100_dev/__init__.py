#成都社保查询：
#Code：510100
#地址：https://gr.cdhrss.gov.cn:442/cdwsjb/login.jsp
#账号：028732390
#密码：ld1254732520!

import time,datetime
import requests
import json
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError
from services.commons import AbsFetchTask

MAIN_URL = 'https://gr.cdhrss.gov.cn:442/cdwsjb/personal/personalHomeAction!query.do'
LOGIN_URL = 'https://gr.cdhrss.gov.cn:442/cdwsjb/netHallLoginAction!personalLogin.do'#'https://gr.cdhrss.gov.cn:442/cdwsjb/netHallHomeAction!getViewArticleListForLogin.do'
MXHEARD_URL='https://gr.cdhrss.gov.cn:442/cdwsjb/personal/query/queryPersonPaymentInfoAction.do'
MX_URL='https://gr.cdhrss.gov.cn:442/cdwsjb/personal/query/queryPersonPaymentInfoAction!queryPayment.do'

class Task(AbsFetchTask):
    task_info = dict(
        city_name="成都",
        help="""<li>联名卡有两个密码，一个是银行查询密码，一个是公积金查询服务密码。</li>
                <li>如若查询服务密码，可拨打服务热线12329修改。</li>"""
    )
    def _get_common_headers(self):
        return {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36'
        }



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
        assert '个人编号' in params, '缺少个人编号'
        assert '密码' in params, '缺少密码'

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '个人编号' not in params:
                params['个人编号'] = meta.get('个人编号')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '个人编号' and '个人编号' in meta:
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
                id_num = params['个人编号']
                pwd = params['密码']
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

                self.result_key = id_num
                self.result_meta['个人编号'] = id_num
                self.result_meta['密码'] = pwd
                self.result_identity['task_name'] = '成都'
                return
            except Exception as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='个人编号', name='个人编号', cls='input'),
            dict(key='密码', name='密码',cls='input' )
        ], err_msg)

    def _unit_fetch_name(self):
        try:
            data = self.result['data']
            resp = self.s.post(MAIN_URL,data=dict(userid=''),headers={ 'X-Requested-With': 'XMLHttpRequest'})
            soup = BeautifulSoup(resp.content, 'html.parser')
            jsons=soup.text.replace('\r\n','')
            jsonread=json.loads(jsons)
            data['baseinfo'] = {
                '社保编号': jsonread['fieldData']['aac001'],
                '身份证号': jsonread['fieldData']['aac002'],
                '社会保障号': jsonread['fieldData']['aac002'],
                '参保单位': jsonread['fieldData']['aab069'],
                '姓名': jsonread['fieldData']['aac003'],
                '人员状态': jsonread['fieldData']['aac008'],
                '缴费状态': jsonread['fieldData']['aac031'],
                '参保经办机构': jsonread['fieldData']['yab003'],
                "更新时间": datetime.datetime.now().strftime('%Y-%m-%d'),
                '城市名称': '成都',
                '城市编号': '510100'
            }
            self.result_identity['target_id'] = jsonread['fieldData']['aac002']
            self.result_identity['target_name'] = jsonread['fieldData']['aac003']
            status='断缴'
            if jsonread['fieldData']['aac031']=='参保缴费':
                status='正常缴费'
            self.result_identity['status'] =status
            #明细头
            resp=self.s.get(MXHEARD_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            #typeheards=soup.select('.ui-state-default slick-header-column')
            #typeheards=['缴费月份','单位名称','缴费基数','单位缴费金额','个人缴费金额','单位缴费比例','个人缴费比例','实收时间','划入账户金额','险种类型']

            #明细(险种比较多)
            arrtype1={'01':'养老保险','02':'失业保险','03':'医疗保险','04':'工伤保险','05':'生育保险'}
            arrtype={'01':'old_age','02':'unemployment','03':'medical_care','04':'injuries','05':'maternity'}

            for k,v in arrtype.items():
                arrtime = []
                oldsum = 0.00
                yilsum=0.00
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
                        '缴费时间':dicold['aae002'],
                        '缴费单位': dicold['aab004'],
                        '缴费基数': dicold['yac004'],
                        '公司缴费': dicold['dwjfje'],
                        '个人缴费': dicold['grjfje'],
                        '单位缴费比例': dicold['aaa042'],
                        '个人缴费比例': dicold['aaa041'],
                        '实收时间': dicold['grjfrq'],
                        '划入账户金额': dicold['hrzhje'],
                        '险种类型': arrtype1[dicold['aae140']],
                        '缴费类型':''
                    }
                    if v == 'old_age':
                        arrtime.append(dicold['aae002'])
                        oldsum+=float(dicold['grjfje'])
                    if v == 'medical_care':
                        yilsum+=float(dicold['grjfje'])
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

                    arr.append(dicnew)
                    if len(months) > 0:
                        data[v]['data'][yearkeys][months] = arr
                    else:
                       data[v]['data'][yearkeys].setdefault(yearday[-2:],arr)
                if v=='old_age':
                    data['baseinfo'].setdefault('缴费时长', str(len(arrtime)))
                    data['baseinfo'].setdefault('最近缴费时间', max(arrtime))
                    data['baseinfo'].setdefault('开始缴费时间', min(arrtime))
                    data['baseinfo'].setdefault('个人养老累计缴费', oldsum)
                if v == 'medical_care':
                    data['baseinfo'].setdefault('个人医疗累计缴费', yilsum)
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()