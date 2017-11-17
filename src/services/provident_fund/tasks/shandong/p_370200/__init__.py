from bs4 import BeautifulSoup
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask

LOGIN_URL = 'http://219.147.7.52:89/Controller/login.ashx'
VC_URL='http://219.147.7.52:89/Controller/Image.aspx'
INFO_URL='http://www.cqgjj.cn/Member/gr/gjjyecx.aspx'
MINGXI_URL='http://www.cqgjj.cn/Member/gr/gjjmxcx.aspx'
class Task(AbsFetchTask):
    task_info = dict(
        city_name="青岛",
        help="""<li>首次登陆密码默认为住房公积金个人编号后6位。</li>
            <li>住房公积金个人编号取得方式：
                本人持住房公积金联名卡到所属银行自助终端查询；本人持身份证到住房公积金管理中心各管理处查询；本人到单位住房公积金经办人处查询。
            </li>""",
        developers = [{'name': '卜圆圆', 'email': 'byy@qinqinxiaobao.com'}]
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
        assert '身份证号' in params, '缺少身份证号'
        assert '密码' in params, '缺少密码'

        # other check
        身份证号 = params['身份证号']
        密码 = params['密码']
        if len(密码) < 6:
            raise InvalidParamsError('身份证号或密码错误')
        if 身份证号.isdigit():
            if len(身份证号) <15:
                raise InvalidParamsError('身份证号错误')
            return
        raise InvalidParamsError('身份证号或密码错误')

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                id_num = params['身份证号']
                password = params['密码']
                vc = params['vc']
                data={
                    'name': id_num,
                    'password': password,
                    'yzm':vc,
                    'logintype': '0',
                    'usertype': '10',
                    'dn':'',
                    'signdata':'',
                    '1': 'y'
                }
                resp = self.s.post(LOGIN_URL, data=data)
                soup = BeautifulSoup(resp.content, 'html.parser')

                return_message = soup.find('input', {'name': 'return_message'})["value"]

                if return_message:
                    raise InvalidParamsError(return_message)
                else:
                    print("登录成功！")
                    self.html = str(resp.content, 'gbk')

                self.result_key = params.get('身份证号')
                # 保存到meta
                self.result_meta['身份证号'] = params.get('身份证号')
                self.result_meta['密码'] = params.get('密码')
                self.result_identity['task_name'] = '青岛'

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input', placeholder='身份证号', value=params.get('身份证号', '')),
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
        #vc_url = VC_URL  # + str(int(time.time() * 1000))
        resp = self.s.get(VC_URL)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])
if __name__ == '__main__':
    from services.client import TaskTestClient

    meta = {'身份证号': '370881198207145816', '密码': '080707'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()

