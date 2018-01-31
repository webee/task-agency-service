import time,datetime,json
from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask
from bs4 import BeautifulSoup

LOGIN_URL='http://118.112.188.109:90/gysbt/front/services/app/login'#http://118.112.188.109/nethall/login.jsp
FIVER_URL='http://118.112.188.109:90/gysbt/front/services/app/queryData'
class Task(AbsFetchTask):
    task_info = dict(
        city_name="贵阳",

        developers=[{'name':'卜圆圆','email':'byy@qinqinxiaobao.com'}]
    )

    def _get_common_headers(self):
        return {'User-Agent':'Mozilla/5.0 (iPhone; CPU iPhone OS 11_2 like Mac OS X) AppleWebKit/604.4.7 (KHTML, like Gecko) Version/8.0 Mobile/15C114 Safari/604.4.7 MDLIFE/2.0'}

    def _query(self, params: dict):
        """任务状态查询"""
        pass

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '身份证号' in params, '缺少身份证号'
        assert '密码' in params, '缺少密码'
        # other check
        身份证号 = params['身份证号']
        密码 = params['密码']
        if len(密码) < 4:
            raise InvalidParamsError('身份证号或密码错误')
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
                data = {
                    'jybh': 'MCX00023',
                    'yac005': id_num,
                    'type': '1',
                    'access_token': '',
                    'yae096': password
                }
                resp = self.s.post(LOGIN_URL,data=data, timeout=20)
                soup = BeautifulSoup(resp.content, 'html.parser')
                ylinfo = json.loads(soup.text)
                if ylinfo['message']:
                    return_message = ylinfo['message']
                    raise InvalidParamsError(return_message)
                else:
                    print("登录成功！")
                    output=ylinfo['output'][0]
                    self.result_data['baseInfo'] = {
                        '城市名称': '贵阳',
                        '城市编号': '520100',
                        '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                        '身份证号': output['AAC002'],
                        '姓名': output['AAC003'],
                        '性别': output['AAC004'],
                        '出生日期': output['AAC006'],
                        '参加工作日期': output['AAC007'],
                        '民族': output['AAC005'],
                        '户口性质': output['AAC009'],
                        '人员状态': output['AAC008'],
                        '医疗账户余额': output['AKC087'],
                        '手机号码': output['AAE005']
                    }
                    self.g.aac001=output['AAC001']
                    # 参保状态
                    datas={
                        'jybh':'yhsi0000001',
                        'aac001':self.g.aac001,
                        'aac002': id_num,
                        'access_token':''
                    }
                    resp = self.s.post(FIVER_URL,data=datas,timeout=20)
                    soup = BeautifulSoup(resp.content, 'html.parser')
                    ylinfo = json.loads(soup.text)
                    output = ylinfo['output'][0]
                    fivdic = {
                        '养老':output['aac031_jbyangl'],
                        '失业': output['aac031_shiy'],
                        '医疗': output['aac031_jbyiliao'],
                        '生育': output['aac031_gs'],
                        '工伤': output['aac031_shengy']
                    }
                    self.result_data['baseInfo'].setdefault('五险状态', fivdic)
                    self.result_identity['target_name'] = self.result_data['baseInfo']['姓名']
                    if '参保缴费' in fivdic.values():
                        self.result_identity['status'] = '正常'
                    else:
                        self.result_identity['status'] = '停缴'
                self.result_key = id_num
                self.result_meta['身份证号'] = id_num
                self.result_meta['密码'] = params.get('密码')
                self.result_identity['task_name'] = '贵阳'
                self.result_identity['target_id'] = id_num
                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input', placeholder='身份证号', value=params.get('身份证号', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
        ], err_msg)

    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            data=self.result_data
            # 五险明细jybh=yhsi0001003&aac001=3004182764&startrow=1&endrow=5&access_token=
            # 五险arrtype={'110':'基本养老保险','210':'失业保险','310':'基本医疗保险','410':'工伤保险','510':'生育保险'}
            arrtype = {'yhsi0001003': 'old_age', 'yhsi0002002': 'unemployment', 'yhsi0003002': 'medical_care', 'yhsi0004002': 'injuries',
                       'yhsi0005002': 'maternity'}
            ylsum = 0.00
            yilsum = 0.00
            arrMaxtime = []
            arrMintime=[]
            arrLenMonth=[]
            for k, v in arrtype.items():  # 类型
                data[v] = {}
                data[v]['data'] = {}
                datas={
                    'jybh':k,
                    'aac001': self.g.aac001,
                    'startrow': 1,
                    'endrow':10000,
                    'access_token': ''
                }
                resp = self.s.post(FIVER_URL, data=datas, timeout=20)
                soup = BeautifulSoup(resp.content, 'html.parser')
                ylinfo = json.loads(soup.text)
                if not ylinfo:
                    continue
                mxdic=ylinfo['output']
                lenmonth=0
                for i in range(0,len(mxdic)):
                    arrs = []
                    cell=mxdic[i]
                    yearkeys=cell['aae002']
                    dic = {
                        '险种名称': cell['jfbz'],
                        '缴费单位': cell['aab004'],
                        '缴费类型': cell['aae143']
                    }
                    years = yearkeys[:4]
                    months = yearkeys[-2:]
                    if v == 'old_age':
                        dic.setdefault('缴费基数', cell['aic020'])
                        dic.setdefault('缴费时间',cell['dwjfrq'])
                        dic.setdefault('个人缴费', cell['grjfje'])
                        dic.setdefault('公司缴费', cell['dwjfje'])
                        ylsum = ylsum + float(cell['grjfje'])
                    elif v == 'medical_care':
                        dic.setdefault('缴费基数', cell['akc010'])
                        dic.setdefault('缴费时间', cell['yae204'])
                        dic.setdefault('个人缴费', cell['grsj'])
                        dic.setdefault('公司缴费', cell['dwsj'])
                        yilsum = yilsum + float(cell['grsj'])
                    elif v == 'unemployment':
                        dic.setdefault('缴费基数', cell['aic020'])
                        dic.setdefault('缴费时间', cell['yae204'])
                        dic.setdefault('个人缴费', cell['ajc030'])
                        dic.setdefault('公司缴费', cell['ajc031'])
                    elif v == 'injuries':
                        dic.setdefault('缴费基数', cell['amc001'])
                        dic.setdefault('缴费时间', cell['yae205'])
                        dic.setdefault('个人缴费', cell['ymc244'])
                        dic.setdefault('公司缴费', cell['ymc237'])
                    elif v == 'maternity':
                        dic.setdefault('缴费基数', cell['amc001'])
                        dic.setdefault('缴费时间', cell['yae204'])
                        dic.setdefault('个人缴费', cell['ymc244'])
                        dic.setdefault('公司缴费', cell['ymc237'])
                    if years not in data[v]['data'].keys():
                        data[v]['data'][years] = {}
                    print(yearkeys)
                    if months not in data[v]['data'][years].keys():
                        lenmonth=lenmonth+1
                        data[v]['data'][years][months] = {}
                    else:
                        arrs = data[v]['data'][years][months]
                    arrs.append(dic)
                    data[v]['data'][years][months] = arrs
                if v == 'old_age':
                    data['baseInfo'].setdefault('个人养老累计缴费', "%.2f" % ylsum)
                if v == 'medical_care':
                    data['baseInfo'].setdefault('个人医疗累计缴费', "%.2f" % yilsum)
                if len(data[v]['data'])>0:
                    arrMaxtime.append(max(data[v]['data']) + max(data[v]['data'][max(data[v]['data'])]))
                    arrMintime.append(min(data[v]['data']) + min(data[v]['data'][min(data[v]['data'])]))
                    arrLenMonth.append(lenmonth)
            if len(arrLenMonth)>0:
                data['baseInfo'].setdefault('缴费时长', max(arrLenMonth))
            else:
                data['baseInfo'].setdefault('缴费时长', 0)
            if len(arrMintime) > 0:
                data['baseInfo'].setdefault('开始缴费时间', min(arrMintime))
            else:
                data['baseInfo'].setdefault('开始缴费时间', '')
            if len(arrMaxtime) > 0:
                data['baseInfo'].setdefault('最近缴费时间', min(arrMaxtime))
            else:
                data['baseInfo'].setdefault('最近缴费时间', '')
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    meta = {'身份证号': '512223196307143271'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()

#身份证号：522328199608134515  密码：960925  身份证号：520103196901181261  密码：200518  身份证号：522226196406012833  密码：196461
#身份证号：520181199002171732  密码：520173 身份证号：510725197007127117   密码：771122  身份证号：522121198109055230  密码：051081
