# cff---成都--四川省省会  社保信息

# 天津  社保信息
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

    def _prepare(self, data=None):
        super()._prepare()
        self.result['data']['baseInfo']={}

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
                self.result_key = params.get('用户名')

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


                # 保存到meta
                self.result_meta['用户名'] = params.get('用户名')
                self.result_meta['密码'] = params.get('密码')
                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='用户名', name='用户名', cls='input', placeholder='请输入登录号|社会保障号|社保卡号', value=params.get('用户名', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    # 转换五险状态
    def _convert_type(self, nums):
        res = ""
        if nums == "1":
            res = "正常参保"
        elif nums == "2":
            res = "暂停"
        elif nums == "3":
            res = "终止"
        return res

    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError

            # 个人信息
            res = self.s.get("https://gr.cdhrss.gov.cn:442/cdwsjb/personal/personalHomeAction!query.do")
            s = json.loads(res.text)["fieldData"]

            self.result['data']['baseInfo'] = {
                '个人编号': s['aaz500'],
                '姓名': s['aac003'],
                '社会保障号': s['aac002'],
                '人员状态': s['aac008'],
                '参保单位': s['aab069'],
                '参保地区': s['yab003'],
            }

            # 社保明细-----养老

            # 社保缴费明细
            self.result['data']["old_age"] = {  # 养老
                "data": {}
            }
            basedataE = self.result['data']["old_age"]["data"]
            modelE = {}

            self.result['data']["medical_care"] = {  # 医疗
                "data": {}
            }
            basedataH = self.result['data']["medical_care"]["data"]
            modelH = {}

            self.result['data']["unemployment"] = {  # 失业
                "data": {}
            }
            basedataI = self.result['data']["unemployment"]["data"]
            modelI = {}

            self.result['data']["injuries"] = {  # 工伤
                "data": {}
            }
            basedataC = self.result['data']["injuries"]["data"]
            modelC = {}

            self.result['data']["maternity"] = {  # 生育
                "data": {}
            }
            basedataB = self.result['data']["maternity"]["data"]
            modelB = {}

            startTime = ""#rs['workDate'][0:6]  # 查询开始时间
            endTime = time.strftime("%Y%m", time.localtime())  # 查询结束时间


            # 社保明细-----养老
            detailEI = self.s.get(
                Detail_URL + "?dto['aae041']=" + startTime + "&dto['aae042']=" + endTime + "&dto['aae140_md5list']=&dto['aae140']=01")
            sEI = json.loads(detailEI.text)['lists']['dg_payment']['list']
            for a in range(len(detailEI)):
                years = str(detailEI[a]['payDate'])[0:4]
                months = str(detailEI[a]['payDate'])[4:6]
                basedataE.setdefault(years, {})
                basedataE[years].setdefault(months, [])

                modelE = {
                    '缴费单位':sEI[a]['aab004'],
                    '缴费年月': sEI[a]['aae002'],
                    '缴费基数': sEI[a]['yac004'],
                    '单位缴存额': sEI[a]['dwjfje'],
                    '个人缴存额': sEI[a]['grjfje'],
                    '缴费合计':sEI[a]['jfjezh']
                }

                basedataE[years][months].append(modelE)

            # 社保明细-----医疗
            detailHI = self.s.get(
                Detail_URL + "?dto['aae041']=" + startTime + "&dto['aae042']=" + endTime + "&dto['aae140_md5list']=&dto['aae140']=03")
            sHI = json.loads(detailHI.text)['lists']['dg_payment']['list']
            for b in range(len(detailHI)):
                yearH = str(detailHI[b]['payDate'])[0:4]
                monthH = str(detailHI[b]['payDate'])[4:6]
                basedataH.setdefault(yearH, {})
                basedataH[yearH].setdefault(monthH, [])

                modelH = {
                    '缴费单位':sHI[b]['aab004'],
                    '缴费年月':sHI[b]['aae002'],
                    '缴费基数': sHI[b]['yac004'],
                    '单位缴存额': sHI[b]['dwjfje'],
                    '个人缴存额': sHI[b]['grjfje'],
                    '缴费合计': sHI[b]['jfjezh']
                }

                basedataH[yearH][monthH].append(modelH)


            # 社保明细-----工伤
            detailCI = self.s.get(
                Detail_URL + "?dto['aae041']=" + startTime + "&dto['aae042']=" + endTime + "&dto['aae140_md5list']=&dto['aae140']=04")
            sCI = json.loads(detailCI.text)['lists']['dg_payment']['list']
            for c in range(len(detailCI)):
                yearC = str(detailCI[c]['payDate'])[0:4]
                monthC = str(detailCI[c]['payDate'])[4:6]
                basedataC.setdefault(yearC, {})
                basedataC[yearC].setdefault(monthC, [])

                modelC = {
                    '缴费单位':sCI[c]['aab004'],
                    '缴费年月': sCI[c]['aae002'],
                    '缴费基数': sCI[c]['yac004'],
                    '单位缴存额': sCI[c]['dwjfje'],
                    '个人缴存额': sCI[c]['grjfje'],
                    '缴费合计': sCI[c]['jfjezh']
                }

                basedataC[yearC][monthC].append(modelC)


            # 社保明细-----失业
            detailII = self.s.get(
                Detail_URL + "?dto['aae041']=" + startTime + "&dto['aae042']=" + endTime + "&dto['aae140_md5list']=&dto['aae140']=02")
            sII = json.loads(detailII.text)['lists']['dg_payment']['list']
            for d in range(len(detailII)):
                yearI = str(detailII[d]['payDate'])[0:4]
                monthI = str(detailII[d]['payDate'])[4:6]
                basedataI.setdefault(yearI, {})
                basedataI[yearI].setdefault(monthI, [])

                modelI = {
                    '缴费单位':sII[d]['aab004'],
                    '缴费年月': sII[d]['aae002'],
                    '缴费基数': sII[d]['yac004'],
                    '单位缴存额': sII[d]['dwjfje'],
                    '个人缴存额': sII[d]['grjfje'],
                    '缴费合计': sII[d]['jfjezh']
                }

                basedataI[yearI][monthI].append(modelI)


            # 社保明细-----生育
            detailBI = self.s.get(
                Detail_URL + "?dto['aae041']=" + startTime + "&dto['aae042']=" + endTime + "&dto['aae140_md5list']=&dto['aae140']=05")
            sBI = json.loads(detailBI.text)['lists']['dg_payment']['list']
            for f in range(len(detailBI)):
                yearB = str(detailBI[f]['payDate'])[0:4]
                monthB = str(detailBI[f]['payDate'])[4:6]
                basedataB.setdefault(yearB, {})
                basedataB[yearB].setdefault(monthB, [])

                modelB = {
                    '缴费单位': sBI[f]['aab004'],
                    '缴费年月': sBI[f]['aae002'],
                    '缴费基数': sBI[f]['yac004'],
                    '单位缴存额': sBI[f]['dwjfje'],
                    '个人缴存额': sBI[f]['grjfje'],
                    '缴费合计': sBI[f]['jfjezh']
                }

                basedataB[yearB][monthB].append(modelB)


            # 五险状态
            stype = json.loads(
                self.s.get(""))
            social_Type = {
                '养老': self._convert_type(stype[0]['paymentState']),
                '医疗': self._convert_type(stype[2]['paymentState']),
                '失业': self._convert_type(stype[1]['paymentState']),
                '工伤': self._convert_type(stype[5]['paymentState']),
                '生育': self._convert_type(stype[6]['paymentState'])
            }


            self.result['identity'] = {
                "task_name": "成都",
                "target_name": s['aac003'],
                "target_id": self.result['meta']["登录号"],
                "status": ""
            }

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task(SessionData()))
    client.run()

    # 028732390  /  510403199511131021    ld1254732520!
