
import base64
import datetime
from bs4 import BeautifulSoup
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask

VC_URL='http://wsbs.zjhz.hrss.gov.cn/captcha.svl'
LOGIN_URL='http://wsbs.zjhz.hrss.gov.cn/loginvalidate.html'
INFO_URL='http://wsbs.zjhz.hrss.gov.cn/person/personInfo/index.html'
MX_URL='http://wsbs.zjhz.hrss.gov.cn/unit/web_zgjf_query/web_zgjf_doQuery.html'

class Task(AbsFetchTask):
    task_info = dict(
        city_name="杭州",
        help="""<li>首次申请密码或遗忘网上登陆密码，本人须携带有效身份证件至就近街道社区事务受理中心或就近社保分中心自助机具上申请办理</li>"""
    )

    def _get_common_headers(self):
        return {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3100.0 Safari/537.36'}

    def _query(self, params: dict):
        """任务状态查询"""
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()
        pass

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '账号' in params, '缺少账号'
        assert '密码' in params,'缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check
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

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                id_num = params['账号']
                password = params['密码']
                # m = hashlib.md5()
                # m.update(str(password).encode(encoding="utf-8"))
                # pw = m.hexdigest()
                pw=base64.b64encode(password.encode('utf-8'))
                vc = params['vc']
                newurl=LOGIN_URL+'?logintype=2&captcha='+vc
                resp = self.s.post(newurl, data=dict(
                                    type='01',
                                    persontype='01',
                                    account=id_num,
                                    password=pw,
                                    captcha1=vc))
                soup = BeautifulSoup(resp.content, 'html.parser')
                if 'success' in soup.text:
                    print("登录成功！")
                else:
                    return_message = soup.text
                    raise Exception(return_message)

                self.result_key = id_num
                # 保存到meta
                self.result_meta['账号'] = id_num
                self.result_meta['密码'] = password

                self.result_identity['task_name'] = '杭州'

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)
        vc = self._new_vc()
        raise AskForParamsError([
            dict(key='账号', name='账号', cls='input', placeholder='身份证号或者市民邮箱(@hz.cn)', value=params.get('账号', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}, value=params.get('vc', '')),
        ], err_msg)

    def _unit_fetch(self):
        try:
            data = self.result_data
            # 基本信息
            resp=self.s.get(INFO_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            alltable=soup.findAll('table')
            infotable=alltable[3]
            infostatus=alltable[6]

            data['baseInfo'] = {
                "更新时间": datetime.datetime.now().strftime('%Y-%m-%d'),
                '城市名称': '杭州',
                '城市编号': '330100'
            }
            for row in infotable.find_all('tr'):
                cell = [i.text for i in row.find_all('td')]
                data['baseInfo'].setdefault(cell[0].replace(' ', '').replace('：',''), cell[1].replace(' ', '').replace('\xa0','').replace('\r','').replace('\n',''))
                data['baseInfo'].setdefault(cell[2].replace(' ', '').replace('：',''), cell[3].replace(' ', '').replace('\xa0','').replace('\r','').replace('\n',''))

            fristtime=[]
            infodic={}
            for row in infostatus.find_all('tr'):
                cell = [i.text for i in row.find_all('td')]
                if cell[1] != '险种类型':
                    infodic[cell[1].replace('企业基本','').replace('保险','').replace('职工医保（企业）','医疗').replace('\r\n','')]=cell[2].replace('参保缴费','正常参保').replace('\r\n','')

                    fristtime.append(cell[4])

            data['baseInfo'].setdefault('五险状态',infodic)
            data['baseInfo'].setdefault('开始缴费时间',min(fristtime))
            self.result_identity['target_name'] = data['baseInfo']['姓名']
            self.result_identity['target_id'] = data['baseInfo']['身份证号码']
            if '正常参保' in infodic.values():
                self.result_identity['status'] = '正常参保'
            else:
                self.result_identity['status'] = '停缴'


            #五险明细
            # 五险arrtype={'11':'基本养老保险','21':'失业保险','31':'基本医疗保险','41':'工伤保险','51':'生育保险'}
            arrtype = {'11': 'old_age', '21': 'unemployment', '31': 'medical_care','41': 'injuries', '51': 'maternity'}
            for k, v in arrtype.items():   #类型
                data[v] = {}
                data[v]['data'] = {}
                yearkeys = ''
                for i in range(int(min(fristtime)[:4]),int(datetime.date.year)):  #年
                    for y in range(1,3):     #分页
                        url=MX_URL+'?m_aae002='+i+'&m_aae140='+k+'&pageNo='+y
                        resp = self.s.get(url)
                        soup = BeautifulSoup(resp.content, 'html.parser')
                        tablelist=soup.select('.grid')



            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        resp = self.s.get(VC_URL)
        return dict(cls='data:image', content=resp.content, content_type=resp.headers.get('Content-Type'))
if __name__ == '__main__':
    from services.client import TaskTestClient
    meta = {'账号': '441426198410150015@hz.cn', '密码': 'lsp123456'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()
