import time
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask
from bs4 import BeautifulSoup

LOGIN_URL='https://grcx.dgsi.gov.cn/action/LoginAction'#https://grcx.dgsi.gov.cn/
VC_URL='https://grcx.dgsi.gov.cn/pages/checkimage.JSP'
INFOR_URL='https://grcx.dgsi.gov.cn/action/MainAction?'

class Task(AbsFetchTask):
    task_info = dict(
        city_name="东莞",

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
        assert '身份证号' in params, '缺少身份证号'
        assert '密码' in params, '缺少密码'
        # other check
        身份证号 = params['身份证号']
        密码 = params['密码']
        if len(密码) < 4:
            raise InvalidParamsError('密码错误')
        if len(身份证号) < 15:
            raise InvalidParamsError('身份证号错误')

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
            elif pr['key'] == 'other':
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
                vc = params['vc']
                data = {
                    'ywType': 'login',
                    'SFZHM': id_num,
                    'PASSWORD': password,
                    'imagecheck': vc
                }
                resp = self.s.post(LOGIN_URL, data=data, timeout=20)
                soup = BeautifulSoup(resp.content, 'html.parser')
                successinfo = soup.findAll('td')
                if len(successinfo) > 0:
                    successinfo = successinfo[4].text
                else:
                    successinfo = ''
                if successinfo:
                    return_message = successinfo
                    raise InvalidParamsError(return_message)
                else:
                    print("登录成功！")

                self.result_key = id_num
                # 保存到meta
                self.result_meta['身份证号'] = id_num
                self.result_meta['密码'] = params.get('密码')
                self.result_identity['task_name'] = '东莞'
                self.result_identity['target_id'] = id_num
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
            # 基本信息
            resp = self.s.get(INFOR_URL+'menuid=105702&ActionType=grzlxg')
            soup = BeautifulSoup(resp.content, 'html.parser')
            tables = soup.findAll('td')
            data = self.result_data
            data['baseInfo'] = {
                '城市名称': '东莞',
                '城市编号': '441900',
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '身份证号': self.result_meta['身份证号'],
                '姓名': tables[1].text,
                '性别': tables[5].text,
                '出生日期': tables[7].text,
                '参加工作日期':tables[9].text,
                '手机号码': soup.findAll('input')[2].attrs['value']
            }
            #参保状态
            resp = self.s.get(INFOR_URL+'menuid=106203&ActionType=q_grcbxxcx')
            soup = BeautifulSoup(resp.content, 'html.parser')
            tbody=soup.findAll('tbody')[1]
            rows = tbody.find_all('tr')
            fivdic={}
            ljmonth=[]
            fristtime=[]
            for row in rows:
                cell = [i.text.replace('保险','').replace('基本','') for i in row.find_all('td')]
                fivdic.setdefault(cell[1],cell[2])
                fristtime.append(cell[3])
                ljmonth.append(cell[4])
            data['baseInfo'].setdefault('五险状态',fivdic)
            data['baseInfo'].setdefault('缴费时长', max(ljmonth))
            data['baseInfo'].setdefault('开始缴费时间', min(fristtime))

            #缴费明细
            resp = self.s.get(INFOR_URL + 'menuid=206206&ActionType=q_grcbxzjfmxcx_tj')
            soup = BeautifulSoup(resp.content, 'html.parser')
            tbody = soup.findAll('tbody')[1]

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        resp=self.s.get('https://grcx.dgsi.gov.cn/',verify=False)
        resp = self.s.get(VC_URL,verify=False,timeout=25)
        return dict(content=resp.content)
if __name__ == '__main__':
    from services.client import TaskTestClient

    meta = {'身份证号': '513901198603293354', '密码': '20171226'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()

#身份证号：513901198603293354   密码：20171226  身份证号：140321198209121213  密码：20160414
