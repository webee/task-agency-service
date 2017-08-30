# cff---济南  社保信息

import time
import requests
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError
import json
import base64
from PIL import Image
import io
import hashlib


LOGIN_URL = r"http://60.216.99.138/hsp/logonDialog.jsp"
VC_URL = r"http://60.216.99.138/hsp/genAuthCode"


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
                'Host': '60.216.99.138',
                'X-Requested-With':'XMLHttpRequest'
        })

        # result
        result: dict = self.result
        result.setdefault('key',{})
        result.setdefault('meta', {})
        result.setdefault('data', {})

        result.setdefault('detailEI',{})           #养老
        result.setdefault('detailHI', {})          #医疗
        result.setdefault('detailII', {})          #失业
        result.setdefault('detailCI', {})          #工伤
        result.setdefault('detailBI', {})          #生育


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
        resps = json.loads(self.s.get(VC_URL).text)
        firstNum=resps['numLeftBase64']
        oprate=resps['operatorBase64']
        lastNum=resps['numRightBase64']
        equla=resps['equalsBase64']

        arr = [firstNum,oprate,lastNum,equla]
        toImage = Image.new('RGB',(110,50),(255,255,255))
        for i in range(4):
            fromImge = Image.open(io.BytesIO(base64.b64decode(arr[i])))
            if(fromImge.mode=="P"):
                fromImge.convert("RGB")
            loc=(i*22+15,10)
            toImage.paste(fromImge,loc)

        toImage.show()

    def _unit_login(self, params=None):
        err_msg = None
        if params:
            # 非开始或者开始就提供了参数
            try:

                id_num = params['id_num']
                account_pass = params['account_pass']
                m = hashlib.md5()
                m.update(str(account_pass).encode(encoding="utf-8"))
                pw = m.hexdigest()

                self._new_vc()
                vc = input("请输入运算后的结果：")

                _xmlString="<?xml version='1.0' encoding='UTF-8'?><p><s userid='"+id_num+"'/><s usermm='"+pw+"'/><s authcode='"+vc+"'/><s yxzjlx='A'/><s appversion='1.0.60'/><s dlfs='undefined'/></p>"

                resp = self.s.post("http://60.216.99.138/hsp/logon.do?method=doLogon&_xmlString="+_xmlString)
                uuid=resp.text.split(',')[2].split(':')[1].replace('"','').replace('"','')

                # 个人基本信息
                res=self.s.get("http://60.216.99.138/hsp/hspUser.do?method=fwdQueryPerInfo&__usersession_uuid="+uuid)
                soup=BeautifulSoup(res.content,'html.parser').findAll("tr")
                self.result['data']['baseInfo']={
                    '姓名':soup[0].findAll("td")[1].find(type="text")["value"],
                    '身份证号':soup[0].findAll("td")[3].find(type="text")["value"],

                    '性别':soup[1].findAll("td")[1].find(type="text")["value"],
                    '出生日期': soup[1].findAll("td")[3].find(type="text")["value"],

                    '单位名称': soup[9].findAll("td")[1].find(type="text")["value"]
                    #'民族':soup[2].findAll("td")[1].find(type="text")["value"],
                    #'户口性质':soup[3].findAll("td")[3].find(type="text")["value"],
                }

                searchYear=input("请输入需要查询的年份：")
                if(searchYear==""):
                    searchYears=time.localtime()[0]
                else:
                    searchYears=searchYear

                # 养老缴费明细
                sEI=self.s.get("http://60.216.99.138/hsp/siAd.do?method=queryAgedPayHis&__usersession_uuid="+uuid+"&year="+str(searchYears)+"")
                detailEI= BeautifulSoup(sEI.content, 'html.parser').find('table', {'class': 'defaultTableClass'}).findAll("tr")
                for a in range(len(detailEI)):
                    if((a+1)<len(detailEI)):
                        td = detailEI[a + 1].findAll("td")
                        self.result['detailEI'][td[3].find(type="text")["value"]] = {
                            '缴费年月': td[0].find(type="text")["value"],
                            '缴费基数': str(td[1].find(type="text")["value"]).replace(',',''),
                            '缴费金额': td[2].find(type="text")["value"],
                        }

                # 医疗缴费明细
                sHI=self.s.get("http://60.216.99.138/hsp/siMedi.do?method=queryMediPayHis&__usersession_uuid="+uuid+"&year="+str(searchYears)+"")
                detailHI= BeautifulSoup(sHI.content, 'html.parser').find('table',{'class':'defaultTableClass'}).findAll("tr")
                for b in range(len(detailHI)):
                    if((b+1)<len(detailHI)):
                        td2 = detailHI[b + 1].findAll("td")
                        self.result['detailHI'][td2[5].find(type="text")["value"]] = {
                            '缴费年月': td2[0].find(type="text")["value"],
                            '缴费基数': str(td2[1].find(type="text")["value"]).replace(',',''),
                            '缴费金额': td2[2].find(type="text")["value"],
                        }

                # 失业缴费明细
                sII=self.s.get("http://60.216.99.138/hsp/siLost.do?method=queryLostPayHis&__usersession_uuid="+uuid+"&year="+str(searchYears)+"")
                detailII = BeautifulSoup(sII.content, 'html.parser').find('table',{'class': 'defaultTableClass'}).findAll("tr")
                for c in range(len(detailII)):
                    if((c+1)<len(detailII)):
                        td3 = detailII[c + 1].findAll("td")
                        self.result['detailII'][td3[3].find(type="text")["value"]] = {
                            '缴费年月': td3[0].find(type="text")["value"],
                            '缴费基数': str(td3[1].find(type="text")["value"]).replace(',',''),
                            '缴费金额': td3[2].find(type="text")["value"],
                        }

                # 工伤缴费明细
                sCI=self.s.get("http://60.216.99.138/hsp/siHarm.do?method=queryHarmPayHis&__usersession_uuid="+uuid+"&year="+str(searchYears)+"")
                detailCI= BeautifulSoup(sCI.content, 'html.parser').find('table',{'class': 'defaultTableClass'}).findAll("tr")
                for d in range(len(detailCI)):
                    if((d+1)<len(detailCI)):
                        td4 = detailCI[d + 1].findAll("td")
                        self.result['detailCI'][td4[1].find(type="text")["value"]] = {
                            '缴费年月': td4[0].find(type="text")["value"],
                            '缴费状态': str(td4[2].find(type="text")["value"]).replace(',',''),
                        }

                # 生育缴费明细
                sBI=self.s.get("http://60.216.99.138/hsp/siBirth.do?method=queryBirthPayHis&__usersession_uuid="+uuid+"&year="+str(searchYears)+"")
                detailBI= BeautifulSoup(sBI.content, 'html.parser').find('table',{'class': 'defaultTableClass'}).findAll("tr")
                for f in range(len(detailBI)):
                    if((f+1)<len(detailBI)):
                        td5 = detailBI[f + 1].findAll("td")
                        self.result['detailBI'][td5[1].find(type="text")["value"]] = {
                            '缴费年月': td5[0].find(type="text")["value"],
                            '缴费状态': str(td5[2].find(type="text")["value"]).replace(',',''),
                        }

                self.result['key'] = id_num
                self.result['meta'] = {
                    '身份证号': id_num,
                    '登录密码': account_pass
                }

                return
            except Exception as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='id_num', name='身份证号码', cls='input'),
            dict(key='account_pass', name='密码', cls='input'),
        ], err_msg)


    def _unit_fetch_name(self):
        try:
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()

    # 371402199708176125  1314.bing
