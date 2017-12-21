import time
import json
from services.service import SessionData, AbsTaskUnitSessionTask
from bs4 import BeautifulSoup
from services.service import AskForParamsError, PreconditionNotSatisfiedError
from services.commons import AbsFetchTask
from  services.errors import InvalidParamsError

LOGIN_URL = 'http://wscx.xmgjj.gov.cn/xmgjjGR/login.shtml'
VC_URL = 'http://wscx.xmgjj.gov.cn/xmgjjGR/codeImage.shtml'
INFO_URL='http://wscx.xmgjj.gov.cn/xmgjjGR/queryPersonXx.shtml'
MX_URL='http://wscx.xmgjj.gov.cn/xmgjjGR/queryGrzhxxJson.shtml'
class Task(AbsFetchTask):
    task_info = dict(
        city_name="厦门",
        help="""<li>如您未在公积金网站查询过您的公积金信息，请到厦门公积金管理中心官网网完成“注册”然后再登录。</li>""",
        developers=[{'name':'卜圆圆','email':'byy@qinqinxiaobao.com'}]
    )
    def _get_common_headers(self):
        return {'User-Agent':'Mozilla/5.0 (iPad; CPU OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1'}

    def _query(self, params: dict):
        """任务状态查询"""
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '账号' in params, '缺少账号'
        assert '密码' in params, '缺少密码'
        if 'vc' in params:
            assert 'vc' in params, '缺少验证码'
        # other check
        账号 = params['账号']
        密码 = params['密码']
        if len(密码) < 4:
            raise InvalidParamsError('账号或密码错误')
        if len(账号) < 15:
            raise InvalidParamsError('身份证错误')


    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '账号' not in params:
                params['账号'] = meta.get('账号')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '账号' and '账号' in meta:
                continue
            elif pr['key'] == '密码' and '密码' in meta:
                continue
            res.append(pr)
        return res

    def _unit_login(self, params=None):
        Frist_Time=False#self.g.fristtime
        err_msg = None
        if not self.is_start or params:
            try:
                self._check_login_params(params)
                id_num = params['账号']
                self.s.idnum=id_num
                password = params['密码']
                vc=''
                if 'vc' in params:
                    vc = params['vc']

                data = dict(
                    securityCode2=vc,
                    securityCode=vc,
                    username=id_num,
                    password=password
                )
                resp = self.s.post(LOGIN_URL, data=data,
                                   headers={'Content-Type': 'application/x-www-form-urlencoded'},timeout=10)

                soup = BeautifulSoup(resp.content, 'html.parser')
                if soup.select('#err_area'):
                    return_message = soup.select('#err_area')[0].find('font').text
                else:
                    return_message=None
                if return_message:
                    Frist_Time=True
                    raise InvalidParamsError(return_message)
                else:
                    print("登录成功！")

                self.result_key = id_num
                # 保存到meta
                self.result_meta['账号'] = id_num
                self.result_meta['密码'] = password
                self.result_identity['task_name'] = '厦门'
                self.result_identity['target_id'] = id_num

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)
        if Frist_Time:
            vc = self._new_vc()
            raise AskForParamsError([
                dict(key='账号', name='账号', cls='input', placeholder='证件号码', value=params.get('账号', '')),
                dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
                dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
            ], err_msg)
        else:
            #self.g.fristtime = False
            raise AskForParamsError([
                dict(key='账号', name='账号', cls='input', placeholder='证件号码'),
                dict(key='密码', name='密码', cls='input:password'),
            ], err_msg)

    def _unit_fetch(self):
        try:
            data = self.result_data
            # 基本信息
            resp = self.s.post(INFO_URL,timeout=5)
            soup = BeautifulSoup(resp.content, 'html.parser')
            infos=json.loads(soup.text)
            data['baseInfo'] = {
                '城市名称': '厦门',
                '城市编号': '350200',
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '证件类型': '身份证',
                '证件号':self.s.idnum,
                '个人账号':infos['Person']['custAcct'],
                '姓名': infos['Person']['custName'],
                '开户银行':infos['Person']['aaa103'],
                '开户网点':infos['Person']['bankOrgName'],
                '开户日期': infos['Person']['openDate'].replace('年','').replace('月','').replace('日','')
            }
            self.result_identity['target_name'] = data['baseInfo']['姓名']
            acctStatus='封存'
            if infos['Person']['acctStatus']=='0':
                acctStatus='缴存'
            self.result_identity['status'] =acctStatus

            data['companyList'] = []
            diclist = {
                '单位名称': infos['Person']['compName'],
                '当前余额': infos['Person']['bal'],
                '帐户状态': acctStatus,
                '最后业务日期': infos['Person']['lastAutoAcctDate'].replace('年','').replace('月','').replace('日','')
            }
            data['companyList'].append(diclist)

            # 明细信息
            datas={
                'custAcct': data['baseInfo']['个人账号'],
                'startDate': data['baseInfo']['开户日期'],
                'endDate':time.strftime("%Y-%m-%d", time.localtime()).replace('-','')
            }
            resp = self.s.post(MX_URL,data=datas,timeout=5)
            soup = BeautifulSoup(resp.content, 'html.parser')
            infos = json.loads(soup.text)
            data['detail'] = {}
            data['detail']['data'] = {}
            years = ''
            months = ''
            for i in range(0,int(infos['totalRecords'])):
                arr = []
                dicinfo=infos['list'][i]
                dic={
                    '时间': dicinfo['bankAcctDate'],
                    '单位名称': '',
                    '支出': 0,
                    '收入': float(dicinfo['creditAmt']),
                    '汇缴年月':'',
                    '余额': dicinfo['saveBal'],
                    '类型': dicinfo['bankSumy']
                }
                times = dicinfo['bankAcctDate'].replace('年','').replace('月','').replace('日','')
                if years != times[:4]:
                    years = times[:4]
                    data['detail']['data'][years] = {}
                    if months != times[4:6]:
                        months = times[4:6]
                        data['detail']['data'][years][months] = {}
                else:
                    if months != times[4:6]:
                        months = times[4:6]
                        data['detail']['data'][years][months] = {}
                    else:
                        arr = data['detail']['data'][years][months]
                arr.append(dic)
                data['detail']['data'][years][months] = arr
                print(arr)

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)
    def _new_vc(self):
        vc_url = VC_URL #+ str(int(time.time() * 1000))
        resp = self.s.get(vc_url,timeout=5)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])


if __name__ == '__main__':
    from services.client import TaskTestClient
    meta = {'账号': '362321199602224347'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()

    #账号：350821199411230414  密码：20120305xin 账号：430722199009274233 密码：hxp15268053044

