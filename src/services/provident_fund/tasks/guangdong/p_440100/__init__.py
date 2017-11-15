# cff---广州--公积金账号采集

import time
import requests

from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError, InvalidConditionError, \
    PreconditionNotSatisfiedError
from services.commons import AbsFetchTask

LoginUrl="https://gzgjj.gov.cn/wsywgr/"


class Task(AbsFetchTask):
    task_info = dict(
        city_name="广州",
        help="""
            <li>公积金账号一般为身份证号后面+00或者01（顺序生成）。</li>
            <li>个人密码当天连续错误输入累计3次，则系统自动锁定账户，第二天才能继续验证；错误连续累计超过10次的，将被锁定账户，职工可持本人身份证明原件前往住房公积金归集业务经办网点办理解锁。</li>
            """,

        developers=[{'name': '程菲菲', 'email': 'feifei_cheng@chinahrs.net'}]
    )

    def _get_common_headers(self):
        return {
        }

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
        assert '证件号' in params, '缺少证件号'
        assert '姓名' in params, '缺少姓名'
        assert '密码' in params, '缺少密码'
        # other check
        证件号 = params['证件号']
        姓名=params['姓名']
        密码 = params['密码']

        if len(证件号) == 0:
            raise InvalidParamsError('证件号为空，请输入证件号！')
        elif len(证件号)!=15 and len(证件号)!=18:
            raise InvalidParamsError('证件号不正确，请重新输入！')

        if len(姓名)==0:
            raise InvalidParamsError("姓名为空，请输入姓名！")

        if len(密码) == 0:
            raise InvalidParamsError('密码为空，请输入密码！')
        elif len(密码) < 6:
            raise InvalidParamsError('密码不正确，请重新输入！')

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '证件号' not in params:
                params['证件号'] = meta.get('证件号')
            if '姓名' not in params:
                params['姓名'] = meta.get('姓名')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '证件号' and '证件号' in meta:
                continue
            elif pr['key'] == '姓名' and '姓名' in meta:
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
                id_num = params.get("证件号")
                username=params.get("姓名")
                account_pass = params.get("密码")
                # vc = params.get("vc")

                self.result_key = id_num
                self.result_meta['证件号'] =id_num
                self.result_meta['姓名'] = username
                self.result_meta['密码']=account_pass

                raise TaskNotImplementedError('查询服务维护中')

            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='证件号', name='证件号', cls='input',value=params.get('证件号', '')),
            dict(key='姓名', name='姓名', cls='input', value=params.get('姓名', '')),
            dict(key='密码', name='密码', cls='input:password',value=params.get('密码', '')),
        ], err_msg)


    def _unit_fetch(self):
        try:

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task(SessionData()))
    client.run()
