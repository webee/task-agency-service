# cff---郑州--河南省省会   公积金信息

import time
import requests
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError
import re

MAIN_URL = r'http://wx.zzgjj.com/pcweb/pcchaxun/chaxun'
LOGIN_URL = r"http://wx.zzgjj.com/pcweb/pcchaxun/chaxun"
VC_URL = r""


class Task(AbsTaskUnitSessionTask):

    def _prepare(self):
        state: dict = self.state
        self.s = requests.Session()
        cookies = state.get('cookies')
        if cookies:
            self.s.cookies = cookies
        self.s.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; rv:54.0) Gecko/20100101 Firefox/54.0',
                'Accept-Encoding':'gzip, deflate',
                'Host': 'wx.zzgjj.com',
        })

        # result
        result: dict = self.result
        result.setdefault('key',{})
        result.setdefault('meta', {})
        result.setdefault('data', {})

    def _update_session_data(self):
        super()._update_session_data()
        self.state['cookies'] = self.s.cookies

    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_name, self._unit_login)

    def _query(self, params: dict):
         t = params.get('t')
         if True:
             return self._new_vc()

    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert 'id_num' in params, '缺少身份证号'
        assert 'account_pass' in params, '缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check

    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                id_num = params['id_num']
                account_name = params['account_name']
                password=params['password']

                data={
                    'name': account_name,
                    'sfzh': id_num,
                    'mm': password,
                }
                resp = self.s.post(LOGIN_URL, data=data)
                soup = BeautifulSoup(resp.content, 'html.parser')
                data = soup.find('div', {'class': 'query-wrap'})
                data = re.sub('\s', '', data.text)

                self.result['data']['baseInfo'] = {
                    '公积金账户': re.findall(r"公积金账户：(.+?)单位信息", data)[0],
                    '单位信息': re.findall(r"单位信息：(.+?)开户日期", data)[0],
                    '开户日期': re.findall(r"开户日期：(.+?)缴存人姓名", data)[0],
                    '缴存人姓名': re.findall(r"缴存人姓名：(.+?)缴存基数", data)[0],
                    '缴存基数': re.findall(r"缴存基数：(.+?)月缴额", data)[0],
                    '月缴额': re.findall(r"月缴额：(.+?)个人缴存比例", data)[0],
                    '个人缴存比例': re.findall(r"个人缴存比例：(.+?)单位缴存比例", data)[0],
                    '单位缴存比例': re.findall(r"单位缴存比例：(.+?)缴存余额", data)[0],
                    # '缴存余额':self.replaceHTMLNone(re.findall(r"缴存余额：(.+?)缴至月份", data)),
                    '缴至月份': re.findall(r"缴至月份：(.+?)缴存状态", data)[0],
                    '缴存状态': re.findall(r"缴存状态：(.+)", data)[0],
                }

                self.result['key'] = id_num
                self.result['meta'] = {
                    '身份证号': id_num,
                    '用户姓名':account_name,
                    '登录密码': password
                }
                return
            except Exception as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='id_num', name='身份证号', cls='input'),
            dict(key='account_name', name='用户姓名', cls='input'),
            dict(key='password', name='密码', cls='input'),
        ], err_msg)

    def _unit_fetch_name(self):
        try:
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        return True

if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()

    # 410105198205183841  徐琳佳  111111
