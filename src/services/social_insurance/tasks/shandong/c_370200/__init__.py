#青岛社保查询 370284198904034616   892027

import datetime
import hashlib
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError
from services.commons import AbsFetchTask

MAIN_URL = 'http://221.215.38.136/grcx/work/index.do?method=level2Menu&topMenuId=1000'
LOGINONE_URL = 'http://221.215.38.136/grcx/work/m01/logincheck/valid.action'
LOGIN_URL='http://221.215.38.136/grcx/work/login.do?method=login'
VC_URL = 'http://221.215.38.136/grcx/common/checkcode.do'
BASEINFO_URl='http://221.215.38.136/grcx/work/m01/f1121/show.action'
OLDQuery_URL='http://221.215.38.136/grcx/work/m01/f1203/oldQuery.action'
medicalQuery_URL='http://221.215.38.136/grcx/work/m01/f1204/medicalQuery.action'
unemployQuery_URL='http://221.215.38.136/grcx/work/m01/f1205/unemployQuery.action'
STATUS_URL='http://221.215.38.136/grcx/work/m01/f1102/insuranceQuery.action'
class Task(AbsFetchTask):
    task_info = dict(
        city_name="青岛",
        help="""<li>首次登录初始密码为老卡的个人编号（磁条）或新卡的社会保障卡号（芯片）；如果老卡（磁条）的个人编号最前一位是0，输入密码时需去掉0。</li>
            <li>如忘记密码，可到青岛社保网上查询平台中的“忘记密码”进行密码重置或到参保所在社会保险经办机构申请密码初始化。</li>"""
    )
    def _get_common_headers(self):
        return { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36'
        }
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
        assert '身份证号' in params, '缺少身份证号'
        #assert 'account_num' in params, '缺少职工姓名'
        assert '密码' in params,'缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check
    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '身份证号' not in params:
                params['身份证号'] = meta.get('身份证号')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '身份证号' and '身份证号' in meta:
                continue
            elif pr['key'] == '密码' and '密码' in meta:
                continue
            res.append(pr)
        return res
    def _unit_login(self, params=None):
        err_msg = None
        params
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params['身份证号']
                #account_num = params['account_num']
                password=params['密码']
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

                self.result_key = id_num
                self.result_meta['身份证号'] = id_num
                self.result_meta['密码'] = password
                self.result_identity['task_name'] = '青岛'
                self.result_identity['target_id'] = id_num
                return
            except Exception as e:
                err_msg = str(e)

        vc = self._new_vc()
        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input', value=params.get('身份证号', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}, value=params.get('vc', '')),
        ], err_msg)

    def _unit_fetch_name(self):
        try:
            data = self.result_data
            #基本信息
            resp=self.s.get(BASEINFO_URl)
            soup=BeautifulSoup(resp.content,'html.parser')
            zkindex=soup.select('select')[0]['value']
            data['baseInfo']={
                '社保编号' : soup.select('input')[0]['value'],
                '姓名': soup.select('input')[1]['value'],
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
                '通讯地址': soup.select('input')[13]['value'],
                "更新时间": datetime.datetime.now().strftime('%Y-%m-%d'),
                '城市名称': '青岛',
                '城市编号': '370200'
            }

            resp = self.s.get(STATUS_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            tabs = soup.select('.main-table')[0]
            arrstatus={}
            idstatus='停缴'
            for tr in tabs.findAll('tr'):
                cell = [i.text for i in tr.find_all('td')]
                if len(cell)>2:
                    strss='停缴'
                    if cell[3]=='参保缴费':
                        idstatus='正常参保'
                        strss='正常参保'
                    arrstatus.setdefault(cell[2].replace('保险', '').replace('企业', '').replace('基本', ''),strss)

            data['baseInfo'].setdefault('五险状态', arrstatus)
            self.result_identity['target_name']=soup.select('input')[1]['value']
            self.result_identity['status']=idstatus
            #养老明细信息
            data['old_age']={}
            data['old_age']['data']={}
            arrtime=[]
            oldsum=0.00
            yearkeys=''
            pageOLDQuery_URL = OLDQuery_URL
            resp = self.s.get(pageOLDQuery_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            pages = len(soup.select('.mypagelink')[0].findAll('a'))
            for i in range(1,pages):
                pageOLDQuery_URL=OLDQuery_URL+'?aac001=80161738&page_active=oldQuery&page_oldQuery='+str(i)
                resp=self.s.get(pageOLDQuery_URL)
                soup=BeautifulSoup(resp.content,'html.parser')
                tab=soup.select('.main-table')[0]
                titkeys=[]
                for th in tab.findAll('th'):
                    titlename = th.getText().replace(' ', '')
                    if titlename == '缴费年月':
                        titlename = '缴费时间'
                    if titlename == '个人基数':
                        titlename = '缴费基数'
                    if titlename == '单位名称':
                        titlename = '缴费单位'
                    titkeys.append(titlename)
                for tr in tab.findAll('tr'):
                    dic = {}
                    i=0
                    monthkeys=''
                    for td in tr.findAll('td'):
                        dic.setdefault(titkeys[i],td.getText())
                        i=i+1
                        if i==3:
                            monthkeys = td.getText()
                        if i==5:
                            if yearkeys!=monthkeys[:4] or yearkeys=='':
                                yearkeys=monthkeys[:4]
                                data['old_age']['data'][yearkeys] = {}
                        if i == 7:
                            oldsum+=float(td.getText())
                        if i==10:
                            arr=[]
                            months=''
                            for (key,value) in data['old_age']['data'][yearkeys].items():
                                if key==monthkeys[-2:]:
                                    months=monthkeys[-2:]
                                    arr =value
                            dic.setdefault('公司缴费', '')
                            arr.append(dic)
                            if len(months)>0:
                                data['old_age']['data'][yearkeys][months]=arr
                            else:
                                arrtime.append(monthkeys)
                                data['old_age']['data'][yearkeys].setdefault(monthkeys[-2:],arr)
            data['baseInfo'].setdefault('缴费时长',str(len(arrtime)))
            data['baseInfo'].setdefault('最近缴费时间',max(arrtime))
            data['baseInfo'].setdefault('开始缴费时间',min(arrtime))
            data['baseInfo'].setdefault('个人养老累计缴费', oldsum)
            #医疗明细信息
            data['medical_care'] = {}
            data['medical_care']['data'] = {}
            yearkeys = ''
            yilsum=0.00
            resp = self.s.get(medicalQuery_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            pages = len(soup.select('.mypagelink')[0].findAll('a'))
            for i in range(1, pages):
                pageOLDQuery_URL = medicalQuery_URL + '?aac001=80161738&page_active=medicalQuery&page_medicalQuery=' + str(i)
                resp = self.s.get(pageOLDQuery_URL)
                soup = BeautifulSoup(resp.content, 'html.parser')
                tab = soup.select('.main-table')[0]
                titkeys =[]
                for th in tab.findAll('th'):
                    titlename = th.getText().replace(' ', '')
                    if titlename == '缴费年月':
                        titlename = '缴费时间'
                    if titlename == '个人基数':
                        titlename = '缴费基数'
                    if titlename == '单位名称':
                        titlename = '缴费单位'
                    titkeys.append(titlename)
                for tr in tab.findAll('tr'):
                    dic = {}
                    i = 0
                    monthkeys = ''
                    for td in tr.findAll('td'):
                        dic.setdefault(titkeys[i], td.getText())
                        i = i + 1
                        if i == 3:
                            monthkeys = td.getText()
                        if i == 5:
                            if yearkeys!=monthkeys[:4] or yearkeys=='':
                                yearkeys=monthkeys[:4]
                                data['medical_care']['data'][yearkeys] = {}
                        if i == 10:
                            yilsum+=float(td.getText())
                            arr = []
                            months = ''
                            for (key, value) in data['medical_care']['data'][yearkeys].items():
                                if key == monthkeys[-2:]:
                                    months = monthkeys[-2:]
                                    arr = value
                            dic.setdefault('公司缴费', '')
                            arr.append(dic)
                            if len(months) > 0:
                                data['medical_care']['data'][yearkeys][months] = arr
                            else:
                                data['medical_care']['data'][yearkeys].setdefault(monthkeys[-2:], arr)
            data['baseInfo'].setdefault('个人医疗累计缴费', yilsum)
            #失业明细信息

            data['unemployment'] = {}
            data['unemployment']['data'] = {}
            yearkeys = ''
            resp = self.s.get(unemployQuery_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            pages = len(soup.select('.mypagelink')[0].findAll('a'))
            for i in range(1, pages):
                pageunemployQuery_URL = unemployQuery_URL + '?aac001=80161738&page_active=unemployQuery&page_unemployQuery=' + str(
                    i)
                resp = self.s.get(pageunemployQuery_URL)
                soup = BeautifulSoup(resp.content, 'html.parser')
                tab = soup.select('.main-table')[0]
                titkeys =[]
                for th in tab.findAll('th'):
                    titlename = th.getText().replace(' ', '')
                    if titlename == '缴费年月':
                        titlename = '缴费时间'
                    if titlename == '个人基数':
                        titlename = '缴费基数'
                    if titlename == '单位名称':
                        titlename = '缴费单位'
                    titkeys.append(titlename)
                for tr in tab.findAll('tr'):
                    dic = {}
                    i = 0
                    monthkeys = ''
                    for td in tr.findAll('td'):
                        dic.setdefault(titkeys[i], td.getText())
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
                            dic.setdefault('公司缴费', '')
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
