import time
import requests
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError
from services.errors import InvalidParamsError, InvalidConditionError
from services.commons import AbsFetchTask

MAIN_URL = 'http://szsbzx.jsszhrss.gov.cn:9900/web/website/personQuery/personQueryAction.action'
LOGIN_URL = 'http://szsbzx.jsszhrss.gov.cn:9900/web/website/indexProcess?frameControlSubmitFunction=checkLogin'
VC_URL = 'http://szsbzx.jsszhrss.gov.cn:9900/web/website/rand.action?r='


class Task(AbsFetchTask):
    task_info = {
        'task_name': '真实抓取',
        'help': '测试真实抓取'
    }

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36'
        }

    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_name, self._unit_login)

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if 'id_num' not in params:
                params['id_num'] = meta.get('id_num')
            if 'account_num' not in params:
                params['account_num'] = meta.get('account_num')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == 'id_num' and 'id_num' in meta:
                continue
            elif pr['key'] == 'account_num' and 'account_num' in meta:
                continue
            res.append(pr)
        return res

    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert 'id_num' in params, '缺少身份证号'
        assert 'account_num' in params, '缺少个人编号'
        assert 'vc' in params, '缺少验证码'
        # other check

    def _unit_login(self, params=None):
        err_msg = None
        if params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params['id_num']
                account_num = params['account_num']
                vc = params['vc']

                resp = self.s.post(LOGIN_URL, data=dict(
                    sfzh=id_num,
                    grbh=account_num,
                    yzcode=vc
                ))
                data = resp.json()
                errormsg = data.get('errormsg')
                if errormsg:
                    raise InvalidParamsError(errormsg)

                self.result['key'] = id_num
                self.result['meta'] = {
                    'id_num': id_num,
                    'account_num': account_num
                }
                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='id_num', name='身份证号', cls='input'),
            dict(key='account_num', name='个人编号', cls='input'),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch_name(self):
        try:
            # 设置data
            data = self.result['data']
            resp = self.s.get(MAIN_URL)
            # FIXME:
            # soup = BeautifulSoup(resp.content, 'html.parser')
            # name = soup.select('#kind1 > table > tbody > tr:nth-child(2) > td:nth-child(2)')[0]['value']
            data['name'] = '卜礼祥'

            # 设置identity
            identity: dict = self.result['identity']
            identity.update({
                'task_name': '测试real',
                'target_name': data['name'],
                'target_id': self.result['meta']['id_num'],
                'status': '正常',
            })

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        vc_url = VC_URL + str(int(time.time() * 1000))
        resp = self.s.get(vc_url)
        return dict(cls='data:image', content=resp.content, content_type=resp.headers.get('Content-Type'))


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()
