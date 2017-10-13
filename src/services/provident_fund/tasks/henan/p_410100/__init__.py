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
        assert 'idCard' in params, '缺少身份证号'
        assert 'fullname' in params, '缺少用户姓名'
        assert 'pass' in params, '缺少密码'
        # other check
        身份证号 = params['idCard']
        用户姓名 = params['fullname']
        密码 = params['pass']

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
            if 'idCard' not in params:
                params['idCard'] = meta.get('idCard')
            if 'fullname' not in params:
                params['fullname'] = meta.get('fullname')
            if 'pass' not in params:
                params['pass'] = meta.get('pass')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == 'idCard' and 'idCard' in meta:
                continue
            elif pr['key'] == 'fullname' and 'fullname' in meta:
                continue
            elif pr['key'] == 'pass' and 'pass' in meta:
                continue
            res.append(pr)
        return res


    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                self.result_data['companyList']=[]
                id_num = params.get("idCard")
                account_name = params.get("fullname")
                account_pass = params.get("pass")

                data = {
                    'name': account_name,
                    'sfzh': id_num,
                    'mm': account_pass,
                }
                resp = self.s.post(LOGIN_URL, data=data)

                self.result_key = id_num
                self.result_meta['身份证号'] =id_num
                self.result_meta['用户姓名'] = account_name
                self.result_meta['登录密码']=account_pass

                soup = BeautifulSoup(resp.content, 'html.parser')
                datas = soup.findAll('div', {'class': 'cx'})[0]
                data = datas.findAll('p')

                self.result['data']['baseInfo'] = {
                    '姓名': data[3].text.split('：')[1],
                    '证件号': self.result_meta['身份证号'],
                    '证件类型':'身份证',
                    '公积金账号': data[0].text.split('：')[1],
                    '开户日期': data[2].text.split('：')[1],
                    '缴存基数': data[4].text.split('：')[1],
                    '月缴额': data[5].text.split('：')[1],
                    '个人缴存比例': data[6].text.split('：')[1],
                    '单位缴存比例': data[7].text.split('：')[1],
                    '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                    '城市名称': '郑州市',
                    '城市编号': '410100'
                }

                self.result_data['companyList'].append({
                    "单位名称": data[1].text.split('：')[1],
                    "单位登记号": "-",
                    "所属管理部编号": "-",
                    "所属管理部名称": "-",
                    "当前余额": float(data[8].text.split('：')[1]),
                    "帐户状态": data[10].text.split('：')[1],
                    "当年缴存金额": "-",
                    "当年提取金额": "-",
                    "上年结转余额": "-",
                    "最后业务日期": data[9].text.split('：')[1],
                    "转出金额": "-"
                })


                # identity 信息
                self.result['identity'] = {
                    "task_name": "郑州",
                    "target_name": self.result_meta['用户姓名'],
                    "target_id": self.result_meta['身份证号'],
                    "status":  data[10].text.split('：')[1]
                }

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='idCard', name='身份证号', cls='input', value=params.get('idCard', '')),
            dict(key='fullname', name='用户姓名', cls='input', value=params.get('fullname', '')),
            dict(key='pass', name='密码', cls='input', value=params.get('pass', '')),
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
