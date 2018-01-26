import time,datetime,json
from bs4 import BeautifulSoup
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask
#http://221.207.175.178:7989/uaa/personlogin#/personLogin
LOGIN_URL='http://221.207.175.178:7989/uaa/api/person/idandmobile/login'
VC_URL = 'http://221.207.175.178:7989/uaa/captcha/img'
USER_URL='http://221.207.175.178:7989/api/security/user'
INFOR_URL='http://221.207.175.178:7989/ehrss-si-person/api/rights/person/baseinfo?personId='
MX_URL='http://221.207.175.178:7989/ehrss-si-person/api/rights/payment/paydetail?'
class Task(AbsFetchTask):
    task_info = dict(
        city_name="哈尔滨",
        developers=[{'name':'卜圆圆','email':'byy@qinqinxiaobao.com'}]
    )

    def _get_common_headers(self):
        return {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3100.0 Safari/537.36'}

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
        assert '用户名' in params, '缺少用户名'
        assert '密码' in params, '缺少密码'
        # other check
        用户名 = params['用户名']
        密码 = params['密码']
        if len(密码) < 4:
            raise InvalidParamsError('用户名或密码错误')
        if len(用户名) < 5:
            raise InvalidParamsError('用户名错误')
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

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                id_num = params['用户名']
                password = params['密码']
                vc = params['vc']
                data = {
                    'username': id_num,
                    'password': password,
                    'captchaWord': vc,
                    'captchaId':self.state['captchaId']
                }
                resp = self.s.post(LOGIN_URL, data=data, timeout=20)
                if resp.url=='http://221.207.175.178:7989/uaa/personlogin?error':
                    resp=self.s.get('http://221.207.175.178:7989/uaa/personlogin?error')
                    soup=BeautifulSoup(resp.content,'html.parser')
                    return_message = soup.findAll('div')[0].text.replace('\n','').replace('\t','')
                    raise InvalidParamsError(return_message)
                else:
                    soup = BeautifulSoup(resp.content, 'html.parser')
                    self.g.code=self.s.get(soup.text.split('"')[1]).url
                    print("登录成功！")
                self.result_key = id_num
                # 保存到meta
                self.result_meta['用户名'] = id_num
                self.result_meta['密码'] = password
                self.result_identity['task_name'] = '哈尔滨'
                self.result_identity['target_id'] = id_num
                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='用户名', name='用户名', cls='input', placeholder='社保卡或身份证', value=params.get('用户名', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            resp = self.s.get(USER_URL,headers={'Accept':'application/json, text/plain, */*','Accept-Language':'zh-CN,zh;q=0.8'})
            soup = BeautifulSoup(resp.content, 'html.parser')
            useriddic=json.loads(soup.text)
            userid=str(useriddic['associatedPersons'][0]['id'])
            # 基本信息
            data = self.result_data
            resp = self.s.get(INFOR_URL+userid)
            soup = BeautifulSoup(resp.content, 'html.parser')
            infodic=json.loads(soup.text)
            if not infodic:
                return
            data['baseInfo'] = {
                '城市名称': '哈尔滨',
                '城市编号': '230100',
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '个人编号': userid,
                '社保编号': infodic['baseInfoDTO']['idSocialensureNumber'],
                '身份证号': infodic['baseInfoDTO']['idNumber'],
                '姓名': infodic['baseInfoDTO']['name'],
                '性别':'女' if infodic['baseInfoDTO']['sex']=='2' else '男',
                '人员状态':'在职' if infodic['baseInfoDTO']['individualStatus']=='1' else '离职',
                '个人养老累计缴费':'0.00',
                '个人医疗累计缴费': '0.00'
            }
            #五险状态
            fivestate=infodic['insurInfoList']
            paymentState={}
            firstJoinDate=[]
            insuranceCode={}
            for i in range(0,len(fivestate)):
                fivdic=fivestate[i]
                firstJoinDate.append(fivdic['firstJoinDate'])
                if fivdic['insuranceCode']=='31':
                    names='医疗'
                    insuranceCode.setdefault(fivdic['insuranceCode'],'medical_care')
                elif fivdic['insuranceCode']=='32':
                    names='大病'
                    insuranceCode.setdefault(fivdic['insuranceCode'], 'serious_illness')
                elif fivdic['insuranceCode'] == '41':
                    names = '工伤'
                    insuranceCode.setdefault(fivdic['insuranceCode'], 'injuries')
                elif fivdic['insuranceCode'] == '51':
                    names = '生育'
                    insuranceCode.setdefault(fivdic['insuranceCode'], 'maternity')
                elif fivdic['insuranceCode'] == '11':
                    names = '养老'
                    insuranceCode.setdefault(fivdic['insuranceCode'], 'old_age')
                elif fivdic['insuranceCode'] == '21':
                    names = '失业'
                    insuranceCode.setdefault(fivdic['insuranceCode'], 'unemployment')
                if fivdic['paymentState']=='1':
                    paymentState.setdefault(names, '正常')
                elif fivdic['paymentState']=='2':
                    paymentState.setdefault(names, '停缴')
            self.result_identity['target_name'] = data['baseInfo']['姓名']
            if '正常' in paymentState.values():
                self.result_identity['status'] = '正常'
            else:
                self.result_identity['status'] = '停缴'
            data['baseInfo'].setdefault('五险状态',paymentState)
            data['baseInfo'].setdefault('开始缴费时间', min(firstJoinDate)[:7].replace('-',''))

            #明细
            statime=min(firstJoinDate)[:7].replace('-','')
            endtime=time.strftime("%Y-%m-%d", time.localtime())[:7].replace('-','')
            ylsum = 0.00
            yilsum = 0.00
            arrMaxtime = []
            arrlong=[]
            for k,v in insuranceCode.items():  # 类型
                data[v] = {}
                data[v]['data'] = {}
                resp = self.s.get(MX_URL + 'endTime='+endtime+'&paymentType='+k+'&personId='+userid+'&startTime='+statime+'&type=0')#,headers={'Accept':'application/json, text/plain, */*','Accept-Language':'zh-CN,zh;q=0.8','Referer':self.g.code,'Host':'221.207.175.178:7989'})
                soup = BeautifulSoup(resp.content, 'html.parser')
                infodic = json.loads(soup.text)
                if not infodic:
                    return
                longmonth=0
                for i in range(0,len(infodic['list'])):
                    arrs = []
                    olddic=infodic['list'][i]
                    newdic={
                        '缴费时间': olddic['issue'][:4]+'-'+olddic['issue'][-2:],
                        '险种名称': olddic['type'],
                        '缴费基数': olddic['basePay'],
                        '个人缴费': olddic['personPay'],
                        '缴费单位': olddic['companyName'],
                        '缴费类型': olddic['payType'],
                        '公司缴费': olddic['companyPay']
                    }
                    yearkeys = olddic['issue']
                    years = yearkeys[:4]
                    months = yearkeys[-2:]
                    if v == 'medical_care':
                        yilsum = float(yilsum) + float(olddic['personPay'])
                    if v == 'old_age':
                        ylsum = float(ylsum) + float(olddic['personPay'])
                    if years not in data[v]['data'].keys():
                        data[v]['data'][years] = {}
                    if months not in data[v]['data'][years].keys():
                        data[v]['data'][years][months] = {}
                        longmonth=longmonth+1
                    else:
                        arrs = data[v]['data'][years][months]
                    arrs.append(newdic)
                    data[v]['data'][years][months] = arrs
                if v == 'old_age':
                    data['baseInfo']['个人养老累计缴费']= "%.2f" % ylsum
                if v == 'medical_care':
                    data['baseInfo']['个人医疗累计缴费']="%.2f" % yilsum
                if len(data[v]['data'])>0:
                    arrMaxtime.append(max(data[v]['data']) + max(data[v]['data'][max(data[v]['data'])]))
                    arrlong.append(longmonth)
            if len(arrMaxtime)>0:
                data['baseInfo'].setdefault('最近缴费时间', max(arrMaxtime))
                data['baseInfo'].setdefault('缴费时长', max(arrlong))
            else:
                data['baseInfo'].setdefault('最近缴费时间', '')
                data['baseInfo'].setdefault('缴费时长', 0)
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)
    def _new_vc(self):
        resp = self.s.get(VC_URL,timeout=25)
        soup = BeautifulSoup(resp.content, 'html.parser')
        texts=json.loads(soup.text)
        self.state['captchaId']=texts['id']
        resp = self.s.get(VC_URL+'/'+texts['id'], timeout=25)
        return dict(content=resp.content,content_type='application/json;charset=UTF-8')

if __name__ == '__main__':
    from services.client import TaskTestClient

    meta = {'用户名': '230105197210311926','密码':'mh15245014501'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()

# 用户名：230105197210311926  密码：mh15245014501  用户名：230803196905110064  密码：Zls13936311366
