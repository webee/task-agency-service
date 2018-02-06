import hashlib
from services.service import SessionData
from bs4 import BeautifulSoup
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask
# https://www.sipspf.org.cn/SZGJJ_ORG/corp/login.jsp
VC_URL='https://www.sipspf.org.cn/person_online/service/identify.do?sessionid='
LOGIN_URL='https://www.sipspf.org.cn/person_online/service/EMPLogin/login'
class Task(AbsFetchTask):
    task_info = dict(
        city_name="苏州园区",
        help=""" """
    )
    def _get_common_headers(self):
        return {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36'
        }

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
        assert '编号' in params, '缺少编号'
        assert '密码' in params, '缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check
        身份证号 = params['编号']
        密码 = params['密码']
        if len(密码) < 4:
            raise InvalidParamsError('编号或密码错误')
        if 身份证号.isdigit():
            if len(身份证号) < 8:
                raise InvalidParamsError('编号错误')
            return
        raise InvalidParamsError('编号或密码错误')
    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '编号' not in params:
                params['编号'] = meta.get('编号')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '编号' and '编号' in meta:
                continue
            elif pr['key'] == '密码' and '密码' in meta:
                continue
            res.append(pr)
        return res

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                id_num = params['编号']
                password = params['密码']
                vc=params['vc']
                resp = self.s.get(
                    'https://www.sipspf.org.cn/person_online/service/problem.do?sessionid=' + self.state['sessionid'])
                soup = BeautifulSoup(resp.content, 'html.parser')
                if '加' in soup.text:
                    jia=soup.text.split('加')
                    daan=int(jia[0])+1
                elif '减' in soup.text:
                    jia=soup.text.split('减')
                    daan=int(jia[0])-1
                elif '乘' in soup.text:
                    jia=soup.text.split('乘')
                    daan=int(jia[0])
                elif '除' in soup.text:
                    jia=soup.text.split('除')
                    daan=int(jia[0])
                resp=self.s.post('https://www.sipspf.org.cn/sipspf/web/pub/activate/checkPwd',data=dict(membid=id_num),headers={'X-Requested-With':'XMLHttpRequest'})
                soup = BeautifulSoup(resp.content, 'html.parser')

                m = hashlib.md5()
                m.update(str(password).encode(encoding="utf-8"))
                hashpsw = m.hexdigest()
                datas = {
                    'uname': id_num,
                    'upass':hashpsw,
                        'identify': vc,
                'answer': daan,
                'param3': ''
                }
                resp = self.s.post(LOGIN_URL, data=datas,headers={'X-Requested-With':'XMLHttpRequest'})
                soup = BeautifulSoup(resp.content, 'html.parser')

                self.result_key = id_num
                # 保存到meta
                self.result_meta['编号'] = id_num
                self.result_meta['密码'] = password

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='编号', name='编号', cls='input', placeholder='社保（公积金）编号', value=params.get('编号', '')),
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
        resp=self.s.get('https://www.sipspf.org.cn/SZGJJ_ORG/corp/login.jsp')
        self.state['sessionid']=resp.cookies._cookies['www.sipspf.org.cn']['/']['JSESSIONID'].value

        vc_url = VC_URL+self.state['sessionid']
        resp = self.s.get(vc_url)
        return dict(cls="data:image", content=resp.content, content_type=resp.headers['Content-Type'])

if __name__ == '__main__':
    from services.client import TaskTestClient

    meta = {'编号': '03670368', '密码': '011982'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()
