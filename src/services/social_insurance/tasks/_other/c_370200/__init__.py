# cff---青岛  社保信息

import time
import requests
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError
import hashlib

MAIN_URL = r'http://221.215.38.136/grcx/work/m01/f1121/show.action?'
LOGIN_URL = r"http://221.215.38.136/grcx/work/login.do"
VC_URL = r"http://221.215.38.136/grcx/common/checkcode.do"


class Task(AbsTaskUnitSessionTask):

    def _prepare(self):
        state: dict = self.state
        self.s = requests.Session()
        cookies = state.get('cookies')
        if cookies:
            self.s.cookies = cookies
        self.s.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; rv:54.0) Gecko/20100101 Firefox/54.0',
                'Accept-Encoding':'gzip, deflate',
                'Host': '221.215.38.136',
        })

        # result
        result: dict = self.result
        result.setdefault('key',{})
        result.setdefault('meta', {})
        result.setdefault('data', {})

        result.setdefault('detailEI',{})    #养老
        result.setdefault('detailHI',{})    #医疗
        result.setdefault('detailII',{})    #失业
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
        vc_url = VC_URL
        resp = self.s.get(vc_url)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])

    def _unit_login(self, params=None):
        err_msg = None
        if params:
            # 非开始或者开始就提供了参数
            try:

                id_num = params['id_num']
                account_pass = params['account_pass']
                vc = params['vc']

                m=hashlib.md5()
                m.update(str(account_pass).encode(encoding="utf-8"))
                pw=m.hexdigest()

                data={
                    'checkCode': vc,
                    'domainId': '1',
                    'groupid': '-95',
                    'kc02flag': '',
                    'loginName': id_num,
                    'loginName18': id_num,
                    'method': 'login',
                    'password': pw
                }
                resp = self.s.post(LOGIN_URL, data=data)
                tm=str(resp.url.split('&')[2]).replace('_t=','')

                self.result['key'] = id_num
                self.result['meta'] = {
                    '身份证号': id_num,
                    '登录密码': account_pass
                }

                res=self.s.get(MAIN_URL+"_t="+tm)
                soup=BeautifulSoup(res.content,'html.parser')
                data=soup.find('table',{'class':'table_box'}).findAll("tr")
                tr1=data[4].findAll("td")
                tr2=data[5].findAll("td")
                tr3=data[6].findAll("td")

                self.result['data']['userInfo']={
                    '职工编号':tr1[1].find(type='text')['value'],
                    '姓名':tr1[3].find(type='text')['value'],
                    '身份证号':tr1[5].find(type='text')['value'],

                    '性别':tr2[1].find(type='text')['value'],
                    '出生日期':tr2[5].find(type='text')['value'],

                    '人员状态':tr3[1].find(type='text')['value'],
                    '民族':tr3[3].find(type='text')['value'],
                }

                # 设置identity
                identity = self.result['identity']
                identity.update({
                    'task_name': '济南市',
                    'target_name': tr1[3].find(type='text')['value'],
                    'target_id': self.result['meta']["身份证号"],
                    'status': "",
                })


                # 养老缴费明细
                detailEI=self.s.get("http://221.215.38.136/grcx/work/m01/f1203/oldQuery.action")
                sEI=BeautifulSoup(detailEI.content,'html.parser').find('table',{'class':'main-table'}).findAll('tr')
                for a in range(len(sEI)-3):
                    std=sEI[a].findAll('td')
                    self.result['detailEI'][str(std[1].text)]={
                        '缴费单位':std[3].text,
                        '缴费年月': std[1].text,
                        '缴费基数': std[5].text,
                        '缴费状态': std[4].text,
                        '个人缴存额': std[6].text,
                    }

                # 医疗缴费明细
                detailHI=self.s.get("http://221.215.38.136/grcx/work/m01/f1204/medicalQuery.action")
                sHI=BeautifulSoup(detailHI.content,'html.parser').find('table',{'class':'main-table'}).findAll('tr')
                for b in range(len(sHI)-2):
                    tds=sHI[b].findAll('td')
                    self.result['detailHI'][str(tds[1].text)]={
                        '缴费单位': tds[3].text,
                        '缴费年月': tds[1].text,
                        '缴费基数': tds[5].text,
                        '缴费状态': tds[4].text,
                        '个人缴存额': tds[6].text,
                    }

                # 失业缴费明细
                detailII=self.s.get("http://221.215.38.136/grcx/work/m01/f1205/unemployQuery.action")
                sII=BeautifulSoup(detailII.content,'html.parser').find('table',{'class':'main-table'}).findAll('tr')
                for c in range(len(sII)-1):
                    stds=sII[c].findAll('td')
                    self.result['detailII'][str(stds[2].text)]={
                        '缴费单位': stds[1].text,
                        '缴费年月': stds[2].text,
                        '缴费基数': stds[5].text,
                        '缴费状态': stds[4].text,
                        '个人缴存额': stds[6].text,
                    }

                return
            except Exception as e:
                err_msg = str(e)

        vc = self._new_vc()
        raise AskForParamsError([
            dict(key='id_num', name='身份证号', cls='input'),
            dict(key='account_pass', name='登录密码', cls='input'),
            dict(key='vc', name='验证码', cls='data:image', data=vc, query={'t': 'vc'}),
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

    # 370284198904034616  892027    840c316352141350ef72014656b96102
