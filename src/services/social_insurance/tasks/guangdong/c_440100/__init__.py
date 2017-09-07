from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask

import time
from bs4 import BeautifulSoup
import execjs

class Task(AbsFetchTask):
    task_info = dict(
        city_name="广州",
        help=""""""
    )

    def _get_common_headers(self):
        return {
            'User-Agent':'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36',
            'Accept-Encoding':'gzip, deflate, sdch',
            'Host':'zlss.hrssgz.gov.cn'
        }

    def _prepare(self):
        """恢复状态，初始化结果"""
        super()._prepare()
        # state
        # state: dict = self.state
        # TODO: restore from state

        # result
        # result: dict = self.result
        # TODO: restore from result

    def _update_session_data(self):
        """保存任务状态"""
        super()._update_session_data()
        # state
        # state: dict = self.state
        # TODO: update state

        # result
        # result: dict = self.result
        # TODO: update temp result

    def _query(self, params: dict):
        """任务状态查询"""
        pass

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '账号' in params, '缺少账号'
        assert '密码' in params, '缺少密码'
        # other check
        账号 = params['账号']
        密码 = params['密码']
        if len(密码) < 4:
            raise InvalidParamsError('账号或密码错误')
        if len(账号) < 4:
            raise InvalidParamsError('账号或密码错误')

    def _loadJs(self):
        jsstr = self.s.get("http://gzlss.hrssgz.gov.cn/cas/third/security.js")
        ctx = execjs.compile(jsstr.text)
        modlus="00a6adde094d3a76cd88df34026e9b034560485c1c0c90fab750c4335de9968532b3ce99503c7f856238c51c9494d069f274cacaa0c918013c08bab250602f6d71f91e60980942ed9b5e6fcc069f78a831d3dd9b3b45a10c8f19d0b29c8c26aa5aff535ecf27ef3ca0b0d0f008ce587f1c6e427e4724f8e8bf5414f286dac64957"
        print(ctx.call('getKeyPair', '010001','',modlus))

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                self.result_key = params.get('账号')
                # 保存到meta
                self.result_meta['账号'] = params.get('账号')
                self.result_meta['密码'] = params.get('密码')

                resp = self.s.get("http://gzlss.hrssgz.gov.cn/cas/login")
                lt=BeautifulSoup(resp.content,'html.parser').find('input',{'name':'lt'})['value']
                data={
                    'usertype':"2",
                    'lt':lt,
                    'username':params.get('账号'),
                    'password':params.get('密码'),
                    '_eventId':'submit'
                }

                resps=self.s.post("http://gzlss.hrssgz.gov.cn/cas/login",data)
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='账号', name='账号', cls='input', value=params.get('账号', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
        ], err_msg)

    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient
    client = TaskTestClient(Task(SessionData()))
    client.run()

    # 441225199102281010  wtz969462
