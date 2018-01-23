import datetime
from bs4 import BeautifulSoup
from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask

LOGIN_URL='http://wsbs.njhrss.gov.cn/NJLD/LoginAction'#http://wsbs.njhrss.gov.cn/NJLD/
VC_URL='http://wsbs.njhrss.gov.cn/NJLD/Images'
class Task(AbsFetchTask):
    task_info = dict(
        city_name="南京",
        help="""""",
        developers=[{'name':'卜圆圆','email':'byy@qinqinxiaobao.com'}]
    )

    def _get_common_headers(self):
        return {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3100.0 Safari/537.36'}

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
        assert 'other' in params, '请选择登录方式'
        if params["other"] == "1":
            assert 'bh1' in params, '缺少社会卡号'
            assert 'mm1' in params, '缺少密码'
        elif params["other"] == "3":
            assert 'bh3' in params, '缺少身份证号'
            assert 'mm3' in params, '缺少密码'
        # other check
        if params["other"] == "1":
            用户名 = params['bh1']
        elif params["other"] == "3":
            用户名 = params['bh3']
        if params["other"] == "1":
            密码 = params['mm1']
        elif params["other"] == "3":
            密码 = params['mm3']
        if len(密码) < 4:
            raise InvalidParamsError('密码错误')

        if len(用户名) <8:
            raise InvalidParamsError('用户名错误！')
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert 'other' in params, '请选择登录方式'
        if params["other"] == "3":
            assert 'bh3' in params, '缺少身份证号'
            assert 'mm3' in params, '缺少密码'
        elif params["other"] == "1":
            assert 'bh1' in params, '缺少社会卡号'
            assert 'mm1' in params, '缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check
        if params["other"] == "1":
            用户名 = params['bh1']
        elif params["other"] == "3":
            用户名 = params['bh3']
        if params["other"] == "1":
            密码 = params['mm1']
        elif params["other"] == "3":
            密码 = params['mm3']

        if len(密码) < 4:
            raise InvalidParamsError('用户名或密码错误')
        if len(用户名) < 5:
            raise InvalidParamsError('登陆名错误')

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                vc=params['vc']
                if params["other"] == "3":
                    code = "3"
                    datas={
                        'u': params['bh' + code],
                        'p': params['mm' + code],
                        'key': vc,
                        'dl':''
                    }
                    LOGIN_URLb=LOGIN_URL+'?act=PersonLogin'
                elif params["other"] == "1":
                    code = "1"
                    datas = {
                        'u': params['bh' + code],
                        'p': params['mm' + code],
                        'key': vc,
                        'lx':'1',
                        'dl': ''
                    }
                    LOGIN_URLb = LOGIN_URL + '?act=CompanyLoginPerson'
                id_num = params['bh' + code]
                password = params['mm' + code]
                header = {
                    'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate',
                    'Accept-Language':'zh-CN,zh;q=0.8',
                    'Cache-Control':'max-age=0',
                    'Connection': 'keep-alive',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Upgrade-Insecure-Requests':'1',
                    'Host':'wsbs.njhrss.gov.cn',
                    'Origin':'http://wsbs.njhrss.gov.cn',
                    'Referer':'http://wsbs.njhrss.gov.cn/NJLD/',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3100.0 Safari/537.36'
                }
                self.s.post("http://wsbs.njhrss.gov.cn/NJLD/",headers=header)
                resp = self.s.post(LOGIN_URLb, data=datas)
                soup = BeautifulSoup(resp.content, 'html.parser')
                if 'success' in soup.text:
                    print("登录成功！")
                else:
                    return_message = soup.text.replace("['", "").replace("']", "")
                    raise InvalidParamsError(return_message)
                self.result_key = id_num
                # 保存到meta
                self.result_meta['用户名'] = id_num
                self.result_meta['密码'] = password

                raise TaskNotImplementedError('查询服务维护中')
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='other',
                     name='[{"tabName":"社会保障卡号","tabCode":"1","isEnable":"1"},{"tabName":"身份证号","tabCode":"3","isEnable":"1"}]',
                 cls='tab', value=params.get('类型Code', '')),
            dict(key='bh1', name='社会卡号', cls='input', tabCode="1", value=params.get('用户名', '')),
            dict(key='mm1', name='密码', cls='input:password', tabCode="1", value=params.get('密码', '')),
            dict(key='bh3', name='身份证号', cls='input', tabCode="3", value=params.get('用户名', '')),
            dict(key='mm3', name='密码', cls='input:password', tabCode="3", value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}, tabCode="[1,3]", value=''),
        ], err_msg)

    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)
    def _new_vc(self):
        resp = self.s.get(VC_URL)
        return dict(cls='data:image', content=resp.content, content_type=resp.headers.get('Content-Type'))

if __name__ == '__main__':
    from services.client import TaskTestClient
    client = TaskTestClient(Task())
    client.run()
#用户名：320113197712104814  密码：85226073