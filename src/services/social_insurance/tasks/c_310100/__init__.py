# cff---上海  社保信息

import time
import requests
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError
import json

MAIN_URL = r''
LOGIN_URL = r"http://www.12333sh.gov.cn/sbsjb/wzb/129.jsp"
VC_URL = r"http://www.12333sh.gov.cn/sbsjb/wzb/Bmblist.jsp"


class Task(AbsTaskUnitSessionTask):

    def _prepare(self):
        state: dict = self.state
        self.s = requests.Session()
        cookies = state.get('cookies')
        if cookies:
            self.s.cookies = cookies
        self.s.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36',
                'Accept-Encoding':'gzip, deflate',
                'Host': 'www.12333sh.gov.cn',
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
        resp = self.s.get(VC_URL)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])


    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:

                id_num = params['id_num']
                account_pass = params['account_pass']
                vc = params['vc']

                data={
                    'userid':id_num,
                    'userpw':account_pass,
                    'userjym':vc
                }
                resp = self.s.post("http://www.12333sh.gov.cn/sbsjb/wzb/dologin.jsp", data=data)

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


    def _match_money(self,dtime1,dtime2,fmoney):
        if(dtime1==dtime2):
            return fmoney
        else:
            return ""

    def _match_commapy(self,dtime,dt):
        rescom=""
        for tr in range(len(dt)):
            trd=dt[tr].find('jfsj').text.split('-')
            if(trd[0]<=dtime<=trd[1]):
                rescom=dt[tr].find('jfdw').text

        return rescom


    def _unit_fetch_name(self):
        try:
            resp=self.s.get("http://www.12333sh.gov.cn/sbsjb/wzb/sbsjbcx.jsp")
            soup=BeautifulSoup(resp.content,'html.parser')
            years=soup.find('xml',{'id':'dataisxxb_sum3'}).findAll("jsjs")

            self.result['data']['baseInfo']={
                '姓名':soup.find('xm').text,
                '身份证号':soup.find('zjhm').text,
                '更新时间':time.strftime("%Y-%m-%d",time.localtime()),
                '城市名称':'上海市',
                '城市编号':'310100',
                '缴费时长':soup.find('xml',{'id':'dataisxxb_sum4'}).find('jsjs2').text,
                '最近缴费时间':years[len(years)-1].find('jsjs1').text,
                #'开始缴费时间':'',
                '个人养老累积缴费':soup.find('xml',{'id':'dataisxxb_sum4'}).find('jsjs3').text,
                #'个人医疗累积缴费':''
            }

            # 社保缴费明细
            # 养老
            self.result['data']['old_age']={
                "data":{}
            }
            dataBaseE=self.result['data']['old_age']["data"]
            modelE={}

            details=soup.find('xml',{'id':'dataisxxb_sum2'}).findAll("jsjs")
            dt = soup.findAll("jfdwinfo")

            for a in range(len(years)):
                yearE=details[a].find('jsjs1').text[0:4]
                monthE=details[a].find('jsjs1').text[4:6]

                dataBaseE.setdefault(yearE,{})
                dataBaseE[yearE].setdefault(monthE,[])

                modelE={
                    '缴费年月':details[a].find('jsjs1').text,
                    '缴费单位':self._match_commapy(details[a].find('jsjs1').text,dt),
                    '缴费基数':details[a].find('jsjs3').text,
                    '应缴金额':details[a].find('jsjs4').text,
                    '实缴金额':self._match_money(details[a].find('jsjs1').text,years[a].find('jsjs1').text,years[a].find('jsjs3').text)
                }
                dataBaseE[yearE][monthE].append(modelE)


            # 医疗
            self.result['data']['medical_care'] = {
                "data": {}
            }
            dataBaseH = self.result['data']['medical_care']["data"]
            modelH = {}

            for b in range(len(details)):
                yearH = details[b].find('jsjs1').text[0:4]
                monthH = details[b].find('jsjs1').text[4:6]

                dataBaseH.setdefault(yearH, {})
                dataBaseH[yearH].setdefault(monthH, [])

                modelH = {
                    '缴费年月': details[b].find('jsjs1').text,
                    '缴费单位': self._match_commapy(details[b].find('jsjs1').text, dt),
                    '缴费基数': details[b].find('jsjs3').text,
                    '应缴金额': details[b].find('jsjs6').text,
                    #'实缴金额':''
                }
                dataBaseH[yearH][monthH].append(modelH)


            # 失业
            self.result['data']['unemployment'] = {
                "data": {}
            }
            dataBaseI = self.result['data']['unemployment']["data"]
            modelI = {}

            for c in range(len(details)):
                yearI = details[c].find('jsjs1').text[0:4]
                monthI = details[c].find('jsjs1').text[4:6]

                dataBaseI.setdefault(yearI, {})
                dataBaseI[yearI].setdefault(monthI, [])

                modelI = {
                    '缴费年月': details[c].find('jsjs1').text,
                    '缴费单位': self._match_commapy(details[c].find('jsjs1').text, dt),
                    '缴费基数': details[c].find('jsjs3').text,
                    '应缴金额': details[c].find('jsjs8').text,
                    #'实缴金额': ''
                }
                dataBaseI[yearI][monthI].append(modelI)


            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()

    # 321322199001067241  123456       5002931643   123456
