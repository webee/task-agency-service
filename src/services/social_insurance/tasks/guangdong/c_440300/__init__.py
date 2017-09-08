import base64
import time
import random
import json
import datetime
from bs4 import BeautifulSoup
from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask

LOGIN_URL = 'https://seyb.szsi.gov.cn/web/ajaxlogin.do'
VC_URL = 'https://seyb.szsi.gov.cn/web/ImageCheck.jpg'
USERINFO_URL='https://shebao.szsi.gov.cn:4482/socialsecurity/goInsured.do?method=listInsured'
class Task(AbsFetchTask):
    task_info = dict(
        city_name="深圳",
        help="""1.若您尚未激活或者没有在网上查询过您的社保卡，请点击激活社保账号<br/>
        2.如果您曾经激活过社保卡，但忘记密码，请点击忘记密码<br/>
        3.如办理社保卡时，没有登记手机号码或者更换手机号码，请本人携带身份证原件和新手机到社保分中心柜台办理注册手机变更业务。
        """
    )

    def _get_common_headers(self):
        return { 'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3100.0 Safari/537.36'}

    def _query(self, params: dict):
        """任务状态查询"""
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()
        pass

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_userinfo,self._unit_login)
        #self._add_unit(self._unit_fetch, self._unit_login)

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '用户名' in params, '缺少用户名'
        assert '密码' in params, '缺少密码'
        # other check
        用户名 = params['用户名']
        密码 = params['密码']
        if len(密码) < 4:
            raise InvalidParamsError('用户名或密码错误')
        if len(用户名) < 4:
            raise InvalidParamsError('用户名或密码错误')

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '用户名' not in params:
                params['用户名'] = meta.get('用户名')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '用户名' and '用户名' in meta:
                continue
            elif pr['key'] == '密码' and '密码' in meta:
                continue
            res.append(pr)
        return res
    def _unit_login(self, params:dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                username=params['用户名']
                password =params['密码']
                vc = params['vc']
                resp = self.s.post(LOGIN_URL, data=dict(
                    r=random.random(),
                    LOGINID=username,
                    PASSWORD=password,
                    IMAGCHECK=vc,
                    OPERTYPE2=3,
                    ISBIND='false',
                    now=time.strftime('%a %b %d %Y %H:%M:%S', time.localtime()),
                    callback=''
                ))
                soup = BeautifulSoup(resp.content, 'html.parser')
                jsonread = json.loads(soup.text)
                errormsg = jsonread['message']
                if errormsg:
                    raise InvalidParamsError(errormsg)
                self.result_key = params.get('username')

                # 保存到meta
                self.result_meta['用户名'] = params.get('用户名')
                self.result_meta['密码'] = params.get('密码')

                self.result_identity['task_name']='深圳'

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='用户名', name='用户名', cls='input', value=params.get('用户名', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}, value=params.get('vc', '')),
        ], err_msg)

    def _unit_fetch_userinfo(self):
        """用户信息"""
        try:
            self.result_data["baseInfo"]={
                '城市名称':'深圳市',
                '城市编号': '440300',
                '更新时间': time.strftime("%Y-%m-%d", time.localtime())
            }
            resp = self.s.get(USERINFO_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            userinfoname = soup.findAll('dt')
            userinfovalues = soup.findAll('dd')
            fivedic={}
            monthnum = 0
            status='不正常'
            for i in range(0,len(userinfoname)):
                if userinfoname[i].find('参保状态')==-1:
                    if userinfovalues[i]=='参加':
                       status = '正常'
                    fivedic.setdefault(userinfoname[:2],userinfovalues)
                else:
                    self.result_data["baseInfo"].setdefault(userinfoname[i],userinfovalues[i])
                    if userinfoname[i].find('累计月数')==-1 and monthnum < int(userinfovalues[i]):
                        monthnum = int(userinfovalues[i])

            self.result_identity['status'] =status
            self.result_data["baseInfo"].setdefault('缴费时长', monthnum)
            self.result_data["baseInfo"].setdefault('五险状态',fivedic)
            self.result_identity['target_name']=''
            self.result_identity['target_id']=''

            #TODO: 执行任务，如果没有登录，则raise PermissionError
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _unit_fetch(self):
        """五险"""
        try:
            # 明细(险种比较多)arrtype={'01':'基本养老保险','02':'失业保险','03':'基本医疗保险','04':'工伤保险','05':'生育保险'}
            arrtype = {'Yl': 'old_age', 'Shiye': 'unemployment', 'Yil': 'medical_care', 'Gs': 'injuries', 'Sy': 'maternity'}
            statetime=''
            endtime=''
            for k, v in arrtype.items():
                self.result_data[v]['data']={}
                years=''
                months=''
                personjfsum=0.00
                datas=dict(
                    _isModel= 'true',
                    params='{"oper": "CbjfmxcxAction.queryCbjfmx'+k+'", "params": {}, "datas": {"ncm_glt_医疗缴费明细": {"params": {"pageSize": 10, "curPageNum": 1}, "dataset": [], "heads": [],"heads_change": []}}}'
                )
                resp = self.s.post(USERINFO_URL,datas)
                pagearr=json.loads(resp.text)
                """获取分页"""
                pagesize=pagearr["datas"]['params']['pagesize']
                rowsCount=pagearr["datas"]['params']['rowsCount']
                pagenum=rowsCount/pagesize
                pagenums=rowsCount//pagesize
                if pagenum>pagenums:
                    pagenums=pagenums+1
                for i in round(1,pagenums+1):
                    datas = dict(
                        _isModel='true',
                        params='{"oper": "CbjfmxcxAction.queryCbjfmx'+k+'", "params": {}, "datas": {"ncm_glt_医疗缴费明细": {"params": {"pageSize": 10, "curPageNum": '+i+',"maxPageSize":50,"rowsCount":'+rowsCount+',"Total_showMsg":null,"Total_showMsgCell":null,"Total_Cols":[]},"heads":[],"heads_change":[],"dataset":[]}}}'
                    )
                    resp = self.s.post(USERINFO_URL, datas)
                    mx=json.loads(resp.text)["datas"]
                    for i in round(0,len(mx['dataset'])):
                        if v=='old_age'or v=='medical_care':
                            personjfsum=personjfsum+float(mx['dataset'][i]['个人缴'])
                            #enterjfsum=enterjfsum+float(mx['dataset'][i]['单位缴'])
                        yearmonth=mx['dataset'][i]['缴费年月'].replace('年','').replace('月','')
                        if statetime==''or int(statetime)>int(yearmonth):
                            statetime=yearmonth
                        if endtime=='' or int(endtime)<int(yearmonth):
                            endtime=yearmonth
                        if years=='' or years!=yearmonth[:4]:
                            years=yearmonth[:4]
                            self.result_data[v]['data'][years]={}
                            if months == yearmonth[-2:]:
                                self.result_data[v]['data'][years][months] = {}
                        if months == '' or months != yearmonth[-2:]:
                            months=yearmonth[-2:]
                            self.result_data[v]['data'][years][months]={}
                        mxdic={
                            '缴费时间':yearmonth,
                            '缴费类型':'-',
                            '缴费基数':mx['dataset'][i]['缴费工资'],
                            '公司缴费':mx['dataset'][i]['单位缴'],
                            '个人缴费': mx['dataset'][i]['个人缴'],
                            '缴费单位': mx['dataset'][i]['单位名称'],
                            '单位编号': mx['dataset'][i]['单位编号'],
                            '缴费合计': mx['dataset'][i]['缴费合计'],
                            '备注': mx['dataset'][i]['备注']
                        }
                        self.result_data[v]['data'][years][months]=mxdic

                if v == 'old_age':
                    self.result_data["baseInfo"].setdefault('个人养老累计缴费', personjfsum)
                if v == 'medical_care':
                    self.result_data["baseInfo"].setdefault('个人医疗累计缴费', personjfsum)
            self.result_data["baseInfo"].setdefault('最近缴费时间', endtime)
            self.result_data["baseInfo"].setdefault('开始缴费时间', statetime)
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    # 刷新验证码
    def _new_vc(self):
        resp = self.s.get(VC_URL)
        return dict(cls='data:image', content=resp.content, content_type=resp.headers.get('Content-Type'))

if __name__ == '__main__':
    from services.client import TaskTestClient
    meta = {'用户名': 'keguangping', '密码': 'Kegp850907'}
    client = TaskTestClient(Task(SessionData(), prepare_data=dict(meta=meta), is_start=False))
    client.run()
