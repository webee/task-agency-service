import time
import json
import re
from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask
from bs4 import BeautifulSoup

#http://123.233.117.50:801/jnwt/indexPerson.jsp
LOGIN_URL='http://123.233.117.50:801/jnwt/per.login'
VC_URL='http://123.233.117.50:801/jnwt/vericode.jsp'
INFOR_URL='http://123.233.117.50:801/jnwt/init.summer?_PROCID=60020009'
MX_URL='http://123.233.117.50:801/jnwt/init.summer?_PROCID=60020010'
LIST_URL='http://123.233.117.50:801/jnwt/dynamictable?uuid='
class Task(AbsFetchTask):
    task_info = dict(
        city_name="济南",

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
        assert '身份证号' in params, '缺少身份证号'
        assert '密码' in params, '缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check
        身份证号 = params['身份证号']
        密码 = params['密码']
        if len(密码) < 4:
            raise InvalidParamsError('密码错误')
        if len(身份证号) < 15:
            raise InvalidParamsError('身份证号错误')

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
            elif pr['key'] == 'other':
                continue
            res.append(pr)
        return res

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                id_num = params['身份证号']
                password = params['密码']
                vc = params['vc']
                data = {
                    'certinum': id_num,
                    'perpwd': password,
                    'vericode': vc
                }
                resp = self.s.post(LOGIN_URL, data=data, timeout=20)
                soup = BeautifulSoup(resp.content, 'html.parser')
                successinfo = soup.select('.error')
                if len(successinfo)>0:
                    successinfo=successinfo[0].next
                else:
                    successinfo=''
                if successinfo:
                    return_message = successinfo
                    raise InvalidParamsError(return_message)
                else:
                    print("登录成功！")

                self.result_key = id_num
                # 保存到meta
                self.result_meta['身份证号'] =id_num
                self.result_meta['密码'] = params.get('密码')
                self.result_identity['task_name'] = '济南'
                self.result_identity['target_id'] =id_num

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input', placeholder='身份证号', value=params.get('身份证号', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            #基本信息
            resp=self.s.get(INFOR_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            tables=soup.select('#ct_form')[0]
            data = self.result_data
            #帐户状态
            grzh =''
            for i in range(0,len(soup.select('#PerAccState')[0].findAll('option'))):
                if len(soup.select('#PerAccState')[0].findAll('option')[i].attrs)==2:
                    grzh=soup.select('#PerAccState')[0].findAll('option')[i].text
                    if grzh=='正常':
                        self.result_identity['status'] ='缴存'
                    else:
                        self.result_identity['status'] = '封存'

            # 冻结原因
            FrzRsn = ''
            for i in range(0, len(soup.select('#FrzRsn')[0].findAll('option'))):
                if len(soup.select('#FrzRsn')[0].findAll('option')[i].attrs) == 2:
                    FrzRsn = soup.select('#FrzRsn')[0].findAll('option')[i].text

            data['baseInfo'] = {
                '城市名称': '济南',
                '城市编号': '370100',
                '证件号': soup.select('#CertiNum')[0].attrs['value'],
                '证件类型': '身份证',
                '个人账号': soup.select('#AccNum')[0].attrs['value'],
                '姓名': soup.select('#AccName')[0].attrs['value'],
                '帐户状态': grzh,
                '冻结原因': FrzRsn,
                '开户日期': soup.select('#OpenDate')[0].attrs['value'],
                '月应缴额':soup.select('#MonPaySum')[0].attrs['value'],
                '单位缴存比例':soup.select('#UnitProp')[0].attrs['value'] + '%',
                '个人缴存比例':soup.select('#IndiProp')[0].attrs['value'] + '%',
                '联名卡号': soup.select('#CardNo')[0].attrs['value'],
                '开户银行': soup.select('#AccBankName')[0].attrs['value'],
                '最近6个月的平均缴存基数': soup.select('#avgbasenumber')[0].attrs['value'],
                '连续缴存月数': soup.select('#paynum')[0].attrs['value'],
                '缴存基数': soup.select('#BaseNumber')[0].attrs['value'],
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '最后汇缴月': soup.select('#LastPayDate')[0].attrs['value']
            }
            self.result_identity['target_name'] = soup.select('#AccName')[0].attrs['value']
            data['companyList'] = []
            entdic = {
                '单位账号': soup.select('#UnitAccNum')[0].attrs['value'],
                '单位名称': soup.select('#UnitAccName')[0].attrs['value'],
                '委托代办单位编号': soup.select('#AgentUnitNo')[0].attrs['value'],
                '当前余额': soup.select('#Balance')[0].attrs['value'],
                '帐户状态': grzh
            }
            data['companyList'].append(entdic)
            #缴存信息
            resp = self.s.get(MX_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            inputs=soup.findAll('input')
            textareas=soup.findAll('textarea')
            cscontent=eval(soup.findAll("script")[8].text.split('=')[1].split(';')[0])
            cscontent['BegDate']='2014-01-01'
            cscontent['EndDate'] = time.strftime("%Y-%m-%d", time.localtime())
            resps=self.s.post('http://123.233.117.50:801/jnwt/command.summer?uuid='+str(int(time.time() * 1000)),data=cscontent)
            soups = BeautifulSoup(resps.content, 'html.parser')

            datas={
                      'dynamicTable_id': 'datalist',
                      'dynamicTable_currentPage': '0',
                      'dynamicTable_pageSize': '1000',
                      'dynamicTable_nextPage': '1',
                      'dynamicTable_page':'/ydpx/60020010/602010_01.ydpx' ,
                      'dynamicTable_paging': 'true',
                      'dynamicTable_configSqlCheck': '0',
                      'errorFilter': '1 = 1',
                      'BegDate':'2014-01-01' ,
                      'EndDate':time.strftime("%Y-%m-%d", time.localtime()),
                      '_APPLY':inputs[2].attrs['value'] ,
                      '_CHANNEL': inputs[3].attrs['value'],
                      '_PROCID': inputs[4].attrs['value'],
                      '_LoginType':inputs[5].attrs['value'],
                      'DATAlISTGHOST':textareas[0].text,
                      '_DATAPOOL_':textareas[1].text
            }
            resp = self.s.post(LIST_URL+str(int(time.time() * 1000)),data=datas,headers={'X-Requested-With':'XMLHttpRequest',
                                                                                         'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
                                                                                         'Accept': 'application / json,text / javascript, * / *; q=0.01',
                                                                                         'Accept - Encoding': 'gzip,deflate',
                                                                                         'Accept - Language':'zh - CN, zh;q = 0.8',
                                                                                        'Connection': 'keep - alive',
                                                                                         'Host': '123.233.117.50:801',
                                                                                            'Origin': 'http: // 123.233.117.50: 801',
                                                                                            'Referer': 'http: // 123.233.117.50: 801 / jnwt / init.summer?_PROCID = 60020010'
                                                                                         })
            soup = BeautifulSoup(resp.content, 'html.parser')
            listinfo=json.loads(soup.text)
            mingxiinfo=listinfo['data']
            mxlist=mingxiinfo['data']
            data['detail'] = {}
            data['detail']['data'] = {}
            years = ''
            months = ''
            hjcs = 0
            hjje = ''
            hjrq = ''
            for i in range(0, int(mingxiinfo['totalCount'])):
                mxdic = mxlist[i]
                arr = []
                oper=mxdic['oper']
                sr=''
                zc=''
                if oper=='2037':
                    oper='年度结息'
                    sr= mxdic['amt1']
                elif oper=='1015':
                    oper = '汇缴'
                    sr = mxdic['amt1']
                elif oper == '2001':
                    oper = '个人开户'
                    sr = mxdic['amt1']
                elif oper == '2024':
                    oper = '住房提取'
                    zc=mxdic['amt1']
                else:
                    zc = mxdic['amt1']

                dic = {
                    '时间': mxdic['transdate'],
                    '单位名称': '',
                    '支出': zc,
                    '收入':sr,
                    '汇缴年月': mxdic['begindatec'],
                    '余额': mxdic['amt2'],
                    '类型':oper

                }
                if oper == '汇缴':
                    hjcs = hjcs + 1
                    hjje = sr
                    hjrq = mxdic['begindatec']
                times = mxdic['transdate'][:7].replace('-', '')
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
        #vc_url = VC_URL  # + str(int(time.time() * 1000))
        resp = self.s.get(VC_URL,timeout=15)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])
if __name__ == '__main__':
    from services.client import TaskTestClient
    meta = {'身份证号': '37011219821208683X', '密码': 'maomao7758'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()

#身份证号：37108319901120054X   密码：6668138mn  身份证号: 37091119900223121X  密码: xiaomeng@520  身份证号: 370104198901272224  密码: tian209114
#身份证号: 371523199410170510  密码: lupt7877  身份证号: 37011219821208683X   密码: maomao7758