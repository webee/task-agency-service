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
Detail_URL=r"http://public.tj.hrss.gov.cn/ehrss-si-person/api/rights/payment/emp/"

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
                'Host': 'public.tj.hrss.gov.cn',
        })

        # result
        result: dict = self.result
        result.setdefault('meta', {})
        result.setdefault('data', {})
        self.result['data']['baseInfo']={}
        result.setdefault('key', {})


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
        assert 'id_num' in params, '缺少用户名'
        assert 'account_pass' in params, '缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check

    def _new_vc(self):
        resps = self.s.get(VC_URL)
        soup =BeautifulSoup(resps.text,'html.parser')
        vc_url = VC_URL + soup.text[7:].replace('"}','')
        global CaptchaIds
        CaptchaIds=soup.text[7:].replace('"}','')
        resp = self.s.get(vc_url)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])

    #转换五险状态
    def _convert_type(self,nums):
        res=""
        if(nums=="1"):
            res="参保"
        elif(nums=="2"):
            res="暂停"
        elif(nums=="3"):
            res="终止"
        return res

    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:

                id_num = params['id_num']
                account_pass = params['account_pass']
                CaptchaId =CaptchaIds
                vc = params['vc']

                data={
                    'username':id_num,
                    'password':account_pass,
                    'captchaId':CaptchaId,
                    'captchaWord':vc
                }
                resp = self.s.post(LOGIN_URL, data=data)

                self.result['key'] = id_num
                self.result['meta'] = {
                    '用户名': id_num,
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
            rs = json.loads((respon.text))
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


            #社保明细-----养老

            #社保缴费明细
            self.result['data']["old_age"] = {                                  # 养老
                "data": {}
            }
            basedataE = self.result['data']["old_age"]["data"]
            modelE = {}

            self.result['data']["medical_care"] = {                            # 医疗
                "data": {}
            }
            basedataH = self.result['data']["medical_care"]["data"]
            modelH = {}

            self.result['data']["unemployment"] = {                             # 失业
                "data": {}
            }
            basedataI = self.result['data']["unemployment"]["data"]
            modelI = {}

            self.result['data']["injuries"] = {                             # 工伤
                "data": {}
            }
            basedataC = self.result['data']["injuries"]["data"]
            modelC = {}

            self.result['data']["maternity"] = {                             # 生育
                "data": {}
            }
            basedataB = self.result['data']["maternity"]["data"]
            modelB = {}

            perTotalold=0.00;
            perTotalMedical=0.00;
            beginTime=rs['workDate'][0:6]   #查询开始时间
            endTime=time.strftime("%Y%m",time.localtime())     #查询结束时间
            paymentFlag="1"

            # 社保明细-----养老
            rpEI=self.s.get(Detail_URL+str(s) + "?beginTime=" + beginTime + "&endTime=" + endTime + "&insureCode=110&paymentFlag="+paymentFlag)
            detailEI=json.loads(rpEI.text)['empPaymentDTO']
            for a in range(len(detailEI)):
                years=str(detailEI[a]['payDate'])[0:4]
                months=str(detailEI[a]['payDate'])[4:6]
                basedataE.setdefault(years,{})
                basedataE[years].setdefault(months,[])

                modelE={
                    '缴费单位': detailEI[a]['payCompany'],
                    '缴费年月': detailEI[a]['payDate'],
                    '缴费基数': detailEI[a]['payBase'],
                    '单位缴存额': detailEI[a]['companyOverallPay'],
                    '个人缴存额': detailEI[a]['personPay'],
                }

                perTotalold +=float(detailEI[a]['personPay'])   #个人养老累积缴费
                basedataE[years][months].append(modelE)


            # 社保明细-----医疗
            rpHI = self.s.get(Detail_URL + str(s) + "?beginTime=" + beginTime + "&endTime=" + endTime + "&insureCode=310&paymentFlag=" + paymentFlag)
            detailHI = json.loads(rpHI.text)['empPaymentDTO']
            for b in range(len(detailHI)):
                yearH = str(detailHI[b]['payDate'])[0:4]
                monthH = str(detailHI[b]['payDate'])[4:6]
                basedataH.setdefault(yearH, {})
                basedataH[yearH].setdefault(monthH, [])

                modelH={
                    '缴费单位': detailHI[b]['payCompany'],
                    '缴费年月': detailHI[b]['payDate'],
                    '缴费基数': detailHI[b]['payBase'],
                    '单位缴存额': detailHI[b]['companyOverallPay'],
                    '个人缴存额': detailHI[b]['personPay'],
                    # '缴费合计': detailHI[b]['payCount']
                }

                perTotalMedical +=float(detailHI[b]['personPay'])    #个人医疗累积缴费
                basedataH[yearH][monthH].append(modelH)


            # 社保明细-----工伤
            rpCI = self.s.get(Detail_URL + str(s) + "?beginTime=" + beginTime + "&endTime=" + endTime + "&insureCode=410&paymentFlag=" + paymentFlag)
            detailCI = json.loads(rpCI.text)['empPaymentDTO']
            for c in range(len(detailCI)):
                yearC = str(detailCI[c]['payDate'])[0:4]
                monthC = str(detailCI[c]['payDate'])[4:6]
                basedataC.setdefault(yearC, {})
                basedataC[yearC].setdefault(monthC, [])

                modelC={
                    '缴费单位': detailCI[c]['payCompany'],
                    '缴费年月': detailCI[c]['payDate'],
                    '缴费基数': detailCI[c]['payBase'],
                    '单位缴存额': detailCI[c]['companyOverallPay'],
                    '个人缴存额': detailCI[c]['personPay'],
                }

                basedataC[yearC][monthC].append(modelC)


            # 社保明细-----失业
            rpII = self.s.get(Detail_URL + str(s) + "?beginTime=" + beginTime + "&endTime=" + endTime + "&insureCode=210&paymentFlag=" + paymentFlag)
            detailII = json.loads(rpII.text)['empPaymentDTO']
            for d in range(len(detailII)):
                yearI = str(detailII[d]['payDate'])[0:4]
                monthI = str(detailII[d]['payDate'])[4:6]
                basedataI.setdefault(yearI, {})
                basedataI[yearI].setdefault(monthI, [])

                modelI={
                    '缴费单位': detailII[d]['payCompany'],
                    '缴费年月': detailII[d]['payDate'],
                    '缴费基数': detailII[d]['payBase'],
                    '单位缴存额': detailII[d]['companyOverallPay'],
                    '个人缴存额': detailII[d]['personPay'],
                }

                basedataI[yearI][monthI].append(modelI)


            # 社保明细-----生育
            rpBI = self.s.get(Detail_URL + str(s) + "?beginTime=" + beginTime + "&endTime=" + endTime + "&insureCode=510&paymentFlag=" + paymentFlag)
            detailBI = json.loads(rpBI.text)['empPaymentDTO']
            for f in range(len(detailBI)):
                yearB = str(detailBI[f]['payDate'])[0:4]
                monthB = str(detailBI[f]['payDate'])[4:6]
                basedataB.setdefault(yearB, {})
                basedataB[yearB].setdefault(monthB, [])

                modelB={
                    '缴费单位': detailBI[f]['payCompany'],
                    '缴费年月': detailBI[f]['payDate'],
                    '缴费基数': detailBI[f]['payBase'],
                    '单位缴存额': detailBI[f]['companyOverallPay'],
                    '个人缴存额': detailBI[f]['personPay'],
                }

                basedataB[yearB][monthB].append(modelB)


            #五险状态
            stype=json.loads(self.s.get("http://public.tj.hrss.gov.cn/ehrss-si-person/api/rights/insure/"+ str(s) +"").text)
            social_Type={
                '养老':self._convert_type(stype[0]['paymentState']),
                '医疗':self._convert_type(stype[2]['paymentState']),
                '失业':self._convert_type(stype[1]['paymentState']),
                '工伤':self._convert_type(stype[5]['paymentState']),
                '生育':self._convert_type(stype[6]['paymentState'])
            }

            #个人基本详细信息
            counts=0;
            if(len(detailEI)<=len(detailHI)):
                counts=len(detailHI)
            else:
                counts=len(detailEI)

            self.result['data']['baseInfo'] = {
                '姓名': rs['name'],
                '身份证号': rs['idNumber'],
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '城市名称': '天津市',
                '城市编号': '120100',
                '缴费时长': counts,
                '最近缴费时间': detailEI[len(detailEI)-1]['payDate'],
                '开始缴费时间': rs['workDate'][0:6],
                '个人养老累积缴费': perTotalold,
                '个人医疗累积缴费': perTotalMedical,
                '五险状态':social_Type
                # '性别': sexs,
                # '民族':nations,
                # '出生日期':rs['birthday'],
                # '社保卡号':rs['socialSecurityCardNumber'],
                # '手机号码':mobileNumber,
                # '户口性质':householdTypes,
                # '户口所在地详址':rs['householdAddress']
            }

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()

    # 120103197208142619  scz518695
