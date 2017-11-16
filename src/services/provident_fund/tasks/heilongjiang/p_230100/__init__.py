import time
import requests
import re
import ssl
requests.packages.urllib3.disable_warnings()
from bs4 import BeautifulSoup
from services.errors import InvalidParamsError
from services.service import AskForParamsError, PreconditionNotSatisfiedError
from services.commons import AbsFetchTask

MAIN_URL = 'https://fund.hrbgjj.org.cn:8443/fund/webSearchInfoAction.do?method=process'
LOGIN_URL = 'https://fund.hrbgjj.org.cn:8443/fund/webSearchInfoAction.do?method=process'
VC_URL = 'https://fund.hrbgjj.org.cn:8443/fund/webSearchInfoAction.do?method=process&dispatch=genetateValidatecode'



class Task(AbsFetchTask):
    task_info = dict(
        city_name="哈尔滨",
        help="""<li>公积金初始查询密码为111111。为了您的信息安全，请及时到公积金中心查询机上更改密码。</li>
        <li>可向公司人事或者经办人索取公积金账号；凭借身份证去当地网点查询。</li>
        """,
        developers=[{'name':'卜圆圆','email':'byy@qinqinxiaobao.com'}]
    )

    def _get_common_headers(self):
        return {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3141.7 Safari/537.36'
        }

    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_name, self._unit_login)

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '身份证号' in params, '缺少身份证号'
        assert '个人账号' in params, '缺少个人账号'
        assert '密码' in params,'缺少密码'
        assert 'vc' in params, '缺少验证码'
        身份证号 = params['身份证号']
        个人账号 = params['密码']

        if len(身份证号) == 0:
            raise InvalidParamsError('身份证号为空，请输入身份证号')
        elif len(身份证号) < 15:
            raise InvalidParamsError('身份证号不正确，请重新输入')

        if len(个人账号) == 0:
            raise InvalidParamsError('个人账号为空，请输入个人账号！')
        elif len(个人账号) < 6:
            raise InvalidParamsError('个人账号不正确，请重新输入！')
        # other check
    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '身份证号' not in params:
                params['身份证号'] = meta.get('身份证号')
            if '个人账号' not in params:
                params['个人账号'] = meta.get('个人账号')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '个人账号' and '个人账号' in meta:
                continue
            elif pr['key'] == '身份证号' and '身份证号' in meta:
                continue
            elif pr['key'] == '密码' and '密码' in meta:
                continue
            elif pr['key']=='other':
                continue
            res.append(pr)
        return res
    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params['身份证号']
                account_num = params['个人账号']
                password=params['密码']
                vc = params['vc']

                resp = self.s.post(LOGIN_URL, data=dict(
                    dispatch= 'fund_search',
                    return_message='',
                    id_card=id_num,
                    id_account=account_num,
                    searchpwd=password,
                    validcode=vc
                ),verify=False)
                soup = BeautifulSoup(resp.content, 'html.parser')
                return_message = soup.find('input', {'name': 'return_message'})["value"]

                if return_message:
                    raise InvalidParamsError(return_message)
                else:
                    print("登录成功！")
                    self.html = str(resp.content, 'gbk')

                self.result_key= id_num
                self.result_meta['身份证号'] =id_num
                self.result_meta['个人账号'] = account_num
                self.result_meta['密码'] = password

                self.result_identity['task_name']='哈尔滨'
                self.result_identity['target_id'] = id_num

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        vc = self._new_vc()
        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input'),
            dict(key='个人账号', name='个人账号', cls='input'),
            dict(key='密码',name='密码',cls='input:password'),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch_name(self):
        try:
            data = self.result_data
            data['baseInfo']={
                '城市名称': '哈尔滨',
                '城市编号': '230100',
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '证件类型':'身份证'
            }
            resp = self.html
            soup = BeautifulSoup(resp, 'html.parser')
            table_text=soup.findAll('table')
            rows = table_text[2].find_all('tr')
            for row in rows:
                cell = [i.text for i in row.find_all('td')]
                if len(cell)==4:
                    data['baseInfo'][cell[0].replace('\n','').replace('账户余额','当前余额').replace('本年支取总额','当年提取金额').replace('本年缴存总额','当年缴存金额').replace('月汇缴金额','月应缴额').replace('个人缴存基数','缴存基数').replace('    ','').replace('身份证号','证件号')] = re.sub('[\n              \t  \n\r]','',cell[1].replace('\xa0',''))
                    data['baseInfo'][cell[2].replace('\n','').replace('状 态','帐户状态').replace('最后汇缴年月','最后业务日期').replace('\r                \xa0','').replace('    ','')] = re.sub('[\n              \t  \n\r]','',cell[3].replace('\xa0','').replace('-',''))

            self.result_identity['target_name'] = data['baseInfo']['姓名']
            self.result_identity['status'] = ''

            data['companyList']=[]
            diclist= {
                '单位名称':data['baseInfo']['单位名称'],
                '当前余额': data['baseInfo']['当前余额'],
                '帐户状态': data['baseInfo']['帐户状态'],
                '当年缴存金额': data['baseInfo']['当年缴存金额'],
                '当年提取金额': data['baseInfo']['当年提取金额'],
                '最后业务日期': data['baseInfo']['最后业务日期']
            }
            data['companyList'].append(diclist)
            return
        except (AssertionError, InvalidParamsError) as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        vc_url = VC_URL #+ str(int(time.time() * 1000))
        resp = self.s.get(vc_url,verify=False)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])


if __name__ == '__main__':
    from services.client import TaskTestClient
    meta = {'身份证号': '230223197310180837','个人账号':'801016453429', '密码': '111111'}

    client = TaskTestClient(Task(prepare_data = dict(meta=meta)))
    client.run()
