# cff---成都--四川省省会  社保信息


from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError, InvalidConditionError, \
    PreconditionNotSatisfiedError
from services.commons import AbsFetchTask

import time
import requests
from bs4 import BeautifulSoup
import json

MAIN_URL = r"https://gr.cdhrss.gov.cn:442/cdwsjb/personal/personalHomeAction!query.do"
LOGIN_URL = r"https://gr.cdhrss.gov.cn:442/cdwsjb/netHallLoginAction!personalLogin.do"
VC_URL = r"https://gr.cdhrss.gov.cn:442/cdwsjb/CaptchaImg"
Detail_URL=r"https://gr.cdhrss.gov.cn:442/cdwsjb/personal/query/queryPersonPaymentInfoAction!queryPayment.do"


class Task(AbsFetchTask):
    task_info = dict(
        city_name="成都",
        help="""
        <li>联名卡有两个密码，一个是银行查询密码，一个是公积金查询服务密码</li>
        <li>如若查询服务密码，可拨打服务热线12329修改</li>
        """
    )

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36',
            'Accept-Encoding':'gzip, deflate, sdch',
            'Host': 'gr.cdhrss.gov.cn:442',
            'X-Requested-With':'XMLHttpRequest',
        }

    # def _prepare(self, data=None):
    #     super()._prepare()
    #     self.result_data['baseInfo']={}

    def _query(self, params: dict):
        """任务状态查询"""
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()
            # pass

    def _new_vc(self):
        resp = self.s.get(VC_URL)
        return dict(cls='data:image', content=resp.content, content_type=resp.headers['Content-Type'])

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '用户名' in params, '缺少用户名'
        assert '密码' in params, '缺少密码'
        # other check
        用户名 = params['用户名']
        密码 = params['密码']

        if len(用户名) == 0:
            raise InvalidParamsError('用户名为空，请输入用户名')
        elif len(用户名) < 4:
            raise InvalidParamsError('用户名不正确，请重新输入')

        if len(密码) == 0:
            raise InvalidParamsError('密码为空，请输入密码！')
        elif len(密码) < 6:
            raise InvalidParamsError('密码不正确，请重新输入！')

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '用户名' not in params:
                params['用户名'] = meta.get('用户名')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '用户名' and '用户名' in meta:
                continue
            elif pr['key'] == '密码' and '密码' in meta:
                continue
            res.append(pr)
        return res

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)

                id_num = params.get("用户名")
                account_pass = params.get("密码")
                vc = params.get("vc")

                data = {
                    'username':id_num,
                    'password':account_pass,
                    'checkCode':vc,
                    'type':'undefined',
                    'tm':str(time.time()*1000)[0:13],
                }
                resp = self.s.post(LOGIN_URL, data=data)
                res=json.loads(resp.text)
                if(len(res)>1):
                    raise InvalidParamsError(res['msg'])
                else:
                    # 保存到meta
                    self.result_key = id_num
                    self.result_meta['用户名'] = id_num
                    self.result_meta['密码'] = account_pass
                    return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='用户名', name='用户名', cls='input', placeholder='请输入登录号|社会保障号|社保卡号', value=params.get('用户名', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _convert_type(self,num):
        resinfo=""
        if(num=="1"):
            resinfo="正常"
        else:
            resinfo="异常"
        return resinfo

    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            # 个人信息
            res = self.s.get("https://gr.cdhrss.gov.cn:442/cdwsjb/personal/personalHomeAction!query.do")
            s = json.loads(res.text)["fieldData"]

            # 社保明细
            startTime = "199001"
            endTime = time.strftime("%Y%m", time.localtime())  # 查询结束时间

            # 社保缴费明细-----养老
            self.result['data']["old_age"] = { "data": {}}
            basedataE = self.result['data']["old_age"]["data"]
            modelE = {}
            peroldTotal=0.0
            detailEI = self.s.get(Detail_URL + "?dto['aae041']=" + startTime + "&dto['aae042']=" + endTime + "&dto['aae140_md5list']=&dto['aae140']=01")
            sEI = json.loads(detailEI.text)['lists']['dg_payment']['list']
            for a in range(len(sEI)):
                years = str(sEI[a]['aae002'])[0:4]
                months = str(sEI[a]['aae002'])[4:6]
                basedataE.setdefault(years, {})
                basedataE[years].setdefault(months, [])

                modelE = {
                    '缴费单位': sEI[a]['aab004'],
                    '缴费时间': sEI[a]['aae002'],
                    '缴费类型':'',
                    '缴费基数': sEI[a]['yac004'],
                    '公司缴费': sEI[a]['dwjfje'],
                    '个人缴费': sEI[a]['grjfje']
                    #'缴费合计': sEI[a]['jfjezh']
                }
                peroldTotal += float(sEI[a]['grjfje'])
                basedataE[years][months].append(modelE)


            self.result['data']["medical_care"] = {"data": {}}
            basedataH = self.result['data']["medical_care"]["data"]
            modelH = {}
            permedicalTotal=0.0
            # 社保明细-----医疗
            detailHI = self.s.get(Detail_URL + "?dto['aae041']=" + startTime + "&dto['aae042']=" + endTime + "&dto['aae140_md5list']=&dto['aae140']=03")
            sHI = json.loads(detailHI.text)['lists']['dg_payment']['list']
            for b in range(len(sHI)):
                yearH = str(sHI[b]['aae002'])[0:4]
                monthH = str(sHI[b]['aae002'])[4:6]
                basedataH.setdefault(yearH, {})
                basedataH[yearH].setdefault(monthH, [])

                modelH = {
                    '缴费单位': sHI[b]['aab004'],
                    '缴费时间': sHI[b]['aae002'],
                    '缴费类型': '',
                    '缴费基数': sHI[b]['yac004'],
                    '公司缴费': sHI[b]['dwjfje'],
                    '个人缴费': sHI[b]['grjfje'],
                    #'缴费合计': sHI[b]['jfjezh']
                }
                permedicalTotal += float(sHI[b]['grjfje'])
                basedataH[yearH][monthH].append(modelH)


            self.result['data']["unemployment"] = {"data": {}}
            basedataI = self.result['data']["unemployment"]["data"]
            modelI = {}
            # 社保明细-----失业
            detailII = self.s.get(Detail_URL + "?dto['aae041']=" + startTime + "&dto['aae042']=" + endTime + "&dto['aae140_md5list']=&dto['aae140']=02")
            sII = json.loads(detailII.text)['lists']['dg_payment']['list']
            for d in range(len(sII)):
                yearI = str(sII[d]['aae002'])[0:4]
                monthI = str(sII[d]['aae002'])[4:6]
                basedataI.setdefault(yearI, {})
                basedataI[yearI].setdefault(monthI, [])

                modelI = {
                    '缴费单位': sII[d]['aab004'],
                    '缴费时间': sII[d]['aae002'],
                    '缴费类型': '',
                    '缴费基数': sII[d]['yac004'],
                    '公司缴费': sII[d]['dwjfje'],
                    '个人缴费': sII[d]['grjfje'],
                    #'缴费合计': sII[d]['jfjezh']
                }
                basedataI[yearI][monthI].append(modelI)


            self.result['data']["injuries"] = {"data": {}}
            basedataC = self.result['data']["injuries"]["data"]
            modelC = {}
            # 社保明细-----工伤
            detailCI = self.s.get(Detail_URL + "?dto['aae041']=" + startTime + "&dto['aae042']=" + endTime + "&dto['aae140_md5list']=&dto['aae140']=04")
            sCI = json.loads(detailCI.text)['lists']['dg_payment']['list']
            for c in range(len(sCI)):
                yearC = str(sCI[c]['aae002'])[0:4]
                monthC = str(sCI[c]['aae002'])[4:6]
                basedataC.setdefault(yearC, {})
                basedataC[yearC].setdefault(monthC, [])

                modelC = {
                    '缴费单位': sCI[c]['aab004'],
                    '缴费时间': sCI[c]['aae002'],
                    '缴费类型': '',
                    '缴费基数': sCI[c]['yac004'],
                    '公司缴费': sCI[c]['dwjfje'],
                    '个人缴费': '-',
                    #'缴费合计': sCI[c]['jfjezh']
                }
                basedataC[yearC][monthC].append(modelC)


            self.result['data']["maternity"] = {"data": {}}
            basedataB = self.result['data']["maternity"]["data"]
            modelB = {}
            # 社保明细-----生育
            detailBI = self.s.get(Detail_URL + "?dto['aae041']=" + startTime + "&dto['aae042']=" + endTime + "&dto['aae140_md5list']=&dto['aae140']=05")
            sBI = json.loads(detailBI.text)['lists']['dg_payment']['list']
            for f in range(len(sBI)):
                yearB = str(sBI[f]['aae002'])[0:4]
                monthB = str(sBI[f]['aae002'])[4:6]
                basedataB.setdefault(yearB, {})
                basedataB[yearB].setdefault(monthB, [])

                modelB = {
                    '缴费单位': sBI[f]['aab004'],
                    '缴费时间': sBI[f]['aae002'],
                    '缴费类型': '',
                    '缴费基数': sBI[f]['yac004'],
                    '公司缴费': sBI[f]['dwjfje'],
                    '个人缴费': '-',
                    #'缴费合计': sBI[f]['jfjezh']
                }
                basedataB[yearB][monthB].append(modelB)


            # 五险状态
            stype =self.s.get("https://gr.cdhrss.gov.cn:442/cdwsjb/personal/query/queryCZInsuranceInfoAction.do")
            stypes=BeautifulSoup(stype.text,'html.parser').find('div',{'id':'SeInfo'})
            stype2=json.loads(stypes.text.split('data')[39].split(';')[0].replace('=',''))['list']
            social_Type = {
                '养老': self._convert_type(stype2[0]['aac031']),
                '医疗': self._convert_type(stype2[2]['aac031']),
                '失业': self._convert_type(stype2[1]['aac031']),
                '工伤': self._convert_type(stype2[3]['aac031']),
                '生育': self._convert_type(stype2[4]['aac031'])
            }


            # 个人基本信息
            if(s['aac031']=="参保缴费"):
                status="正常"
            else:
                status="异常"

            mcount=[len(sEI)-1,len(sHI)-1,len(sII)-1,len(sCI)-1,len(sBI)-1]    # 缴费时长
            moneyCount=max(mcount)

            self.result_data['baseInfo'] = {
                '姓名': s['aac003'],
                '身份证号': s['aac002'],
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '城市名称': '成都',
                '城市编号': '510100',
                '缴费时长': moneyCount,
                '最近缴费时间': sEI[0]['aae002'],
                '开始缴费时间': sEI[len(sEI)-1]['aae002'],
                '个人养老累计缴费': peroldTotal,
                '个人医疗累计缴费': permedicalTotal,
                '五险状态': social_Type,
                '状态': status,

                '个人编号': s['aac001'],
            }

            self.result['identity'] = {
                "task_name": "成都",
                "target_name": s['aac003'],
                "target_id": self.result['meta']["用户名"],
                "status": status
            }

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task(SessionData()))
    client.run()

    # 028732390  /  510403199511131021    ld1254732520!
