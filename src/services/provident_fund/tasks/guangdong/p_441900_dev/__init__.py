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
            data = {
                'header': '{"code":0,"message":{"title":"","detail":""}}',
                'body': '{dataStores:{},parameters:{"certType":"","psnName":"","psnAccSt":"","orgAcc":"","certNo":""}}'
            }
            resp = self.s.post(LOGIN_URL + 'method=Biz1003', data=json.dumps(data),
                               headers={'ajaxRequest': 'true', 'Content-Type': 'multipart/form-data',
                                        'X-Requested-With': 'XMLHttpRequest'
                                        }, timeout=20)
            soup = BeautifulSoup(resp.content, 'html.parser')
            dicinfo=execjs.eval(soup.text)
            infos=dicinfo['body']['dataStores']['psnZSInfoDs']['rowSet']['primary']
            data = self.result_data
            data['baseInfo'] = {
                '城市名称': '东莞',
                '城市编号': '441900',
                '证件类型': '身份证' if infos[0]['CERT_TYPE']=='0' else '',
                '证件号': infos[0]['CERT_NO'],
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '个人账号': infos[0]['PSN_ACC'],
                '姓名': infos[0]['PSN_NAME'],
                '账户状态': '正常' if infos[0]['PSN_ACC_ST']=='1' else '停缴',
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
            self.result_identity['target_id'] =data['baseInfo']['证件号']
            self.result_identity['target_name'] = data['baseInfo']['姓名']
            self.result_identity['status'] = data['baseInfo']['账户状态']
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
