# cff---天津  社保信息

import time
import requests
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError
import json

MAIN_URL = r'http://public.tj.hrss.gov.cn/ehrss/si/person/ui/?code=gD3uyf'
LOGIN_URL = r"http://public.tj.hrss.gov.cn/uaa/api/person/idandmobile/login"
VC_URL = r"http://public.tj.hrss.gov.cn/uaa/captcha/img/"
Detail_URL = r"http://public.tj.hrss.gov.cn/ehrss-si-person/api/rights/payment/emp/"


class Task(AbsTaskUnitSessionTask):
    def _prepare(self):
        state: dict = self.state
        self.s = requests.Session()
        cookies = state.get('cookies')
        if cookies:
            self.s.cookies = cookies
        self.s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate, sdch',
            'Host': 'public.tj.hrss.gov.cn',
        })

        # result
        result: dict = self.result
        result.setdefault('key', {})
        result.setdefault('meta', {})
        result.setdefault('data', {})
        result.setdefault('detailEI', {})  # 养老
        result.setdefault('detailHI', {})  # 医疗
        result.setdefault('detailCI', {})  # 工伤
        result.setdefault('detailII', {})  # 失业
        result.setdefault('detailBI', {})  # 生育
        result.setdefault('identity', {})

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

    def _new_vc(self):
        resps = self.s.get(VC_URL)
        soup = BeautifulSoup(resps.text, 'html.parser')
        vc_url = VC_URL + soup.text[7:].replace('"}', '')
        global CaptchaIds
        CaptchaIds = soup.text[7:].replace('"}', '')
        resp = self.s.get(vc_url)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])

    def _unit_login(self, params=None):
        err_msg = None
        if params:
            # 非开始或者开始就提供了参数
            try:

                id_num = params['id_num']
                account_pass = params['account_pass']
                CaptchaId = CaptchaIds
                vc = params['vc']

                data = {
                    'username': id_num,
                    'password': account_pass,
                    'captchaId': CaptchaId,
                    'captchaWord': vc
                }
                resp = self.s.post(LOGIN_URL, data=data)

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
            dict(key='id_num', name='用户名', cls='input'),
            dict(key='account_pass', name='登录密码', cls='input'),
            dict(key='vc', name='验证码', cls='data:image', data=vc, query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch_name(self):
        try:
            rest = self.s.get("http://public.tj.hrss.gov.cn/api/security/user")
            s = json.loads(rest.text)["associatedPersons"][0]["id"]

            respon = self.s.get("http://public.tj.hrss.gov.cn/ehrss-si-person/api/rights/persons/" + str(s))
            rs = json.loads(respon.text)
            if rs['sex'] == "1":  # 性别
                sexs = '男'
            elif rs['sex'] == "2":
                sexs = '女'

            if rs['mobileNumber'] is None:  # 联系电话
                mobileNumber = ""
            else:
                mobileNumber = rs['mobileNumber']

            rsep = self.s.get("http://public.tj.hrss.gov.cn/ehrss-si-person/api/selectcodes")
            res = json.loads(rsep.text)["codeList"]
            for nt in range(len(res["NATION"])):  # 民族
                if res["NATION"][nt]["value"] == rs['nation']:
                    nations = res["NATION"][nt]["name"]
                    break

            for ht in range(len(res["HOUSEHOLD_TYPE"])):  # 户口性质
                if res["HOUSEHOLD_TYPE"][ht]["value"] == rs['householdType']:
                    householdTypes = res["HOUSEHOLD_TYPE"][ht]["name"]
                    break

            self.result['data']['userInfo'] = {
                '姓名': rs['name'],
                '性别': sexs,
                '民族': nations,
                '出生日期': rs['birthday'],
                '证件号码': rs['idNumber'],
                '社保卡号': rs['socialSecurityCardNumber'],
                '手机号码': mobileNumber,
                '参加工作日期': rs['workDate'],
                '户口性质': householdTypes,
                # '户口所在地详址':rs['householdAddress']
            }

            # 设置identity
            identity = self.result['identity']
            identity.update({
                'task_name': '天津市',
                'target_name': rs['name'],
                'target_id': self.result['meta']["身份证号"],
                'status': "",
            })

            # 社保明细-----养老
            beginTime = input("请输入需要查询的开始年月：")
            endTime = input("请输入需要查询的结束年月：")
            paymentFlag = "1"
            rpEI = self.s.get(Detail_URL + str(
                s) + "?beginTime=" + beginTime + "&endTime=" + endTime + "&insureCode=110&paymentFlag=" + paymentFlag)
            detailEI = json.loads(rpEI.text)['empPaymentDTO']
            for a in range(len(detailEI)):
                self.result['detailEI'][str(detailEI[a]['payDate'])] = {
                    '缴费单位': detailEI[a]['payCompany'],
                    '缴费年月': detailEI[a]['payDate'],
                    '缴费基数': detailEI[a]['payBase'],
                    '单位缴存额': detailEI[a]['companyOverallPay'],
                    '个人缴存额': detailEI[a]['personPay'],
                    '缴费合计': detailEI[a]['payCount']
                }

            # 社保明细-----医疗
            rpHI = self.s.get(Detail_URL + str(
                s) + "?beginTime=" + beginTime + "&endTime=" + endTime + "&insureCode=310&paymentFlag=" + paymentFlag)
            detailHI = json.loads(rpHI.text)['empPaymentDTO']
            for b in range(len(detailHI)):
                self.result['detailHI'][str(detailHI[b]['payDate'])] = {
                    '缴费单位': detailHI[b]['payCompany'],
                    '缴费年月': detailHI[b]['payDate'],
                    '缴费基数': detailHI[b]['payBase'],
                    '单位缴存额': detailHI[b]['companyOverallPay'],
                    '个人缴存额': detailHI[b]['personPay'],
                    '缴费合计': detailHI[b]['payCount']
                }

            # 社保明细-----工伤
            rpCI = self.s.get(Detail_URL + str(
                s) + "?beginTime=" + beginTime + "&endTime=" + endTime + "&insureCode=410&paymentFlag=" + paymentFlag)
            detailCI = json.loads(rpCI.text)['empPaymentDTO']
            for c in range(len(detailCI)):
                self.result['detailCI'][str(detailCI[c]['payDate'])] = {
                    '缴费单位': detailCI[c]['payCompany'],
                    '缴费年月': detailCI[c]['payDate'],
                    '缴费基数': detailCI[c]['payBase'],
                    '单位缴存额': detailCI[c]['companyOverallPay'],
                    '个人缴存额': detailCI[c]['personPay'],
                    '缴费合计': detailCI[c]['payCount']
                }

            # 社保明细-----失业
            rpII = self.s.get(Detail_URL + str(
                s) + "?beginTime=" + beginTime + "&endTime=" + endTime + "&insureCode=210&paymentFlag=" + paymentFlag)
            detailII = json.loads(rpII.text)['empPaymentDTO']
            for d in range(len(detailII)):
                self.result['detailII'][str(detailII[d]['payDate'])] = {
                    '缴费单位': detailII[d]['payCompany'],
                    '缴费年月': detailII[d]['payDate'],
                    '缴费基数': detailII[d]['payBase'],
                    '单位缴存额': detailII[d]['companyOverallPay'],
                    '个人缴存额': detailII[d]['personPay'],
                    '缴费合计': detailII[d]['payCount']
                }

            # 社保明细-----生育
            rpBI = self.s.get(Detail_URL + str(
                s) + "?beginTime=" + beginTime + "&endTime=" + endTime + "&insureCode=510&paymentFlag=" + paymentFlag)
            detailBI = json.loads(rpBI.text)['empPaymentDTO']
            for f in range(len(detailBI)):
                self.result['detailBI'][str(detailBI[f]['payDate'])] = {
                    '缴费单位': detailBI[f]['payCompany'],
                    '缴费年月': detailBI[f]['payDate'],
                    '缴费基数': detailBI[f]['payBase'],
                    '单位缴存额': detailBI[f]['companyOverallPay'],
                    '个人缴存额': detailBI[f]['personPay'],
                    '缴费合计': detailBI[f]['payCount']
                }

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()

    # 120103197208142619  scz518695
