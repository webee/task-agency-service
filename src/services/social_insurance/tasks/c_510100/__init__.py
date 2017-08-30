# cff---成都--四川省省会  社保信息

import time
import requests
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError
import json

MAIN_URL = r"https://gr.cdhrss.gov.cn:442/cdwsjb/personal/personalHomeAction!query.do"
LOGIN_URL = r"https://gr.cdhrss.gov.cn:442/cdwsjb/netHallLoginAction!personalLogin.do"
VC_URL = r""
Detail_URL=r"https://gr.cdhrss.gov.cn:442/cdwsjb/personal/query/queryPersonPaymentInfoAction!queryPayment.do"

class Task(AbsTaskUnitSessionTask):

    def _prepare(self):
        state: dict = self.state
        self.s = requests.Session()
        cookies = state.get('cookies')
        if cookies:
            self.s.cookies = cookies
        self.s.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36',
                'Accept-Encoding':'gzip, deflate, sdch',
                'Host': 'gr.cdhrss.gov.cn:442',
                'X-Requested-With':'XMLHttpRequest',
        })

        # result
        result: dict = self.result
        result.setdefault('key',{})
        result.setdefault('meta', {})
        result.setdefault('data', {})   # 个人基本信息

        result.setdefault('detailEI',{})     #养老缴费详细
        result.setdefault('detailHI', {})    #医疗缴费详细
        result.setdefault('detailII', {})    #失业缴费详细
        result.setdefault('detailCI', {})    #工伤缴费详细
        result.setdefault('detailBI', {})    #生育缴费详细
        result.setdefault('identity', {})

    def _update_session_data(self):
        super()._update_session_data()
        self.state['cookies'] = self.s.cookies

    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_name, self._unit_login)

    def _query(self, params: dict):
        while True:
            return self._new_vc()

    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert 'id_num' in params, '缺少身份证号'
        assert 'account_pass' in params, '缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check

    def _new_vc(self):
        return True

    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:

                id_num = params['id_num']
                account_pass = params['account_pass']

                data={
                    'username':id_num,
                    'password':account_pass,
                    'checkCode':'undefined',
                    'type':'undefined',
                    'tm':str(time.time()*1000)[0:13],
                }

                resp = self.s.post(LOGIN_URL,data=data)

                self.result['key'] = id_num
                self.result['meta'] = {
                    '登录号': id_num,
                    '登录密码': account_pass
                }

                return
            except Exception as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='id_num', name='用户名', cls='input'),
            dict(key='account_pass', name='登录密码', cls='input'),
        ], err_msg)


    def _unit_fetch_name(self):
        try:
            # 个人信息
            res = self.s.get("https://gr.cdhrss.gov.cn:442/cdwsjb/personal/personalHomeAction!query.do")
            s = json.loads(res.text)["fieldData"]

            self.result['data']["userInfo"] = {
                '个人编号': s['aaz500'],
                '姓名': s['aac003'],
                '社会保障号': s['aac002'],
                '人员状态': s['aac008'],
                '参保单位': s['aab069'],
                '参保地区': s['yab003'],
            }

            # 设置identity
            identity = self.result['identity']
            identity.update({
                'task_name': '成都市',
                'target_name': s['aac003'],
                'target_id': self.result['meta']["登录号"],
                'status': "",
            })

            #养老保险明细
            startTime=input("请输入需要查询的开始时间：")
            endTime=input("请输入需要查询的结束时间：")

            detailEI=self.s.get(Detail_URL+"?dto['aae041']="+startTime+"&dto['aae042']="+endTime+"&dto['aae140_md5list']=&dto['aae140']=01")
            sEI=json.loads(detailEI.text)['lists']['dg_payment']['list']
            for a in range(len(sEI)):
                self.result['detailEI'][str(sEI[a]['aae002'])]={
                    '缴费单位':sEI[a]['aab004'],
                    '缴费年月': sEI[a]['aae002'],
                    '缴费基数': sEI[a]['yac004'],
                    '单位缴存额': sEI[a]['dwjfje'],
                    '个人缴存额': sEI[a]['grjfje'],
                    '缴费合计':sEI[a]['jfjezh']
                }

            #医疗保险明细
            detailHI=self.s.get(Detail_URL+"?dto['aae041']="+startTime+"&dto['aae042']="+endTime+"&dto['aae140_md5list']=&dto['aae140']=03")
            sHI=json.loads(detailHI.text)['lists']['dg_payment']['list']
            for b in range(len(sHI)):
                self.result['detailHI'][str(sHI[b]['aae002'])]={
                    '缴费单位':sHI[b]['aab004'],
                    '缴费年月':sHI[b]['aae002'],
                    '缴费基数': sHI[b]['yac004'],
                    '单位缴存额': sHI[b]['dwjfje'],
                    '个人缴存额': sHI[b]['grjfje'],
                    '缴费合计': sHI[b]['jfjezh']
                }

            #失业保险明细
            detailII=self.s.get(Detail_URL+"?dto['aae041']="+startTime+"&dto['aae042']="+endTime+"&dto['aae140_md5list']=&dto['aae140']=02")
            sII=json.loads(detailII.text)['lists']['dg_payment']['list']
            for c in range(len(sII)):
                self.result['detailII'][str(sII[c]['aae002'])]={
                    '缴费单位':sII[c]['aab004'],
                    '缴费年月': sII[c]['aae002'],
                    '缴费基数': sII[c]['yac004'],
                    '单位缴存额': sII[c]['dwjfje'],
                    '个人缴存额': sII[c]['grjfje'],
                    '缴费合计': sII[c]['jfjezh']
                }

            #工伤保险明细
            detailCI=self.s.get(Detail_URL+"?dto['aae041']="+startTime+"&dto['aae042']="+endTime+"&dto['aae140_md5list']=&dto['aae140']=04")
            sCI=json.loads(detailCI.text)['lists']['dg_payment']['list']
            for d in range(len(sCI)):
                self.result['detailCI'][str(sCI[d]['aae002'])]={
                    '缴费单位':sCI[d]['aab004'],
                    '缴费年月': sCI[d]['aae002'],
                    '缴费基数': sCI[d]['yac004'],
                    '单位缴存额': sCI[d]['dwjfje'],
                    '个人缴存额': sCI[d]['grjfje'],
                    '缴费合计': sCI[d]['jfjezh']
                }

            #生育保险明细
            detailBI=self.s.get(Detail_URL+"?dto['aae041']="+startTime+"&dto['aae042']="+endTime+"&dto['aae140_md5list']=&dto['aae140']=05")
            sBI=json.loads(detailBI.text)['lists']['dg_payment']['list']
            for f in range(len(sBI)):
                self.result['detailBI'][str(sBI[f]['aae002'])]={
                    '缴费单位':sBI[f]['aab004'],
                    '缴费年月': sBI[f]['aae002'],
                    '缴费基数': sBI[f]['yac004'],
                    '单位缴存额': sBI[f]['dwjfje'],
                    '个人缴存额': sBI[f]['grjfje'],
                    '缴费合计': sBI[f]['jfjezh']
                }

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()

    # 028732390  /  510403199511131021    ld1254732520!

