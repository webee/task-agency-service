
import time
import re
import requests
from urllib import parse
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError

MAIN_URL = 'http://www.aygjj.com/gjjcx/zfbzgl/zfbzsq/main_menu.jsp'
LOGIN_URL = 'http://www.aygjj.com/gjjcx/zfbzgl/zfbzsq/login_hidden.jsp'
VC_URL = 'http://www.aygjj.com/gjjcx/zfbzgl/zfbzsq/image.jsp'
GJJMX_URL='http://www.aygjj.com/gjjcx/zfbzgl/gjjmxcx/gjjmx_cx.jsp'
GJJ_URL='http://www.aygjj.com/gjjcx/zfbzgl/zfbzsq/gjjmx_cxtwo.jsp'


class Task(AbsTaskUnitSessionTask):
    # noinspection PyAttributeOutsideInit
    def _prepare(self):
        state: dict = self.state
        self.s = requests.Session()
        cookies = state.get('cookies')
        if cookies:
            self.s.cookies = cookies
        self.s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36'
        })

        # result
        result: dict = self.result
        result.setdefault('meta', {})
        result.setdefault('data', {})

    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_name, self._unit_login)

    def _update_session_data(self):
        super()._update_session_data()
        self.state['cookies'] = self.s.cookies

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert 'id_num' in params, '缺少身份证号'
        assert 'account_num' in params, '缺少职工姓名'
        assert 'password' in params,'缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check

    def _unit_login(self, params=None):
        err_msg = None
        params
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params['id_num']
                account_num = params['account_num']
                password=params['password']
                vc = params['vc']
                data = dict(
                    cxydmc='当前年度',
                    zgzh='',
                    zgxm1=account_num,
                    sfzh=id_num,
                    password=password,
                    yzm=vc
                )
                resp = self.s.post(LOGIN_URL,data=parse.urlencode(data,encoding='gbk'),headers={'Content-Type':'application/x-www-form-urlencoded'})

                soup = BeautifulSoup(resp.content, 'html.parser')

                return_message =soup.find('head') #soup.find('input', {'name': 'zgzh'})["value"]
                if len(return_message.text)>3:
                    return_message=return_message.text.split(';')[0].split('"')[1]
                    raise Exception(return_message)
                else:
                    print("登录成功！")
                    self.zgzh=soup.find('input', {'name': 'zgzh'})["value"]
                    self.sfzh=soup.find('input', {'name': 'sfzh'})["value"]
                    self.zgxm=soup.find('input', {'name': 'zgxm'})["value"]
                    self.dwbm = soup.find('input', {'name': 'dwbm'})["value"]
                    self.cxyd=soup.find('input', {'name': 'cxyd'})["value"]
                    data2 = dict(zgzh=self.zgzh,
                                 sfzh=self.sfzh,
                                 zgxm=self.zgxm,
                                 dwbm=self.dwbm,cxyd=self.cxyd)

                    resp2 = self.s.post(MAIN_URL, data=parse.urlencode(data2, encoding='gbk'),
                                  headers={'Content-Type': 'application/x-www-form-urlencoded'})
                    soup2 = BeautifulSoup(resp2.content, 'html.parser')
                    self.html = str(resp2.content, 'gbk')

                self.result['key'] = '%s.%s' % ('real', id_num)
                self.result['meta'] = {
                    'task': 'real',
                    'id_num': id_num,
                    'password':password,
                    'account_num': account_num
                }
                return
            except Exception as e:
                err_msg = str(e)

        vc = self._new_vc()
        raise AskForParamsError([
            dict(key='id_num', name='身份证号', cls='input'),
            dict(key='account_num', name='职工姓名', cls='input'),
            dict(key='password',name='密码',cls='input'),
            dict(key='vc', name='验证码', cls='data:image', data=vc, query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch_name(self):
        try:
            data = self.result['data']
            # 基本信息
            resp = self.html
            soup = BeautifulSoup(resp, 'html.parser')
            table_text = soup.select('table.1')
            rows = table_text[0].find_all('tr')
            data['baseinfo'] = {}
            for row in rows:
                cell = [i.text for i in row.find_all('td')]
                data['baseinfo'].setdefault(cell[0],cell[1].replace('\xa0',''))
                data['baseinfo'].setdefault(cell[2], cell[3].replace('\xa0',''))



            resp = self.s.post(GJJMX_URL,data = dict(zgzh=self.zgzh,
                                 sfzh=self.sfzh,
                                 zgxm=self.zgxm,
                                 dwbm=self.dwbm,cxyd=self.cxyd),headers={'Content-Type': 'application/x-www-form-urlencoded'})
            soup = BeautifulSoup(resp.content, 'html.parser')
            data['detail'] = {}
            data['detail']['data'] = {}
            selectyear = []
            for option in soup.findAll('option'):
                selectyear.append(option.getText())
            for y in range(0,len(selectyear)):
                cxydone=selectyear[y]
                cxydtwo1=''
                if y==0:
                    cxydtwo1=selectyear[y]
                else:
                    cxydtwo1 = selectyear[y-1]
                data1={'zgzh':self.zgzh,
                           'cxydtwo':cxydone,
                           'cxydtwo':cxydtwo1,
                           'sfzh':self.sfzh,
                           'zgxm':self.zgxm,
                           'dwbm':self.dwbm,
                           'cxyd':self.cxyd}
                resp = self.s.post(GJJ_URL, data=parse.urlencode(data1, encoding='gbk'),
                                  headers={'Content-Type': 'application/x-www-form-urlencoded'})
                soup = BeautifulSoup(resp.content, 'html.parser')
                tab=soup.select('table')[16]
                tabtitle=tab.findAll('tr')[0]
                tabcontent=tab.select('.jtpsoft')
                titkeys = ''
                for td in tabtitle.findAll('td'):
                    if len(titkeys) < 1:
                        titkeys = td.getText()
                    else:
                        titkeys = titkeys + ',' + td.getText()

                for tr in range(0,len(tabcontent)):
                    dic = {}
                    i = 0
                    monthkeys = ''
                    for td in tabcontent[tr].findAll('td'):
                        dic.setdefault(titkeys.split(',')[i], td.getText())
                        i = i + 1
                        if i == 1:
                            monthkeys = td.getText()
                        if i == 6:
                            data['detail']['data'].setdefault(monthkeys,dic)
                #name = soup.select('#name')[0]['value']
                #data['name'] = name

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        vc_url = VC_URL #+ str(int(time.time() * 1000))
        resp = self.s.get(vc_url)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()
