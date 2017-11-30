import hashlib
import json
import time
from bs4 import BeautifulSoup
from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask

VC_URL='http://218.28.166.74:8080/zzsbonline/captcha.png?'
LOGIN_URL='http://218.28.166.74:8080/zzsbonline/usersAction!userLogin'
INFO_URL='http://218.28.166.74:8080/zzsbonline/personAction!GetPersonList'
#MX_URL='http://wsbs.zjhz.hrss.gov.cn/unit/web_zgjf_query/web_zgjf_doQuery.html'
class Task(AbsFetchTask):
    task_info = dict(
        city_name="郑州",
        help="""<li>如您未在社保网站查询过您的社保信息，请到郑州社保网上服务平台完成“注册”然后再登录。</li>
        <li>如有问题请拨打12333。</li>""",
        developers=[{'name':'卜圆圆','email':'byy@qinqinxiaobao.com'}]
    )
    def _get_common_headers(self):
        return {'User-Agent':'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1'}

    def _query(self, params: dict):
        """任务状态查询"""
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()
        pass

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '身份证号' in params, '身份证号'
        assert '密码' in params, '缺少密码'
        # other check
        身份证号 = params['身份证号']
        密码 = params['密码']
        if len(密码) < 4:
            raise InvalidParamsError('身份证号或密码错误')
        if 身份证号.isdigit():
            if len(身份证号) < 15:
                raise InvalidParamsError('身份证错误')
            return
        raise InvalidParamsError('身份证号或密码错误')
    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
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
            if pr['key'] == '身份证号' and '身份证号' in meta:
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
                id_num = params['身份证号']
                password = params['密码']
                m = hashlib.md5()
                m.update(str(password).encode(encoding="utf-8"))
                pw = m.hexdigest()
                vc = params['vc']
                respvc=self.s.post('http://218.28.166.74:8080/zzsbonline/companyAction!getRandCode',data=dict(code=vc))
                vctext=BeautifulSoup(respvc.content, 'html.parser')
                if vctext.text=='0':
                    resp = self.s.post(LOGIN_URL, data=dict(
                        cardid=id_num,
                        password=pw,
                        vcode=vc))
                    soup = BeautifulSoup(resp.content, 'html.parser')
                    msg=json.loads(soup.text)
                    err_msg=msg['msgbox']
                    if err_msg=='用户成功登录':
                        err_msg=''
                else:
                    err_msg='验证码错误！'
                if err_msg:
                    raise InvalidParamsError(err_msg)
                else:
                    print("登录成功！")


                self.result_key = params.get('身份证号')
                # 保存到meta
                self.result_meta['身份证号'] = params.get('身份证号')
                self.result_meta['密码'] = params.get('密码')

                self.result_identity['task_name'] = '郑州'
                self.result_identity['target_id'] = id_num
                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)
        vc = self._new_vc()
        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input', placeholder='身份证号', value=params.get('身份证号', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}, value=params.get('vc', '')),
        ], err_msg)

    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            Tokenurl=self.s.get('http://218.28.166.74:8080/zzsbonline/loginAction',timeout=10)
            tokenhtml=BeautifulSoup(Tokenurl.content, 'html.parser')
            tokens=tokenhtml.select('#token')[0].attrs['value']
            resp = self.s.post(INFO_URL,data=dict(idno='',token=tokens),timeout=10)
            soup = BeautifulSoup(resp.content, 'html.parser')
            infors=json.loads(soup.text)
            persontype=infors[0]['persontype']
            if persontype=='3':
                persontype='未办卡'
            insuretype=infors[0]['insuretype']
            if insuretype=='1':
                insuretype='正常参保'
            self.result_data["baseInfo"] = {
                '城市名称': '郑州',
                '城市编号': '410100',
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '姓名': infors[0]['name'],
                '身份证号': infors[0]['idno'],
                '个人编号': infors[0]['personelno'],
                '社会保障卡号码': infors[0]['cardno'],
                '社保卡状态': persontype,
                '单位编号': infors[0]['companyid'],
                '单位名称': infors[0]['companyname'],
                '卡余额': infors[0]['balance'],
                '缴费基数': infors[0]['payBase'],
                '参保状态':insuretype
            }
            self.result_identity['target_name'] = infors[0]['name']
            self.result_identity['status'] =insuretype

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)
    def _new_vc(self):
        self.s.headers.update({
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.8",
            "Connection": "keep-alive",
            "Host": "218.28.166.74:8080",
            "Referer": "http://218.28.166.74:8080/zzsbonline/login.jsp"
        })
        resp = self.s.get(VC_URL)

        return dict(cls='data:image', content=resp.content)

if __name__ == '__main__':
    from services.client import TaskTestClient

    meta = {'身份证号': '410105198801200097', '密码': '988120'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()
#'身份证号': '410105198801200097', '密码': '988120'