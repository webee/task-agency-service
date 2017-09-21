# cff---郑州--河南省省会   公积金信息

import time
import requests
from bs4 import BeautifulSoup
import re

from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError, InvalidConditionError, \
    PreconditionNotSatisfiedError
from services.commons import AbsFetchTask

MAIN_URL = r'http://wx.zzgjj.com/pcweb/pcchaxun/chaxun'
LOGIN_URL = r"http://wx.zzgjj.com/pcweb/pcchaxun/chaxun"
VC_URL = r""


class Task(AbsFetchTask):
    task_info = dict(
        city_name="郑州",
        help="""
            <li></li>
            """
    )

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; rv:54.0) Gecko/20100101 Firefox/54.0',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'wx.zzgjj.com',
        }

    def _prepare(self, data=None):
        super()._prepare()
        self.result_data['baseInfo']={}
        self.result_data['companyList']={}

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '身份证号' in params, '缺少身份证号'
        assert '用户姓名' in params, '缺少用户姓名'
        assert '密码' in params, '缺少密码'
        # other check
        身份证号 = params['身份证号']
        用户姓名 = params['用户姓名']
        密码 = params['密码']

        if len(身份证号) == 0:
            raise InvalidParamsError('身份证号为空，请输入身份证号')
        elif len(身份证号) < 15:
            raise InvalidParamsError('身份证号不正确，请重新输入')

        if len(用户姓名) == 0:
            raise InvalidParamsError('用户姓名为空，请输入用户姓名')

        if len(密码) == 0:
            raise InvalidParamsError('密码为空，请输入密码！')
        elif len(密码) < 6:
            raise InvalidParamsError('密码不正确，请重新输入！')

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '身份证号' not in params:
                params['身份证号'] = meta.get('身份证号')
            if '用户姓名' not in params:
                params['用户姓名'] = meta.get('用户姓名')
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
            elif pr['key'] == '用户姓名' and '用户姓名' in meta:
                continue
            elif pr['key'] == '密码' and '密码' in meta:
                continue
            res.append(pr)
        return res


    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params.get("身份证号")
                account_name = params.get("用户姓名")
                account_pass = params.get("密码")

                data = {
                    'name': account_name,
                    'sfzh': id_num,
                    'mm': account_pass,
                }
                resp = self.s.post(LOGIN_URL, data=data)

                self.result_key = id_num
                self.result_meta['身份证号'] =id_num
                self.result_meta['用户姓名'] = account_name
                self.result_meta['密码']=account_pass

                soup = BeautifulSoup(resp.content, 'html.parser')
                data = soup.find('div', {'class': 'query-wrap'})
                data = re.sub('\s', '', data.text)

                self.result['data']['baseInfo'] = {
                    '公积金账户': re.findall(r"公积金账户：(.+?)单位信息", data)[0],
                    '开户日期': re.findall(r"开户日期：(.+?)缴存人姓名", data)[0],
                    '姓名': re.findall(r"缴存人姓名：(.+?)缴存基数", data)[0],
                    '身份证号': self.result_meta['身份证号'],
                    '缴存基数': re.findall(r"缴存基数：(.+?)月缴额", data)[0],
                    '月缴额': re.findall(r"月缴额：(.+?)个人缴存比例", data)[0],
                    '个人缴存比例': re.findall(r"个人缴存比例：(.+?)单位缴存比例", data)[0],
                    '单位缴存比例': re.findall(r"单位缴存比例：(.+?)缴存余额", data)[0],
                }

                self.result_data['companyList'] = {
                    "单位名称": re.findall(r"单位信息：(.+?)开户日期", data)[0],
                    "单位登记号": "-",
                    "所属管理部编号": "-",
                    "所属管理部名称": "-",
                    "当前余额": re.findall(r"缴存余额：(.+?)缴至月份", data)[0],
                    "帐户状态": re.findall(r"缴存状态：(.+)", data)[0],
                    "当年缴存金额": "-",
                    "当年提取金额": "-",
                    "上年结转余额": "-",
                    "最后业务日期": re.findall(r"缴至月份：(.+?)缴存状态", data)[0],
                    "转出金额": "-"
                }

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input'),
            dict(key='用户姓名', name='用户姓名', cls='input'),
            dict(key='密码', name='密码', cls='input'),
        ], err_msg)

    def _unit_fetch(self):
        try:

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        return True


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task(SessionData()))
    client.run()

    # 410105198205183841  徐琳佳  111111
