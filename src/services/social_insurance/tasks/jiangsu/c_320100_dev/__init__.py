import datetime
from bs4 import BeautifulSoup
from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask

LOGIN_URL='http://wsbs.njhrss.gov.cn/NJLD/LoginAction'#http://wsbs.njhrss.gov.cn/NJLD/
VC_URL='http://wsbs.njhrss.gov.cn/NJLD/Images'
INFO_URL='http://wsbs.njhrss.gov.cn/NJLD/company/system/lesmainload.jsp'
MX_URL='http://wsbs.njhrss.gov.cn/NJLD/ZjGrJf?act=perform'
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
        self.s.get("http://wsbs.njhrss.gov.cn/NJLD/")
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
                resp = self.s.post(LOGIN_URLb, data=datas,headers=header)
                soup = BeautifulSoup(resp.content, 'html.parser')
                if 'alert' in soup.text:
                    return_message = soup.text.split('(')[1].split('\\')[0]
                    raise InvalidParamsError(return_message)
                else:
                    print("登录成功！")
                self.result_key = id_num
                # 保存到meta
                self.result_meta['用户名'] = id_num
                self.result_meta['密码'] = password
                self.result_identity['task_name'] = '南京'
                return
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
            data = self.result_data
            # 基本信息
            resp = self.s.get(INFO_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            alltable = soup.findAll('td')
            data['baseInfo'] = {
                "更新时间": datetime.datetime.now().strftime('%Y-%m-%d'),
                '城市名称': '南京',
                '城市编号': '320100',
                '姓名':alltable[3].text,
                '劳动保障卡号':alltable[1].text,
                '身份证号': alltable[5].text,
                '工作单位': alltable[7].text,
                '人员状态': alltable[9].text
            }
            self.result_identity['target_name'] = data['baseInfo']['姓名']
            self.result_identity['target_id'] = data['baseInfo']['身份证号']
            self.result_identity['status'] =''
            # if '参保缴费' in infodic.values():
            #     self.result_identity['status'] = '正常'
            # else:
            #     self.result_identity['status'] = '停缴'

            # 五险明细
            # 五险arrtype={'11':'基本养老保险','21':'失业保险','31':'基本医疗保险','41':'工伤保险','51':'生育保险'}
            arrtype = {'1': 'old_age', '4': 'unemployment', '5': 'medical_care', '2': 'injuries', '3': 'maternity'}
            yllen = 0
            ylsum = 0.00
            yilsum = 0.00
            for k, v in arrtype.items():  # 类型
                data[v] = {}
                data[v]['data'] = {}
                resp = self.s.post(MX_URL,data=dict(xz=k,hide='',Submit='查询'))
                soup = BeautifulSoup(resp.content, 'html.parser')
                tablelist = soup.select('.table1')[1]
                arrtitle = []
                cell = []
                for row in tablelist.find_all('tr'):
                    if len(row.attrs) > 0:
                        arrtitle = [ii.text for ii in row.find_all('td')]
                    else:
                        arrs = []
                        cell = [ii.text for ii in row.find_all('td')]
                        if len(cell[0]) > 0:
                            dic = {
                                '缴费时间': cell[0],
                                '险种类型': cell[1],
                                '缴费基数': cell[2],
                                '个人缴费': cell[3],
                                '单位编号': cell[4],
                                '缴费单位': cell[5],
                                '缴费类型': cell[6],
                                '公司缴费': ''
                            }
                            yearkeys = cell[0]
                            years = yearkeys[:4]
                            months = yearkeys[-2:]
                            if v == 'old_age':
                                ylsum = ylsum + float(cell[3])
                            if v == 'medical_care':
                                yilsum = yilsum + float(cell[3])
                            if years not in data[v]['data'].keys():
                                data[v]['data'][years] = {}
                            if months not in data[v]['data'][years].keys():
                                if v == 'old_age':
                                    yllen = yllen + 1
                                data[v]['data'][years][months] = {}
                            else:
                                arrs = data[v]['data'][years][months]
                            arrs.append(dic)
                            data[v]['data'][years][months] = arrs

            data['baseInfo']['最近缴费时间'] = max(data['old_age']['data']) + max(
                data['old_age']['data'][max(data['old_age']['data'])])
            data['baseInfo']['缴费时长'] = yllen
            data['baseInfo']['个人养老累计缴费'] = ylsum
            data['baseInfo']['个人医疗累计缴费'] = yilsum

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