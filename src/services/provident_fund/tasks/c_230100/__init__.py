import time
import requests
import re
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError


MAIN_URL = 'https://fund.hrbgjj.gov.cn:8443/fund/webSearchInfoAction.do?method=process'
LOGIN_URL = 'https://fund.hrbgjj.gov.cn:8443/fund/webSearchInfoAction.do?method=process'
VC_URL = 'https://fund.hrbgjj.gov.cn:8443/fund/webSearchInfoAction.do?method=process&dispatch=genetateValidatecode'


class Task(AbsTaskUnitSessionTask):
    # noinspection PyAttributeOutsideInit
    def _prepare(self):
        state: dict = self.state
        self.s = requests.Session()
        self.s.verify= False
        cookies = state.get('cookies')
        if cookies:
            self.s.cookies = cookies
        self.s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3141.7 Safari/537.36'
        })

        # result
        result: dict = self.result
        result.setdefault('meta', {})
        result.setdefault('data', {})

    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_name, self._unit_login)

    def _update_session_data(self):
        super()._update_session_data()
        self.state['cookies'] = self.s.cookies

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert 'id_num' in params, '缺少身份证号'
        assert 'account_num' in params, '缺少个人帐号'
        assert 'password' in params,'确实密码'
        assert 'vc' in params, '缺少验证码'
        # other check

    def _unit_login(self, params=None):
        err_msg = None
        params
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params['id_num']
                account_num = params['account_num']
                password=params['password']
                vc = params['vc']

                resp = self.s.post(LOGIN_URL, data=dict(
                    dispatch= 'fund_search',
                    return_message='',
                    id_card=id_num,
                    id_account=account_num,
                    searchpwd=password,
                    validcode=vc
                ))
                soup = BeautifulSoup(resp.content, 'html.parser')
                return_message = soup.find('input', {'name': 'return_message'})["value"]

                if return_message:
                    raise Exception(return_message)
                else:
                    print("登录成功！")
                    self.html = str(resp.content, 'gbk')

                self.result['key'] = '%s.%s' % ('real', id_num)
                self.result['meta'] = {
                    'task': 'real',
                    'id_num': id_num,
                    'account_num': account_num,
                    'password':password,
                    'updated': time.time()
                }
                return
            except Exception as e:
                err_msg = str(e)

        vc = self._new_vc()
        raise AskForParamsError([
            dict(key='id_num', name='身份证号', cls='input'),
            dict(key='account_num', name='个人账号', cls='input'),
            dict(key='password',name='密码',cls='input'),
            dict(key='vc', name='验证码', cls='data:image', data=vc, query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch_name(self):
        try:
            data = self.result['data']
            resp = self.html
            soup = BeautifulSoup(resp, 'html.parser')
            table_text=soup.findAll('table')
            rows = table_text[2].find_all('tr')
            for row in rows:
                cell = [i.text for i in row.find_all('td')]
                if len(cell)==4:
                    data[cell[0].replace('\n','')] = re.sub('[\n              \t  \n\r]','',cell[1].replace('\xa0',''))
                    data[cell[2].replace('\n','')] = re.sub('[\n              \t  \n\r]','',cell[3].replace('\xa0',''))
                #elif len(cell)==2:
                    #data[cell[0].replace('\n','')] = re.sub('[\n              \t  \n\r]','',cell[1].replace('\xa0',''))
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        vc_url = VC_URL #+ str(int(time.time() * 1000))
        resp = self.s.get(vc_url)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()
