import time,datetime
from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask
from bs4 import BeautifulSoup

#LOGIN_URL='http://www.fzshbx.org/sb_login.jsp'
LOGIN_URL='http://www.fzshbx.org/sb/user/userLogin.do'
VC_URL='http://www.fzshbx.org/img.jsp'
INFOR_URL='http://www.fzshbx.org/xxcx/grjbxxcx.do'
MX_URL='http://www.fzshbx.org/xxcx/grjfmxcx.do'
class Task(AbsFetchTask):
    task_info = dict(
        city_name="福州",

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
        assert '身份证' in params, '缺少身份证'
        assert '密码' in params, '缺少密码'

        # other check
        身份证 = params['身份证']
        密码 = params['密码']
        if len(密码) < 4:
            raise InvalidParamsError('密码错误')
        if len(身份证) < 15:
            raise InvalidParamsError('身份证错误')

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '身份证' not in params:
                params['身份证'] = meta.get('身份证')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params
    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '身份证' and '身份证' in meta:
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
                id_num = params['身份证']
                password = params['密码']
                vc = params['vc']
                data = {
                    'sbUser.username': id_num,
                    'sbUser.password': password,
                    'sbUser.yzm': vc
                }
                resp = self.s.post(LOGIN_URL, data=data, timeout=20)
                soup = BeautifulSoup(resp.content, 'html.parser')
                successinfo = soup.text.split(';')
                if successinfo[0].find('alert')==0:
                    successinfo = successinfo[0].replace('alert(','').replace(')','')
                elif len(soup.findAll('font'))==1:
                    successinfo =soup.findAll('font')[0].text
                else:
                    successinfo=''
                if successinfo:
                    return_message = successinfo
                    raise InvalidParamsError(return_message)
                else:
                    print("登录成功！")

                self.result_key = id_num
                # 保存到meta
                self.result_meta['身份证号'] = id_num
                self.result_meta['密码'] = params.get('密码')
                self.result_identity['task_name'] = '福州'
                self.result_identity['target_id'] = id_num
                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='身份证', name='身份证', cls='input', placeholder='身份证', value=params.get('身份证', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            # 基本信息
            data = self.result_data
            resp = self.s.get(INFOR_URL)
            soup = BeautifulSoup(resp.content.decode('gbk'), 'html.parser')
            tables = soup.findAll('table')
            if not tables:
                return
            data['baseInfo'] = {
                '城市名称': '福州',
                '城市编号': '350100',
                '更新时间': time.strftime("%Y-%m-%d", time.localtime())
            }
            rows = tables[0].find_all('tr')
            for row in rows:
                cell = [i.text.replace('保险','').replace('基本','').replace(' ','') for i in row.find_all('td')]
                data['baseInfo'].setdefault(cell[0].replace(' ', '').replace('公民身份号码', '身份证号'), cell[1].replace(' ', ''))
                if (len(cell) > 3):
                    data['baseInfo'].setdefault(cell[2].replace(' ', ''),cell[3].replace(' ', ''))
            self.result_identity['target_name'] =data['baseInfo']['姓名']
            self.result_identity['status'] = ''
            #明细
            datas={
                'ac10a.starttime':'',
                    'ac10a.endtime':'',
            'Submit22': '(unable to decode value)',
            'temp':'',
            'page':'1',
            'sppagetotal': '1',
            'length': '10000'
            }
            resp = self.s.post(MX_URL,data=datas)
            soup = BeautifulSoup(resp.content, 'html.parser')
            data['old_age'] = {}
            data['old_age']['data'] = {}
            tables = soup.findAll('tbody')
            ylljjf=0.00
            for row in tables:
                cell = [i.text.replace('\t','').replace('\n','').replace('\r','') for i in row.find_all('td')]
                if int(cell[5])>0:
                    for i in range(-1,int(cell[5])-1):
                        arrs = []
                        dic={
                            '缴费时间':cell[1],
                            '缴费类型':'',
                            '缴费基数': int(cell[6])/int(cell[5]),
                            '公司缴费': float(cell[9])/float(cell[5]),
                            '个人缴费': float(cell[7])/float(cell[5]),
                            '缴费单位': cell[11]
                        }
                        ylljjf=ylljjf+float(cell[7])/float(cell[5])
                        statatime = cell[2]
                        nowtime = datetime.date(int(statatime[:4]) + (int(statatime[-2:]) + i) // 12,
                                                (int(statatime[-2:]) + i) % 12 + 1, 1).strftime('%Y-%m-%d')
                        yearkeys = nowtime[:7].replace('-', '')
                        years = yearkeys[:4]
                        months = yearkeys[-2:]
                        if years not in data['old_age']['data'].keys():
                            data['old_age']['data'][years] = {}
                        if months not in data['old_age']['data'][years].keys():
                            data['old_age']['data'][years][months] = {}
                        else:
                            arrs = data['old_age']['data'][years][months]
                        arrs.append(dic)
                        data['old_age']['data'][years][months] = arrs
            data['baseInfo']['最近缴费时间'] = max(data['old_age']['data']) + max(
                data['old_age']['data'][max(data['old_age']['data'])])
            data['baseInfo']['开始缴费时间'] = min(data['old_age']['data']) + min(
                data['old_age']['data'][min(data['old_age']['data'])])
            data['baseInfo']['缴费时长'] = int(soup.findAll('table')[2].contents[1].findAll('td')[0].text.split('：')[1].replace('\r\n','').replace('\t',''))
            data['baseInfo']['个人养老累计缴费'] = "%.2f" % ylljjf
            data['baseInfo']['个人医疗累计缴费'] = '0.00'
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        resp = self.s.get(VC_URL,timeout=25)
        return dict(content=resp.content,content_type='image/jpeg;charset=GBK')
if __name__ == '__main__':
    from services.client import TaskTestClient

    meta = {'身份证': '370725198710245527', '密码': 'wsm20130420'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()


#身份证：511323198301034510   密码：ygt198313   身份证：350303198406070044   密码：341887  身份证：350123198209016115  密码：15959008652  身份证：350721199806220020 密码：622528
#身份证：352203198710285425   密码：wxb123ggg