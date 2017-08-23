#青岛社保查询 370284198904034616   892027

import requests
import hashlib
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError

MAIN_URL = 'http://221.215.38.136/grcx/work/index.do?method=level2Menu&topMenuId=1000'
LOGINONE_URL = 'http://221.215.38.136/grcx/work/m01/logincheck/valid.action'
LOGIN_URL='http://221.215.38.136/grcx/work/login.do?method=login'
VC_URL = 'http://221.215.38.136/grcx/common/checkcode.do'
BASEINFO_URl='http://221.215.38.136/grcx/work/m01/f1121/show.action'
OLDQuery_URL='http://221.215.38.136/grcx/work/m01/f1203/oldQuery.action'
medicalQuery_URL='http://221.215.38.136/grcx/work/m01/f1204/medicalQuery.action'
unemployQuery_URL='http://221.215.38.136/grcx/work/m01/f1205/unemployQuery.action'
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
        #assert 'account_num' in params, '缺少职工姓名'
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
                #account_num = params['account_num']
                password=params['password']
                vc = params['vc']
                resp=self.s.post(LOGINONE_URL,data=dict(
                     aac147=id_num
                 ))
                soup = BeautifulSoup(resp.content, 'html.parser')
                if len(soup.text)>0:
                    raise Exception(soup.text)
                else:
                    m = hashlib.md5()
                    m.update(password.encode(encoding='utf-8'))
                    hashpsw=m.hexdigest()
                    resp = self.s.post(LOGIN_URL,data = dict(
                        method='login',
                        domainId='1',
                        groupid='-95',
                        checkCode=vc,
                        loginName18=id_num,
                        loginName=id_num,
                        password=hashpsw,
                        kc02flag=''
                    ))
                    soup = BeautifulSoup(resp.content, 'html.parser')

                    if soup.select('.text3'):
                        return_message=soup.select('.text3')[0].text
                        raise Exception(return_message)
                    else:
                        print("登录成功！")

                self.result['key'] = '%s.%s' % ('real', id_num)
                self.result['meta'] = {
                    'task': 'real',
                    'id_num': id_num,
                    'password':password
                }
                return
            except Exception as e:
                err_msg = str(e)

        vc = self._new_vc()
        raise AskForParamsError([
            dict(key='id_num', name='身份证号', cls='input'),
            #dict(key='account_num', name='职工姓名', cls='input'),
            dict(key='password',name='密码',cls='input'),
            dict(key='vc', name='验证码', cls='data:image', data=vc, query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch_name(self):
        try:
            data = self.result['data']
            #基本信息
            resp=self.s.get(BASEINFO_URl)
            soup=BeautifulSoup(resp.content,'html.parser')
            zkindex=soup.select('select')[0]['value']
            data['baseinfo']={
                '职工编号' : soup.select('input')[0]['value'],
                '姓名:': soup.select('input')[1]['value'],
                '身份证号': soup.select('input')[2]['value'],
                '性别':soup.select('input')[3]['value'],
                '参加工作日期': soup.select('input')[4]['value'],
                '出生日期': soup.select('input')[5]['value'],
                '人员状态': soup.select('input')[6]['value'],
                '民 族': soup.select('input')[7]['value'],
                '特殊工种': soup.select('input')[8]['value'],
                '制卡状态': soup.find_all('option')[int(zkindex)].text,
                '发卡银行': soup.select('input')[9]['value'],
                '银行地址': soup.select('input')[10]['value'],
                '联系电话': soup.select('input')[11]['value'],
                '邮政编码':soup.select('input')[12]['value'],
                '通讯地址': soup.select('input')[13]['value']
            }
            #养老明细信息
            data['old_age']={}
            data['old_age']['data']={}
            yearkeys=''
            pageOLDQuery_URL = OLDQuery_URL
            resp = self.s.get(pageOLDQuery_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            pages = len(soup.select('.mypagelink')[0].findAll('a')) - 1
            for i in range(1,pages):
                pageOLDQuery_URL=OLDQuery_URL+'?aac001=80161738&page_active=oldQuery&page_oldQuery='+str(i)
                resp=self.s.get(pageOLDQuery_URL)
                soup=BeautifulSoup(resp.content,'html.parser')
                tab=soup.select('.main-table')[0]
                titkeys=''
                for th in tab.findAll('th'):
                    if len(titkeys)<1:
                        titkeys =th.getText()
                    else:
                        titkeys=titkeys+','+th.getText()
                for tr in tab.findAll('tr'):
                    dic = {}
                    i=0
                    monthkeys=''
                    for td in tr.findAll('td'):
                        dic.setdefault(titkeys.split(',')[i],td.getText())
                        i=i+1
                        if i==3:
                            monthkeys = td.getText()
                        if i==5:
                            if yearkeys!=monthkeys[:4] or yearkeys=='':
                                yearkeys=monthkeys[:4]
                                data['old_age']['data'][yearkeys] = {}
                        if i==10:
                            arr=[]
                            months=''
                            for (key,value) in data['old_age']['data'][yearkeys].items():
                                if key==monthkeys[-2:]:
                                    months=monthkeys[-2:]
                                    arr =value
                                else:
                                    print(key)

                            arr.append(dic)
                            if len(months)>0:
                                data['old_age']['data'][yearkeys][months]=arr
                            else:
                                data['old_age']['data'][yearkeys].setdefault(monthkeys[-2:],arr)
            #医疗明细信息
            data['medical_care'] = {}
            data['medical_care']['data'] = {}
            yearkeys = ''
            resp = self.s.get(medicalQuery_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            pages = len(soup.select('.mypagelink')[0].findAll('a')) - 1
            for i in range(1, pages):
                pageOLDQuery_URL = medicalQuery_URL + '?aac001=80161738&page_active=medicalQuery&page_medicalQuery=' + str(i)
                resp = self.s.get(pageOLDQuery_URL)
                soup = BeautifulSoup(resp.content, 'html.parser')
                tab = soup.select('.main-table')[0]
                titkeys = ''
                for th in tab.findAll('th'):
                    if len(titkeys) < 1:
                        titkeys = th.getText()
                    else:
                        titkeys = titkeys + ',' + th.getText()
                for tr in tab.findAll('tr'):
                    dic = {}
                    i = 0
                    monthkeys = ''
                    for td in tr.findAll('td'):
                        dic.setdefault(titkeys.split(',')[i], td.getText())
                        i = i + 1
                        if i == 3:
                            monthkeys = td.getText()
                        if i == 5:
                            if yearkeys!=monthkeys[:4] or yearkeys=='':
                                yearkeys=monthkeys[:4]
                                data['medical_care']['data'][yearkeys] = {}

                        if i == 10:
                            arr = []
                            months = ''
                            for (key, value) in data['medical_care']['data'][yearkeys].items():
                                if key == monthkeys[-2:]:
                                    months = monthkeys[-2:]
                                    arr = value
                                else:
                                    print(key)

                            arr.append(dic)
                            if len(months) > 0:
                                data['medical_care']['data'][yearkeys][months] = arr
                            else:
                                data['medical_care']['data'][yearkeys].setdefault(monthkeys[-2:], arr)
            #失业明细信息

            data['unemployment'] = {}
            data['unemployment']['data'] = {}
            yearkeys = ''
            resp = self.s.get(unemployQuery_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            pages = len(soup.select('.mypagelink')[0].findAll('a')) - 1
            for i in range(1, pages):
                pageunemployQuery_URL = unemployQuery_URL + '?aac001=80161738&page_active=unemployQuery&page_unemployQuery=' + str(
                    i)
                resp = self.s.get(pageunemployQuery_URL)
                soup = BeautifulSoup(resp.content, 'html.parser')
                tab = soup.select('.main-table')[0]
                titkeys = ''
                for th in tab.findAll('th'):
                    if len(titkeys) < 1:
                        titkeys = th.getText()
                    else:
                        titkeys = titkeys + ',' + th.getText()
                for tr in tab.findAll('tr'):
                    dic = {}
                    i = 0
                    monthkeys = ''
                    for td in tr.findAll('td'):
                        dic.setdefault(titkeys.split(',')[i], td.getText())
                        i = i + 1
                        if i == 4:
                            monthkeys = td.getText()
                        if i == 5:
                            if yearkeys!=monthkeys[:4] or yearkeys=='':
                                yearkeys=monthkeys[:4]
                                data['unemployment']['data'][yearkeys] = {}

                        if i == 8:
                            arr = []
                            months = ''
                            for (key, value) in data['unemployment']['data'][yearkeys].items():
                                if key == monthkeys[-2:]:
                                    months = monthkeys[-2:]
                                    arr = value
                                else:
                                    print(key)

                            arr.append(dic)
                            if len(months) > 0:
                                data['unemployment']['data'][yearkeys][months] = arr
                            else:
                                data['unemployment']['data'][yearkeys].setdefault(monthkeys[-2:], arr)

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        vc_url = VC_URL #+ datetime.now().strftime('%a %b %d %Y %H:%M:%S')
        resp = self.s.get(vc_url)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])

if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()
