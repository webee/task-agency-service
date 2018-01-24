import time,datetime
import operator
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask
from bs4 import BeautifulSoup

LOGIN_URL = 'http://www.hzgjj.gov.cn:8080/WebAccounts/userLogin.do'
VC_URL='http://www.hzgjj.gov.cn:8080/WebAccounts/codeMaker'
INFOR_URL='http://www.hzgjj.gov.cn:8080/WebAccounts/userModify.do'
ENRER_URL='http://www.hzgjj.gov.cn:8080/WebAccounts/perComInfo.do'
YE_URL='http://www.hzgjj.gov.cn:8080/WebAccounts/perComInfo.do?flag=1'
DZD_URL='http://www.hzgjj.gov.cn:8080/WebAccounts/perBillDetial.do'

class Task(AbsFetchTask):
    task_info = dict(
        city_name="杭州",
        help="""<li>个人客户号作为办理业务的唯一编号，可通过询问单位经办人或本人携带本人身份证到本中心查询的方式获取。</li>
        <li>在获取到个人客户号后，请到杭州公积金管理中心官网网完成“注册”然后再登录。</li>""",
        developers=[{'name':'卜圆圆','email':'byy@qinqinxiaobao.com'}]
    )

    def _get_common_headers(self):
        return {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3100.0 Safari/537.36'}

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert 'other' in params, '请选择登录方式'
        if params["other"] == "1":
            assert 'bh1' in params, '缺少客户号'
            assert 'mm1' in params, '缺少密码'
        elif params["other"] == "3":
            assert 'bh3' in params, '缺少用户名'
            assert 'mm3' in params, '缺少密码'
        elif params["other"] == "4":
            assert 'bh4' in params, '缺少市民邮箱'
            assert 'mm4' in params, '缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check
        if params["other"] == "1":
            用户名 = params['bh1']
        elif params["other"] == "3":
            用户名 = params['bh3']
        elif params["other"] == "4":
            用户名 = params['bh4']
        if params["other"] == "1":
            密码 = params['mm1']
        elif params["other"] == "3":
            密码 = params['mm3']
        elif params["other"] == "4":
            密码 = params['mm4']

        if len(密码) < 4:
            raise InvalidParamsError('用户名或密码错误')
        if len(用户名) < 5:
            raise InvalidParamsError('登陆名错误')
        if '@' in 用户名:
            if not 用户名.endswith('@hz.cn'):
                raise InvalidParamsError('市民邮箱错误')
            return

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if 'bh1' not in params:
                params['bh1'] = meta.get('客户号')
            if 'mm1' not in params:
                params['mm1'] = meta.get('密码')
            if 'bh3' not in params:
                params['bh3'] = meta.get('用户名')
            if 'mm3' not in params:
                params['mm3'] = meta.get('密码')
            if 'bh4' not in params:
                params['bh4'] = meta.get('市民邮箱')
            if 'mm4' not in params:
                params['mm4'] = meta.get('密码')
            if 'other' not in params:
                params['other'] = meta.get('类型Code')
        return params
    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            # 用户名
            if meta['类型Code'] == '3':
                if pr['key'] == 'bh3':
                    continue
                if pr['key'] == 'mm3':
                    continue
                if pr['key'] == 'bh1' and '客户号' in meta:
                    continue
                elif pr['key'] == 'mm1' and '密码' in meta:
                    continue
                if pr['key'] == 'bh4' and '市民邮箱' in meta:
                    continue
                elif pr['key'] == 'mm4' and '密码' in meta:
                    continue
                res.append(pr)
            # 客户号
            elif meta['类型Code'] == '1':
                if pr['key'] == 'bh1':
                    continue
                if pr['key'] == 'mm1':
                    continue
                if pr['key'] == 'bh3' and '用户名' in meta:
                    continue
                elif pr['key'] == 'mm3' and '密码' in meta:
                    continue
                if pr['key'] == 'bh4' and '市民邮箱' in meta:
                    continue
                elif pr['key'] == 'mm4' and '密码' in meta:
                    continue
                res.append(pr)
            # 客户号
            elif meta['类型Code'] == '4':
                if pr['key'] == 'bh1':
                    continue
                if pr['key'] == 'mm1':
                    continue
                if pr['key'] == 'bh3' and '用户名' in meta:
                    continue
                elif pr['key'] == 'mm3' and '密码' in meta:
                    continue
                if pr['key'] == 'bh4' and '市民邮箱' in meta:
                    continue
                elif pr['key'] == 'mm4' and '密码' in meta:
                    continue
                res.append(pr)
            else:
                res.append(pr)
        return res
    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_name, self._unit_login)
    def _unit_login(self, params: dict):
        err_msg = None
        params
        if params:
            try:
                self._check_login_params(params)
                if params["other"] == "3":
                    code = "3"
                elif params["other"] == "1":
                    code = "1"
                else:
                    code = "4"
                id_num = params['bh' + code]
                password = params['mm' + code]
                vc = params['vc']
                data={
                    'cust_no':id_num,
                    'password': password,
                    'validate_code': vc,
                    'cust_type': '2',
                    'user_type': code
                }
                resp = self.s.post(LOGIN_URL, data=data, timeout=20)
                soup = BeautifulSoup(resp.content, 'html.parser')
                datas = {
                    'cust_no': id_num,
                    'flag':soup.text,
                    'password': password,
                    'validate_code': vc,
                    'cust_type': '2',
                    'user_type': code
                }
                resp = self.s.post(LOGIN_URL, data=datas, timeout=20)
                soup = BeautifulSoup(resp.content, 'html.parser')

                if soup.text=='2':
                    err_msg='验证码不正确！'
                elif soup.text=='-1':
                    err_msg='用户名或密码不正确！'
                if err_msg:
                    raise InvalidParamsError(err_msg)

                self.result_key = id_num
                self.result_meta['用户名'] = id_num
                self.result_meta['密码'] = password
                self.result_meta['类型Code'] = params["other"]
                self.result_identity['task_name'] = '杭州'

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='other',
                name = '[{"tabName":"客户号","tabCode":"1","isEnable":"1"},{"tabName":"用户名","tabCode":"3","isEnable":"1"},{"tabName":"市民邮箱","tabCode":"4","isEnable":"1"}]',
                       cls = 'tab', value = params.get('类型Code', '')),
            dict(key='bh1', name='客户号', cls='input', tabCode="1", value=params.get('用户名', '')),
            dict(key='mm1', name='密码', cls='input:password', tabCode="1", value=params.get('密码', '')),
            dict(key='bh3', name='用户名', cls='input', tabCode="3", value=params.get('用户名', '')),
            dict(key='mm3', name='密码', cls='input:password', tabCode="3", value=params.get('密码', '')),
            dict(key='bh4', name='市民邮箱', cls='input', tabCode="4", value=params.get('用户名', '')),
            dict(key='mm4', name='密码', cls='input:password', tabCode="4", value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}, tabCode="[1,3,4]", value=''),
        ], err_msg)

    def _unit_fetch_name(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            #基本信息
            resp = self.s.get(INFOR_URL, timeout=25)
            soup = BeautifulSoup(resp.content, 'html.parser')
            table = soup.select('table')[0].findAll('input')
            data = self.result_data
            data['baseInfo'] = {
                '城市名称': '杭州',
                '城市编号': '330100',
                '证件类型': '身份证',
                '证件号': table[3].attrs['value'],
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '手机号': table[0].attrs['value'],
                '个人账号': table[1].attrs['value'],
                '姓名': table[2].attrs['value'],
                '邮箱': table[12].attrs['value'],
                '用户名': table[8].attrs['value'],
                '地址': table[13].attrs['value'],
                '邮编': table[14].attrs['value']
            }
            #企业信息
            resp = self.s.get(ENRER_URL, timeout=25)
            soup = BeautifulSoup(resp.content, 'html.parser')
            table = soup.select('table')[0]
            enterarr=[]   #企业
            statearr=[]   #状态
            y=1     #获取链接
            timeenter={}   #明细时间对应的企业
            maxtimes=[]

            data['companyList'] = []
            for tr in table.findAll('tr'):
                cell = [i.text.replace(' ','') for i in tr.find_all('td')]
                if len(cell):
                    enterarr.append(cell[3])
                    statearr.append(cell[7])
                    dictenter={
                        '单位名称':cell[3],
                        '当前余额':0,
                        '帐户状态':cell[7]
                    }
                    if y<=len(table.findAll('a')):
                        urlinfo='http://www.hzgjj.gov.cn:8080'+table.findAll('a')[y].attrs['href']
                        resps = self.s.get(urlinfo, timeout=25)
                        soups = BeautifulSoup(resps.content, 'html.parser')
                        tables = soups.select('table')[0]
                        timearr=[]
                        for tr in tables.findAll('tr'):
                            cells = [i.text.replace(' ', '') for i in tr.find_all('td')]
                            if len(cells):
                                timearr.append(cells[1])
                                timeenter.setdefault(cells[1],cell[3])
                        y=y+2
                        dictenter.setdefault('最后业务日期',max(timearr))
                        maxtimes.append(max(timearr))
                        data['companyList'].append(dictenter)
                    data['companyList'].sort(key=operator.itemgetter('最后业务日期'),reverse=True)


            if '正常' in statearr:
                self.result_identity['status'] ='缴存'
            else:
                self.result_identity['status'] ='封存'
            self.result_identity['target_name'] = data['baseInfo']['姓名']
            #对账单
            resp = self.s.get(YE_URL, timeout=25)
            soup = BeautifulSoup(resp.content, 'html.parser')
            yuer=soup.findAll('td')[3].text
            data['baseInfo'].setdefault('当前余额',yuer)
            data['companyList'][0]['当前余额'] = yuer
            axx=soup.find('a').attrs['href']
            urlinfo = 'http://www.hzgjj.gov.cn:8080' + axx
            resps = self.s.get(urlinfo, timeout=25)
            soups = BeautifulSoup(resps.content, 'html.parser')
            tables = soups.select('input')
            if len(tables)>3:
                data['baseInfo']['证件号']=tables[3].attrs['value']
                self.result_identity['target_id'] = tables[3].attrs['value']
            data['detail'] = {}
            data['detail']['data'] = {}
            years = ''
            months = ''
            hjje = ''
            hjrq = ''
            hjcs = 0
            for i in range(1998,int(datetime.datetime.now().year+1)):
                datas={
                    'check_ym': i,
                    'button1': '',
                    'acct_no': tables[1].attrs['value'],
                    'cacct_no':tables[2].attrs['value'],
                    'cert_code':tables[3].attrs['value'],
                    'fund_type': tables[4].attrs['value'],
                    'cname':tables[5].attrs['value'],
                    'flag':tables[6].attrs['value'],
                    'begin_date': str(i)+'0101',
                    'end_date': str(i)+'1231'
                    }

                resp = self.s.post(DZD_URL,data=datas, timeout=25)
                soup = BeautifulSoup(resp.content, 'html.parser')
                table = soup.select('table')[0]
                for tr in table.findAll('tr'):
                    cell = [i.text.replace(' ', '') for i in tr.find_all('td')]
                    if len(cell)>2 and cell[1]:
                        arr = []
                        hj = ''
                        hjdw=''
                        lx = cell[2]
                        if '汇缴' in lx:
                            hj =lx[-6:]
                            lx =lx[:2]
                            if max(maxtimes)==hj:
                                hjrq=hj
                                hjje=cell[3]
                        else:
                            lx = cell[2]
                        if hj:
                            hjcs = hjcs + 1
                            hjdw=timeenter[hj]
                        dic = {
                            '时间': cell[1],
                            '单位名称': hjdw,
                            '支出': cell[4],
                            '收入': cell[3],
                            '汇缴年月': hj,
                            '余额': cell[5],
                            '类型': lx
                        }
                        times = cell[1][0:6]
                        if years != times[:4]:
                            years = times[:4]
                            data['detail']['data'][years] = {}
                            if months != times[-2:]:
                                months = times[-2:]
                                data['detail']['data'][years][months] = {}
                        else:
                            if months != times[-2:]:
                                months = times[-2:]
                                data['detail']['data'][years][months] = {}
                            else:
                                arr = data['detail']['data'][years][months]
                        arr.append(dic)
                        data['detail']['data'][years][months] = arr
            data['baseInfo']['最近汇缴日期'] = hjrq
            data['baseInfo']['最近汇缴金额'] = hjje
            data['baseInfo']['累计汇缴次数'] = hjcs
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)
    def _new_vc(self):
        resp = self.s.get(VC_URL)
        return dict(cls='data:image', content=resp.content)


if __name__ == '__main__':
    from services.client import TaskTestClient
    meta = {'类型Code':1,'客户号': '100177149008', '密码': 'W862419B','用户名':'','密码':'','市民邮箱':'','密码':''}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()

#登陆名：100091745304  密码：592316 用户名:chenxia6461 密码：592316   登陆名：100095161703   密码：843320