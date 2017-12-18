# 天津  社保信息
from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError, InvalidConditionError, \
    PreconditionNotSatisfiedError
from services.commons import AbsFetchTask

import time
from bs4 import BeautifulSoup
import json

from services.test.mock_site import TestSite
from services.test.mock import UserAgent, LogRequestFilter

LOGIN_PAGE_URL = 'http://public.tj.hrss.gov.cn/uaa/personlogin'
MAIN_URL = ''
LOGIN_URL = "http://public.hrss.tj.gov.cn/uaa/personlogin#/personLogin"
VC_URL = "http://public.hrss.tj.gov.cn/uaa/captcha/img/"
Detail_URL = "http://public.hrss.tj.gov.cn/ehrss-si-person/api/rights/payment/emp/"

test_site = TestSite()


class Task(AbsFetchTask):
    task_info = dict(
        city_name="天津",
        help="""
        <li>如您未在社保网站查询过您的社保信息，请到天津社保网上服务平台完成“注册”后再登录查询</li>
        <li>如忘记密码，可在天津社保网上服务平台中的”忘记密码”中重置密码</li>
        """,

        developers=[{'name': '程菲菲', 'email': 'feifei_cheng@chinahrs.net'}]
    )

    # def _prepare(self,data=None):
    #     super()._prepare()
    #
    #     state: dict = self.state
    #     self.ua = UserAgent(test_site, state.get('session'))
    #     self.ua.register_request_filter(LogRequestFilter())

    def _update_session_data(self):
        super()._update_session_data()
        # self.state['session'] = self.ua.session

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.79 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'public.hrss.tj.gov.cn',
        }

    def _query(self, params: dict):
        """任务状态查询"""
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()
            # pass

    def _new_vc(self):
        resps = self.s.get(VC_URL)
        soup = resps.text.split(':')[1].replace('"','').replace('}','')
        vc_url = VC_URL + soup
        self.state['CaptchaIds'] = soup
        resp = self.s.get(vc_url)
        return dict(cls='data:image',content=resp.content,content_type=resp.headers['Content-Type'])

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
                CaptchaId = self.state['CaptchaIds']
                vc = params.get("vc")
                # self.ua.get_vc().replace('*','')
                # self.ua.login(id_num, account_pass, vc)

                # self.result_data['x']=self.ua.x()

                data = {
                    'username': id_num,
                    'password': account_pass,
                    'captchaId': CaptchaId,
                    'captchaWord': vc
                }
                resp = self.s.post("http://public.hrss.tj.gov.cn/uaa/api/person/idandmobile/login", data=data)
                # if resp.text == "":
                #     raise InvalidParamsError("登录失败")
                # if resp.url.startswith(LOGIN_PAGE_URL + '?error'):
                #     soup = BeautifulSoup(resp.content, 'html.parser')
                #     divs = soup.select('body > div.alert.alert-danger')
                #     err_msg = "登录失败"
                #     if divs and len(divs) > 0:
                #         err_msg = divs[0].text
                #     raise InvalidParamsError(err_msg)
                if 'http://public.hrss.tj.gov.cn/ehrss/si/person/ui/' not in resp.url:
                    raise InvalidParamsError("登录失败，用户名或密码错误！")
                else:
                    # 保存到meta
                    self.result_meta['用户名'] = params.get('用户名')
                    self.result_meta['密码'] = params.get('密码')
                    return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='用户名', name='用户名', cls='input', placeholder='手机,社保卡或身份证号', value=params.get('用户名', '')),
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
            self.result['data']['baseInfo']={}
            rest = self.s.get("http://public.hrss.tj.gov.cn/api/security/user")
            if rest.status_code!=200:
                raise InvalidConditionError("未找到对应的信息！")

            s = json.loads(rest.text)["associatedPersons"][0]["id"]
            s2=json.loads(rest.text)["associatedPersons"][0]["personNumber"]

            respon = self.s.get("http://public.tj.hrss.gov.cn/ehrss-si-person/api/rights/persons/" + str(s))
            respon2=self.s.get("http://public.tj.hrss.gov.cn/ehrss-si-person/api/rights/persons/overview/" + s2)
            rs = json.loads((respon.text))
            rs2=json.loads((respon2.text))
            # if rs['sex']=="1":            #性别
            #     sexs='男'
            # elif rs['sex']=="2":
            #     sexs='女'
            # if rs['mobileNumber']==None:     #联系电话
            #     mobileNumber=""
            # else:
            #     mobileNumber=rs['mobileNumber']
            # rsep = self.s.get("http://public.tj.hrss.gov.cn/ehrss-si-person/api/selectcodes")
            # res = json.loads(rsep.text)["codeList"]
            # for nt in range(len(res["NATION"])):                                                      #民族
            #     if res["NATION"][nt]["value"] == rs['nation']:
            #         nations=res["NATION"][nt]["name"]
            #         break
            # for ht in range(len(res["HOUSEHOLD_TYPE"])):                                              #户口性质
            #     if res["HOUSEHOLD_TYPE"][ht]["value"] == rs['householdType']:
            #         householdTypes=res["HOUSEHOLD_TYPE"][ht]["name"]
            #         break


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

            perTotalold = 0.00;
            perTotalMedical = 0.00;
            beginTime = rs['workDate'][0:6]  # 查询开始时间
            endTime = time.strftime("%Y%m", time.localtime())  # 查询结束时间
            paymentFlag = "1"

            # 社保明细-----养老
            rpEI = self.s.get(Detail_URL + str(
                s) + "?beginTime=" + beginTime + "&endTime=" + endTime + "&insureCode=110&paymentFlag=" + paymentFlag)
            detailEI = json.loads(rpEI.text)['empPaymentDTO']
            for a in range(len(detailEI)):
                years = str(detailEI[a]['payDate'])[0:4]
                months = str(detailEI[a]['payDate'])[4:6]
                basedataE.setdefault(years, {})
                basedataE[years].setdefault(months, [])

                modelE = {
                    '缴费单位': detailEI[a]['payCompany'],
                    '缴费类型': '',
                    '缴费时间': str(detailEI[a]['payDate']),
                    '缴费基数': detailEI[a]['payBase'],
                    '公司缴费': float(detailEI[a]['companyOverallPay'])+float(detailEI[a]['companyPay']),
                    '个人缴费': detailEI[a]['personPay'],
                    '单位划入统筹': detailEI[a]['companyOverallPay'],
                    '单位划入个账': detailEI[a]['companyPay']
                }

                perTotalold += float(detailEI[a]['personPay'])  # 个人养老累计缴费
                basedataE[years][months].append(modelE)

            # 社保明细-----医疗
            rpHI = self.s.get(Detail_URL + str(
                s) + "?beginTime=" + beginTime + "&endTime=" + endTime + "&insureCode=310&paymentFlag=" + paymentFlag)
            detailHI = json.loads(rpHI.text)['empPaymentDTO']
            for b in range(len(detailHI)):
                yearH = str(detailHI[b]['payDate'])[0:4]
                monthH = str(detailHI[b]['payDate'])[4:6]
                basedataH.setdefault(yearH, {})
                basedataH[yearH].setdefault(monthH, [])

                modelH = {
                    '缴费单位': detailHI[b]['payCompany'],
                    '缴费类型': '',
                    '缴费时间': str(detailHI[b]['payDate']),
                    '缴费基数': detailHI[b]['payBase'],
                    '公司缴费': float(detailHI[b]['companyOverallPay'])+float(detailHI[b]['companyPay']),
                    '个人缴费': detailHI[b]['personPay'],
                    # '缴费合计': detailHI[b]['payCount']
                    '单位划入统筹':detailHI[b]['companyOverallPay'],
                    '单位划入个账':detailHI[b]['companyPay']
                }

                perTotalMedical += float(detailHI[b]['personPay'])  # 个人医疗累计缴费
                basedataH[yearH][monthH].append(modelH)


            # 社保明细-----工伤
            rpCI = self.s.get(Detail_URL + str(
                s) + "?beginTime=" + beginTime + "&endTime=" + endTime + "&insureCode=410&paymentFlag=" + paymentFlag)
            detailCI = json.loads(rpCI.text)['empPaymentDTO']
            for c in range(len(detailCI)):
                yearC = str(detailCI[c]['payDate'])[0:4]
                monthC = str(detailCI[c]['payDate'])[4:6]
                basedataC.setdefault(yearC, {})
                basedataC[yearC].setdefault(monthC, [])

                modelC = {
                    '缴费单位': detailCI[c]['payCompany'],
                    '缴费类型': '',
                    '缴费时间': str(detailCI[c]['payDate']),
                    '缴费基数': detailCI[c]['payBase'],
                    '公司缴费': detailCI[c]['companyOverallPay'],
                    '个人缴费': '',
                }

                basedataC[yearC][monthC].append(modelC)


            # 社保明细-----失业
            rpII = self.s.get(Detail_URL + str(
                s) + "?beginTime=" + beginTime + "&endTime=" + endTime + "&insureCode=210&paymentFlag=" + paymentFlag)
            detailII = json.loads(rpII.text)['empPaymentDTO']
            for d in range(len(detailII)):
                yearI = str(detailII[d]['payDate'])[0:4]
                monthI = str(detailII[d]['payDate'])[4:6]
                basedataI.setdefault(yearI, {})
                basedataI[yearI].setdefault(monthI, [])

                modelI = {
                    '缴费单位': detailII[d]['payCompany'],
                    '缴费类型': '',
                    '缴费时间': str(detailII[d]['payDate']),
                    '缴费基数': detailII[d]['payBase'],
                    '公司缴费': detailII[d]['companyOverallPay'],
                    '个人缴费': detailII[d]['personOverallPay'],
                }

                basedataI[yearI][monthI].append(modelI)


            # 社保明细-----生育
            rpBI = self.s.get(Detail_URL + str(
                s) + "?beginTime=" + beginTime + "&endTime=" + endTime + "&insureCode=510&paymentFlag=" + paymentFlag)
            detailBI = json.loads(rpBI.text)['empPaymentDTO']
            for f in range(len(detailBI)):
                yearB = str(detailBI[f]['payDate'])[0:4]
                monthB = str(detailBI[f]['payDate'])[4:6]
                basedataB.setdefault(yearB, {})
                basedataB[yearB].setdefault(monthB, [])

                modelB = {
                    '缴费单位': detailBI[f]['payCompany'],
                    '缴费类型': '',
                    '缴费时间': str(detailBI[f]['payDate']),
                    '缴费基数': detailBI[f]['payBase'],
                    '公司缴费': detailBI[f]['companyOverallPay'],
                    '个人缴费': '',
                }

                basedataB[yearB][monthB].append(modelB)

            # 大病明细
            self.result['data']["serious_illness"] = {"data": {}}


            # 五险状态
            stype = json.loads(self.s.get("http://public.tj.hrss.gov.cn/ehrss-si-person/api/rights/insure/" + str(s) + "").text)
            yanglao="0"
            yiliao="0"
            shiye="0"
            gongshang="0"
            shengyu="0"
            for wxt in range(len(stype)):
                if stype[wxt]['insuranceCode']=="110":
                    yanglao=stype[wxt]['paymentState']
                elif stype[wxt]['insuranceCode']=="210":
                    shiye=stype[wxt]['paymentState']
                elif stype[wxt]['insuranceCode']=="310":
                    yiliao=stype[wxt]['paymentState']
                elif stype[wxt]['insuranceCode']=="410":
                    gongshang=stype[wxt]['paymentState']
                elif stype[wxt]['insuranceCode']=="510":
                    shengyu=stype[wxt]['paymentState']

            social_Type = {
                '养老': self._convert_type(yanglao),
                '医疗': self._convert_type(yiliao),
                '失业': self._convert_type(shiye),
                '工伤': self._convert_type(gongshang),
                '生育': self._convert_type(shengyu)
            }


            # 个人基本详细信息
            counts = 0;
            if (len(detailEI) <= len(detailHI)):
                counts = len(detailHI)
            else:
                counts = len(detailEI)

            if (social_Type['养老'] == "正常参保"):
                statuss = "正常"
            else:
                statuss = "停缴"

            self.result['data']['baseInfo'] = {
                '姓名': rs['name'],
                '身份证号': rs['idNumber'],
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '城市名称': '天津市',
                '城市编号': '120100',
                '缴费时长': counts,
                '最近缴费时间': str(detailEI[len(detailEI) - 1]['payDate']),
                '开始缴费时间': str(detailEI[0]['payDate']),
                '个人养老累计缴费': perTotalold,
                '个人医疗累计缴费': perTotalMedical,
                '五险状态': social_Type,
                '账户状态':statuss,
                # '性别': sexs,
                # '民族':nations,
                # '出生日期':rs['birthday'],
                # '社保卡号':rs['socialSecurityCardNumber'],
                # '手机号码':mobileNumber,
                # '户口性质':householdTypes,
                # '户口所在地详址':rs['householdAddress']
                '医疗账户余额':str(rs2['medicalBalance']),
                '城职养老账户余额':str(rs2['empAccountSum']),
                '职业年金余额':str(rs2['residentAccountSum'])
            }

            self.result['identity'] = {
                "task_name": "天津",
                "target_name": rs['name'],
                "target_id": self.result_meta['用户名'],
                "status": statuss
            }

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task(SessionData()))
    client.run()

    # 120103197208142619  scz518695
