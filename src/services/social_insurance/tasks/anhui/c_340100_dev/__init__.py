
from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask


LOGIN_URL='http://60.173.202.220/wssb/grlogo.jsp'
VC_URL='http://60.173.202.220/wssb/servlet/VaildCode'
LogPost_URL='http://60.173.202.220/wssb/admin/grpass.jsp'

class Task(AbsFetchTask):
    task_info = dict(
        city_name="合肥",
        help="""
        <li>1.初始密码为社会保障卡卡号（卡号中的字母必须大写），登陆后请自行修改密码！</li>
        <li>2.公民身份证号码是每个公民唯一的、终身不变的身份代码，由公安机关按照公民身份证号码国家标准编制。一般为15位或者18位数字。</li>
        """,

        developers=[{'name':'程菲菲','email':'feifei_cheng@chinahrs.net'}]
    )


    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.12333sh.gov.cn',
        }

    def _query(self, params: dict):
        """任务状态查询"""
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()
        #pass

    def _new_vc(self):
        resp = self.s.get(VC_URL)
        return dict(cls='data:image',content=resp.content,content_type=resp.headers['Content-Type'])


    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '姓名' in params, '缺少姓名'
        assert '身份证号' in params, '缺少身份证号'
        assert '密码' in params, '缺少密码'

        # other check
        姓名 = params['姓名']
        身份证号 = params['身份证号']
        密码 = params['密码']

        if len(姓名) <=1:
            raise InvalidParamsError('请输入姓名')
        if len(身份证号) <15 or len(身份证号)>18:
            raise InvalidParamsError('身份证输入有误')
        if len(密码) < 6:
            raise InvalidParamsError('密码输入有误')


    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '姓名' not in params:
                params['姓名'] = meta.get('姓名')
            if '身份证号' not in params:
                params['身份证号'] = meta.get('身份证号')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '姓名' and '姓名' in meta:
                continue
            elif pr['key'] == '身份证号' and '身份证号' in meta:
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
                self.result_key = params.get('身份证号')

                # 保存到meta
                self.result_meta['姓名'] = params.get('姓名')
                self.result_meta['身份证号'] = params.get('身份证号')
                self.result_meta['密码'] = params.get('密码')

                raise TaskNotImplementedError('查询服务维护中')

            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='姓名', name='姓名', cls='input', value=params.get('姓名', '')),
            dict(key='身份证号', name='身份证号', cls='input', value=params.get('身份证号', '')),
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


    # 魏林甲    341125197810295239    197810qw