# cff---厦门  社保信息

import time
import requests
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError
import ssl
import urllib3
import re

MAIN_URL = r'https://app.xmhrss.gov.cn/UCenter/index_grjbxx.xhtml'
LOGIN_URL = r"https://app.xmhrss.gov.cn/login.xhtml"
VC_URL = r"https://app.xmhrss.gov.cn/vcode.xhtml"
Detail_URL=r"https://app.xmhrss.gov.cn/UCenter/sbjfxxcx.xhtml"

class Task(AbsTaskUnitSessionTask):

    def _prepare(self):
        requests.packages.urllib3.disable_warnings()

        state: dict = self.state
        self.s = requests.Session()
        cookies = state.get('cookies')
        if cookies:
            self.s.cookies = cookies
        self.s.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36',
                'Accept-Encoding':'gzip, deflate, sdch',
                'Host': 'app.xmhrss.gov.cn',
        })

        # result
        result: dict = self.result
        result.setdefault('key',{})
        result.setdefault('meta', {})
        result.setdefault('data', {})

        result.setdefault('detailEI',{})     #养老
        result.setdefault('detailHI',{})     #医疗
        result.setdefault('detailII',{})     #失业
        result.setdefault('detailCI',{})     #工伤
        result.setdefault('detailBI',{})     #生育
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
        resp = self.s.get(VC_URL,verify=False)
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
                    'id0000':id_num,
                    'userpwd':account_pass,
                    'validateCode':vc,
                    'date':str(time.time()*1000)[0:13]
                }
                resp = self.s.post("https://app.xmhrss.gov.cn/login_dowith.xhtml", data=data)

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
            dict(key='id_num', name='社会保险号', cls='input'),
            dict(key='account_pass', name='登录密码', cls='input'),
            dict(key='vc', name='验证码', cls='data:image', data=vc, query={'t': 'vc'}),
        ], err_msg)


    def _unit_fetch_name(self):
        try:
            resp=self.s.get(MAIN_URL)
            soup=BeautifulSoup(resp.content,'html.parser')
            data=soup.find('table',{'class':'tab3'}).findAll('tr')
            self.result['data']['baseInfo']={
                '姓名':data[0].findAll('td')[1].text,
                '保险号':data[1].findAll('td')[1].text,
                '社会保障卡卡号':data[2].findAll('td')[1].text,
                '单位名称':data[4].findAll('td')[1].text,
                '个人身份':data[7].findAll('td')[1].text,
                '工作状态':data[8].findAll('td')[1].text,
            }

            # 设置identity
            identity = self.result['identity']
            identity.update({
                'task_name': '厦门市',
                'target_name': data[0].findAll('td')[1].text,
                'target_id': self.result['meta']["身份证号"],
                'status': "",
            })


            # 社保明细-----医疗
            startDate=input("请输入需要查询的开始时间：")
            endDate=input("请输入需要查询的结束时间：")

            detailHI=self.s.get(Detail_URL+"?xzdm00=1&zmlx00=&qsnyue="+startDate+"&jznyue="+endDate+"")
            sHI=BeautifulSoup(detailHI.content,'html.parser').find('table',{'class':'tab5'}).findAll("tr")
            for a in range(len(sHI)):
                tds = sHI[a].findAll('td')
                self.result['detailHI'][str(re.sub('\s','',tds[3].text))]={
                    '缴费年月':re.sub('\s','',tds[3].text),
                    '缴费基数':re.sub('\s','',tds[7].text),
                    '缴费状态':re.sub('\s','',tds[2].text),
                    '缴费合计':re.sub('\s','',tds[5].text),
                }

            # 社保明细-----养老
            detailEI=self.s.get(Detail_URL+"?xzdm00=2&zmlx00=&qsnyue="+startDate+"&jznyue="+endDate+"")
            sEI=BeautifulSoup(detailEI.content,'html.parser').find('table',{'class':'tab5'}).findAll("tr")
            for b in range(len(sEI)):
                td2=sEI[b].findAll('td')
                self.result['detailEI'][str(re.sub('\s','',td2[3].text))]={
                    '缴费年月': re.sub('\s', '', td2[3].text),
                    '缴费基数': re.sub('\s', '', td2[7].text),
                    '缴费状态': re.sub('\s', '', td2[2].text),
                    '缴费合计': re.sub('\s', '', td2[5].text)
                }

            # 社保明细-----工伤
            detailCI=self.s.get(Detail_URL+"?xzdm00=3&zmlx00=&qsnyue="+startDate+"&jznyue="+endDate+"")
            sCI=BeautifulSoup(detailCI.content,'html.parser').find('table',{'class':'tab5'}).findAll("tr")
            for c in range(len(sCI)):
                td3=sCI[c].findAll('td')
                self.result['detailCI'][str(re.sub('\s','',td3[3].text))]={
                    '缴费年月': re.sub('\s', '', td3[3].text),
                    '缴费基数': re.sub('\s', '', td3[7].text),
                    '缴费状态': re.sub('\s', '', td3[2].text),
                    '缴费合计': re.sub('\s', '', td3[5].text)
                }

            # 社保明细-----失业
            detailII=self.s.get(Detail_URL+"?xzdm00=4&zmlx00=&qsnyue="+startDate+"&jznyue="+endDate+"")
            sII=BeautifulSoup(detailII.content,'html.parser').find('table',{'class':'tab5'}).findAll("tr")
            for d in range(len(sII)):
                td4=sII[d].findAll('td')
                self.result['detailII'][str(re.sub('\s','',td4[3].text))]={
                    '缴费年月': re.sub('\s', '', td4[3].text),
                    '缴费基数': re.sub('\s', '', td4[7].text),
                    '缴费状态': re.sub('\s', '', td4[2].text),
                    '缴费合计': re.sub('\s', '', td4[5].text)
                }

            # 社保明细-----生育
            detialBI=self.s.get(Detail_URL+"?xzdm00=5&zmlx00=&qsnyue="+startDate+"&jznyue="+endDate+"")
            sBI=BeautifulSoup(detialBI.content,'html.parser').find('table',{'class':'tab5'}).findAll("tr")
            for f in range(len(sBI)):
                td5=sBI[d].findAll('td')
                self.result['detailBI'][str(re.sub('\s','',td5[3].text))]={
                    '缴费年月': re.sub('\s', '', td5[3].text),
                    '缴费基数': re.sub('\s', '', td5[7].text),
                    '缴费状态': re.sub('\s', '', td5[2].text),
                    '缴费合计': re.sub('\s', '', td5[5].text)
                }

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient
    client = TaskTestClient(Task())
    client.run()

    # 350524196209146816  123789
