from bs4 import BeautifulSoup
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask

LOGIN_URL = 'http://wscx.xmgjj.gov.cn/xmgjjGR/index.jsp'
VC_URL = 'http://wscx.xmgjj.gov.cn/xmgjjGR/codeImage.shtml'
class Task(AbsFetchTask):
    task_info = dict(
        city_name="厦门",
        help="""<li>如您未在公积金网站查询过您的公积金信息，请到厦门公积金管理中心官网网完成“注册”然后再登录。</li>""",
        developers=[{'name':'卜圆圆','email':'byy@qinqinxiaobao.com'}]

    )
    def _get_common_headers(self):
        return {'User-Agent':'Mozilla/5.0 (iPad; CPU OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1'}

    def _query(self, params: dict):
        """任务状态查询"""
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

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
        if 账号.isdigit():
            if len(账号) < 15:
                raise InvalidParamsError('身份证错误')
            return
        raise InvalidParamsError('账号或密码错误')

    def _unit_login(self, params: dict):
        Frist_Time=False
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                id_num = params['账号']
                password = params['密码']
                vc=''
                if Frist_Time:
                    vc = params['vc']
                data = dict(
                    securityCode2=vc,
                    securityCode=vc,
                    username=id_num,
                    password=password
                )
                resp = self.s.post(LOGIN_URL, data=data,
                                   headers={'Content-Type': 'application/x-www-form-urlencoded'})

                soup = BeautifulSoup(resp.content, 'html.parser')

                return_message = soup.select('#err_area')[0].find('font').text
                if len(return_message.text) > 3:
                    Frist_Time=True
                    return_message = return_message.text.split(';')[0].split('"')[1]
                    raise InvalidParamsError(return_message)
                else:
                    print("登录成功！")

                self.result_key = params.get('账号')
                # 保存到meta
                self.result_meta['账号'] = params.get('账号')
                self.result_meta['密码'] = params.get('密码')


            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        if Frist_Time:
            vc = self._new_vc()
            raise AskForParamsError([
                dict(key='账号', name='账号', cls='input', placeholder='证件号码', value=params.get('账号', '')),
                dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
                dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
            ], err_msg)
        else:
            raise AskForParamsError([
                dict(key='账号', name='账号', cls='input', placeholder='证件号码', value=params.get('账号', '')),
                dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            ], err_msg)

    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)
    def _new_vc(self):
        vc_url = VC_URL #+ str(int(time.time() * 1000))
        resp = self.s.get(vc_url)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])


if __name__ == '__main__':
    from services.client import TaskTestClient
    meta = {'账号': '350821199411230414', '密码': '20120305xin'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()

    #账号：350821199411230414  密码：20120305xin
