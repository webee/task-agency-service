import time,datetime,json
from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask
from bs4 import BeautifulSoup

LOGIN_URL='http://wsbs.dggjj.gov.cn/web_housing/CommonTransferServlet?method=Com0002'#http://wsbs.dggjj.gov.cn/web_housing/unieap/pages/login/login.jsp#
VC_URL='http://wsbs.dggjj.gov.cn/web_housing/ValidateCodeServlet'
class Task(AbsFetchTask):
    task_info = dict(
        city_name="东莞",

        developers=[{'name':'卜圆圆','email':'byy@qinqinxiaobao.com'}]
    )

    def _get_common_headers(self):
        return {'User-Agent':'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3100.0 Mobile Safari/537.36'}

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


    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                id_num = params['用户名']
                password = params['密码']
                vc = params['vc']
                data = {
                    'header':'{"code":0,"message":{"title":"","detail":""}}',
                    'body': '{dataStores: {},parameters: {"code": "'+vc+'", "j_password": "'+password+'", "j_username": "'+id_num+'"}}'
                }
                resp = self.s.post(LOGIN_URL, data=data, timeout=20)
                soup = BeautifulSoup(resp.content, 'html.parser')
                ylinfo = json.loads(soup.text)
                if ylinfo['message']:
                    return_message = ylinfo['message']
                    raise InvalidParamsError(return_message)
                else:
                    print("登录成功！")
                self.result_key = params.get('用户名')
                # 保存到meta
                self.result_meta['用户名'] = params.get('用户名')
                self.result_meta['密码'] = params.get('密码')

                raise TaskNotImplementedError('查询服务维护中')
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
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        resp = self.s.get(VC_URL)
        return dict(cls='data:image', content=resp.content)
if __name__ == '__main__':
    from services.client import TaskTestClient
    client = TaskTestClient(Task(SessionData()))
    client.run()

#用户名：430281198611245038  密码：996336
