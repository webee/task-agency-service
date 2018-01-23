import time,datetime,json
import execjs
from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask
from bs4 import BeautifulSoup


LOGIN_URL='http://wsbs.dggjj.gov.cn/web_housing/CommonTransferServlet?'#http://wsbs.dggjj.gov.cn/web_housing/unieap/pages/login/login.jsp#
VC_URL='http://wsbs.dggjj.gov.cn/web_housing/ValidateCodeServlet'
INFOR_URL=''
class Task(AbsFetchTask):
    task_info = dict(
        city_name="东莞",

        developers=[{'name':'卜圆圆','email':'byy@qinqinxiaobao.com'}]
    )

    def _get_common_headers(self):
        return {'User-Agent':'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1'}

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
        assert '用户名' in params, '缺少用户名'
        assert '密码' in params, '缺少密码'
        # other check
        用户名 = params['用户名']
        密码 = params['密码']
        if len(密码) < 4:
            raise InvalidParamsError('用户名或密码错误')
        if len(用户名) < 15:
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
                    "header":'{"code":0,"message":{"title":"","detail":""}}',
                    "body": '{"dataStores": {},"parameters": {"code": "'+vc+'", "j_password": "'+password+'", "j_username": "'+id_num+'"}}'
                }
                resp = self.s.post(LOGIN_URL+'method=Com0002', data=json.dumps(data),headers={'ajaxRequest':'true','Content-Type':'multipart/form-data','X-Requested-With':'XMLHttpRequest',
                                                                 'Host': 'wsbs.dggjj.gov.cn',
                                                                 #'content-type': 'application/json',
                                                                 'Origin': 'http: // wsbs.dggjj.gov.cn',
                                                                'Referer': 'http: // wsbs.dggjj.gov.cn / web_housing / unieap / pages / login / login.jsp'
                                                                }, timeout=20)
                soup = BeautifulSoup(resp.content, 'html.parser')
                dictmessage=execjs.eval(soup.text)
                return_message =dictmessage['header']['message']['title'] #soup.text.split(',')[1].split(':')[2].replace('"','')
                if return_message:
                    raise InvalidParamsError(return_message)
                else:
                    print("登录成功！")
                self.result_key = id_num
                # 保存到meta
                self.result_meta['用户名'] = id_num
                self.result_meta['密码'] = password
                self.result_identity['task_name'] = '东莞'
                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='用户名', name='用户名', cls='input', placeholder='用户名', value=params.get('用户名', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            # 基本信息
            datas = {
                'header': '{"code":0,"message":{"title":"","detail":""}}',
                'body': '{dataStores:{},parameters:{}}'
            }
            resp = self.s.post(LOGIN_URL + 'method=Biz1001', data=json.dumps(datas),
                               headers={'ajaxRequest': 'true', 'Content-Type': 'multipart/form-data',
                                        'X-Requested-With': 'XMLHttpRequest'
                                        }, timeout=20)
            soup = BeautifulSoup(resp.content, 'html.parser')
            dicinfo = execjs.eval(soup.text)
            infos = dicinfo['body']['dataStores']['psnBasicInfoDs']['rowSet']['primary']
            data = self.result_data
            data['baseInfo'] = {
                '城市名称': '东莞',
                '城市编号': '441900',
                '证件类型': '身份证' if infos[0]['CERT_TYPE'] == '0' else '',
                '证件号': infos[0]['CERT_NO'],
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '个人账号': infos[0]['PSN_ACC'],
                '姓名': infos[0]['PSN_NAME'],
                '账户状态': '正常' if infos[0]['PSN_ACC_ST'] == '1' else '停缴',
                '性别': '男' if infos[0]['SEX']=='1' else '女',
                '出生日期': infos[0]['BIRTHDAY'],
                '单位名称': infos[0]['ORG_NAME'],
                '单位地址': infos[0]['ORG_ADD'],
                '手机号': infos[0]['MOBILE_TEL'],
                '邮箱': infos[0]['MAIL'],
                '单位电话': infos[0]['OFFICE_PHONE'],
                '户籍地': infos[0]['REG_RESI_ADD'],
                '现住址': infos[0]['NOW_ADD'],
                '学历': infos[0]['DEGREE'],
                '工资基数': infos[0]['ORIGINAL_BASE'],
                '婚姻情况': infos[0]['MARRY'],
                '配偶姓名': infos[0]['SPOUSE'],
                '配偶身份证号': infos[0]['SPOUSE_CERT_NO'],
                '民族': infos[0]['NATION']
            }
            self.result_identity['target_id'] = data['baseInfo']['证件号']
            self.result_identity['target_name'] = data['baseInfo']['姓名']
            if data['baseInfo']['账户状态']=='正常':
                self.result_identity['status'] = '缴存'
            else:
                self.result_identity['status'] = '封存'

            #账户信息
            datas = {
                'header': '{"code":0,"message":{"title":"","detail":""}}',
                'body': '{dataStores:{},parameters:{"certType":"","psnName":"","psnAccSt":"","orgAcc":"","certNo":""}}'
            }
            resp = self.s.post(LOGIN_URL + 'method=Biz1003', data=json.dumps(datas),
                               headers={'ajaxRequest': 'true', 'Content-Type': 'multipart/form-data',
                                        'X-Requested-With': 'XMLHttpRequest'
                                        }, timeout=20)
            soup = BeautifulSoup(resp.content, 'html.parser')
            dicinfo=execjs.eval(soup.text)
            infos=dicinfo['body']['dataStores']['psnZSInfoDs']['rowSet']['primary']
            enterarr = []
            enterdic={
                '个人账号': infos[0]['PSN_ACC'],
                '姓名': infos[0]['PSN_NAME'],
                '帐户状态': '正常' if infos[0]['PSN_ACC_ST']=='1' else '停缴',
                '开户网点': infos[0]['COLL_BANK_ID'],
                '开户日期': infos[0]['BLD_ACC_TIME'],
                '单位名称': infos[0]['ORG_NAME'],
                '单位账号': infos[0]['ORG_ACC'],
                '缴存基数': infos[0]['ORIGINAL_BASE'],
                '单位缴存比例': infos[0]['ORG_CTB_RATE'],
                '个人缴存比例': infos[0]['PSN_CTB_RATE'],
                '最近汇缴日期': infos[0]['PSN_END_PAY_TIME'],
                '最近汇缴金额': infos[0]['PAY'],
                '当前余额': infos[0]['BAL']
            }
            enterarr.append(enterdic)
            data['companyList']=enterarr
            data['baseInfo']['最近汇缴日期'] = infos[0]['PSN_END_PAY_TIME']
            data['baseInfo']['最近汇缴金额'] = infos[0]['PAY']

            #明细信息
            if not infos[0]['BLD_ACC_TIME']:
                return
            statimeyear=int(infos[0]['BLD_ACC_TIME'][:4])
            endtimeyear=int(time.strftime("%Y-%m-%d", time.localtime())[:4])
            data['detail'] = {}
            data['detail']['data'] = {}
            years = ''
            months = ''
            hjcs = 0
            for i in range(statimeyear,endtimeyear+1):
                statime=str(i)+'-01-01'
                endtime=str(i)+'-12-31'
                datas = {
                    'header': '{"code":0,"message":{"title":"","detail":""}}',
                    'body': '{dataStores:{"psnFormDataStore":{rowSet:{"primary":[{"staTime":"'+statime+'","endTime":"'+endtime+'","_t":""}],"filter":[],"delete":[]},name:"psnFormDataStore",pageNumber:1,pageSize:0,recordCount:0}},parameters:{}}'
                }
                resp = self.s.post(LOGIN_URL + 'method=Biz1002', data=json.dumps(datas),
                                   headers={'ajaxRequest': 'true', 'Content-Type': 'multipart/form-data',
                                            'X-Requested-With': 'XMLHttpRequest'
                                            }, timeout=20)
                soup = BeautifulSoup(resp.content, 'html.parser')
                dicinfo = execjs.eval(soup.text)
                pagesize= dicinfo['body']['dataStores']['psnGridDataStore']['recordCount']
                infos = dicinfo['body']['dataStores']['psnGridDataStore']['rowSet']['primary']
                for y in range(0,len(infos)):
                    cell=infos[y]
                    sr = 0
                    zc = 0
                    arr = []
                    dqye=float(cell['ATTR_BAL'])
                    if '汇缴' in cell['ATTR_SUMMARY']:
                        sr = cell['ATTR_PAY']
                        hjcs = hjcs + 1
                    elif '提取' in cell['ATTR_SUMMARY']:
                        zc = cell['ATTR_PAY']
                    else:
                        sr = cell['ATTR_PAY']
                    dic = {
                        '时间': cell['ATTR_TIME'],
                        '单位名称': data['baseInfo']['单位名称'],
                        '支出': zc,
                        '收入': sr,
                        '汇缴年月': cell['CTB_YM'].replace('-','').replace(' ',''),
                        '余额': cell['ATTR_BAL'],
                        '类型': cell['ATTR_SUMMARY'],
                        '个人账号': cell['PSN_ACC'],
                        '单位账号': cell['ATTR_ORG_ACC']
                    }
                    times = cell['ATTR_TIME'][:7]
                    if years != times[:4]:
                        years = times[:4]
                        data['detail']['data'][years] = {}
                        if months != times[-2:]:
                            months = times[-2:]
                    else:
                        if months != times[-2:]:
                            months = times[-2:]
                        else:
                            arr = data['detail']['data'][years][months]
                    arr.append(dic)
                    data['detail']['data'][years][months] = arr
                if pagesize>10:
                    # datass = {
                    #     'header': '{"code":0,"message":{"title":"","detail":""}}',
                    #     'body': r"{dataStores:{\"psnGridDataStore\":{rowSet:{\"primary\":[],\"filter\":[],\"delete\":[]},name:\"psnGridDataStore\",pageNumber:2,pageSize:10,recordCount:"+str(pagesize)+",conditionValues:[[\""+statime+"\",\"12\"],[\""+endtime+"\",\"12\"]],parameters:{},statementName:\"websys.statistics.psnBizQry\",attributes:{\"staTime\":[\" T.ATTR_TIME \",\"12\"],\"psnAcc\":[\"T.PSN_ACC = '"+data["baseInfo"]["个人账号"]+"'\",\"12\"],\"endTime\":[\" T.ATTR_TIME \",\"12\"]},pool:\"hafmis\"}},parameters:{\"synCount\":\"true\"}}"
                    # }
                    datass="""{header:{"code":0,"message":{"title":"","detail":""}},body:{dataStores:{"psnGridDataStore":{rowSet:{"primary":[],"filter":[],"delete":[]},name:"psnGridDataStore",pageNumber:2,pageSize:10,recordCount:%d,conditionValues:[["%s","12"],["%s","12"]],parameters:{},statementName:"websys.statistics.psnBizQry",attributes:{"staTime":[" T.ATTR_TIME ","12"],"psnAcc":["T.PSN_ACC = '%s'","12"],"endTime":[" T.ATTR_TIME ","12"]},pool:"hafmis"}},parameters:{"synCount":"true"}}}"""%(pagesize,statime,endtime,data["baseInfo"]["个人账号"])
                    resps = self.s.post('http://wsbs.dggjj.gov.cn/web_housing/CommonTransferServlet?method=Com0001', data=datass,
                                       headers={'ajaxRequest': 'true', 'Content-Type': 'multipart/form-data','X-Requested-With': 'XMLHttpRequest','Host':'wsbs.dggjj.gov.cn','Origin':'http://wsbs.dggjj.gov.cn','Referer':'http://wsbs.dggjj.gov.cn/web_housing/orgsys/pages/psnAccsQry/psnQry.jsp','User-Agent':'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3100.0 Mobile Safari/537.36'})
                    soups = BeautifulSoup(resps.content.decode('utf8'), 'html.parser')
                    dicinfos = execjs.eval(soups.text)
                    infos = dicinfos['body']['dataStores']['psnGridDataStore']['rowSet']['primary']
                    for y in range(0, len(infos)):
                        cell = infos[y]
                        sr = 0
                        zc = 0
                        arr = []
                        dqye = float(cell['ATTR_BAL'])
                        if '汇缴' in cell['ATTR_SUMMARY']:
                            sr = cell['ATTR_PAY']
                            hjcs = hjcs + 1
                        elif '提取' in cell['ATTR_SUMMARY']:
                            zc = cell['ATTR_PAY']
                        else:
                            sr = cell['ATTR_PAY']
                        dic = {
                            '时间': cell['ATTR_TIME'],
                            '单位名称': data['baseInfo']['单位名称'],
                            '支出': zc,
                            '收入': sr,
                            '汇缴年月': cell['CTB_YM'].replace('-','').replace(' ',''),
                            '余额': cell['ATTR_BAL'],
                            '类型': cell['ATTR_SUMMARY'],
                            '个人账号': cell['PSN_ACC'],
                            '单位账号': cell['ATTR_ORG_ACC']
                        }
                        times = cell['ATTR_TIME'][:7]
                        if years != times[:4]:
                            years = times[:4]
                            data['detail']['data'][years] = {}
                            if months != times[-2:]:
                                months = times[-2:]
                        else:
                            if months != times[-2:]:
                                months = times[-2:]
                            else:
                                arr = data['detail']['data'][years][months]
                        arr.append(dic)
                        data['detail']['data'][years][months] = arr
            data['baseInfo']['累计汇缴次数'] = hjcs
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        resp = self.s.get(VC_URL)
        return dict(cls='data:image', content=resp.content)
if __name__ == '__main__':
    from services.client import TaskTestClient

    meta = {'用户名': '430281198611245038', '密码': '996336'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()

#用户名：430281198611245038  密码：996336
