import time,random,datetime
import io
from PIL import Image
from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask
from bs4 import BeautifulSoup

LOGIN_URL='http://www.fzzfgjj.com:8011/Admin_Login.aspx'#http://www.fzzfgjj.com:8011/
VC_URL='http://www.fzzfgjj.com:8011/Validate.aspx'
INFO_URL='http://www.fzzfgjj.com:8011/grjbxx.aspx'
MXLIST_URL='http://www.fzzfgjj.com:8011/grzhxx_list.aspx'
MX_URL='http://www.fzzfgjj.com:8011/'
class Task(AbsFetchTask):
    task_info = dict(
        city_name="福州",

        developers=[{'name':'卜圆圆','email':'byy@qinqinxiaobao.com'}]
    )

    def _get_common_headers(self):
        return {'User-Agent':'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3100.0 Mobile Safari/537.36'}

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
            raise InvalidParamsError('登陆名或密码错误')
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
                    '__EVENTTARGET': self.g.soup.select('#__EVENTTARGET')[0].attrs['value'],
                    '__EVENTARGUMENT': self.g.soup.select('#__EVENTARGUMENT')[0].attrs['value'],
                    '__LASTFOCUS': self.g.soup.select('#__LASTFOCUS')[0].attrs['value'],
                    '__VIEWSTATE': self.g.soup.select('#__VIEWSTATE')[0].attrs['value'],
                    '__EVENTVALIDATION': self.g.soup.select('#__EVENTVALIDATION')[0].attrs['value'],
                    'ddlUserType': '03',
                    'txtName': id_num,
                    'txtPass': password,
                    'txtCheckCode': vc,
                    'btnLogin': '登录'
                }
                resp = self.s.post(LOGIN_URL, data=data, timeout=20,
                                   headers={'Cache-Control': 'max-age=0', 'Upgrade-Insecure-Requests': '1',
                                            'Accept-Language': 'zh-CN,zh;q=0.8',
                                            'Host': 'www.fzzfgjj.com:8011',
                                            'Origin': 'http://www.fzzfgjj.com:8011',
                                            'Referer': 'http://www.fzzfgjj.com:8011/Admin_Login.aspx',
                                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'})
                soup = BeautifulSoup(resp.content, 'html.parser')
                if len(soup.findAll('script')) >3:
                    successinfo = soup.findAll('script')[3].text.split('：')[1].split('！')[0]
                elif 'User_UpdatePW.aspx' in resp.url:
                    successinfo = '第一次登陆，请去官网修改新密码！'
                elif resp.url == 'http://www.fzzfgjj.com:8011/User_Main.aspx':
                    successinfo = ''
                if successinfo:
                    return_message = successinfo
                    raise InvalidParamsError(return_message)
                else:
                    print("登录成功！")
                self.result_key = id_num
                # 保存到meta
                self.result_meta['身份证号'] = id_num
                self.result_meta['密码'] = password
                self.result_identity['task_name'] = '福州'
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
            data = self.result_data
            resp = self.s.get(INFO_URL,timeout=20)
            soup = BeautifulSoup(resp.content, 'html.parser')

            if 'value' in soup.select('#ctl00_ContentPlace_txtYddh')[0].attrs.keys():
                Yddh=soup.select('#ctl00_ContentPlace_txtYddh')[0].attrs['value']
            else:
                Yddh =''
            if 'value' in soup.select('#ctl00_ContentPlace_txtJtdh')[0].attrs.keys():
                Jtdh=soup.select('#ctl00_ContentPlace_txtJtdh')[0].attrs['value']
            else:
                Jtdh =''
            if 'value' in soup.select('#ctl00_ContentPlace_txtDwdh')[0].attrs.keys():
                Dwdh=soup.select('#ctl00_ContentPlace_txtDwdh')[0].attrs['value']
            else:
                Dwdh =''
            if 'value' in soup.select('#ctl00_ContentPlace_txtJtdz')[0].attrs.keys():
                Jtdz=soup.select('#ctl00_ContentPlace_txtJtdz')[0].attrs['value']
            else:
                Jtdz =''
            if 'value' in soup.select('#ctl00_ContentPlace_txtYzbm')[0].attrs.keys():
                Yzbm=soup.select('#ctl00_ContentPlace_txtYzbm')[0].attrs['value']
            else:
                Yzbm =''
            data['baseInfo'] = {
                '城市名称': '福州',
                '城市编号': '350100',
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '姓名':soup.select('#ctl00_ContentPlace_txtXm')[0].attrs['value'],
                '证件类型': '身份证',
                '证件号': soup.select('#ctl00_ContentPlace_txtGrZjh')[0].attrs['value'],
                '移动电话':Yddh,
                '家庭电话': Jtdh,
                '单位电话': Dwdh,
                '家庭地址': Jtdz,
                '邮政编码': Yzbm,
                '最近汇款日期': soup.select('#ctl00_ContentPlace_txtSjgxsj')[0].attrs['value']
            }
            resp = self.s.get(MXLIST_URL, timeout=20)
            soup = BeautifulSoup(resp.content, 'html.parser')
            tables=soup.select('#ctl00_ContentPlace_ShowTxt')
            tables = tables[0].find('table')
            if not tables:
                return
            data['detail'] = {}
            data['detail']['data'] = {}
            rows = tables.find_all('tr')
            years = ''
            months = ''
            hjcs = 0
            hjje = ''
            hjrq = ''
            enterarr = []
            for row in rows:
                ahrefs=row.find_all('a')
                if len(ahrefs)>0:
                    ahref = ahrefs[4].attrs['href']
                    khtime = ahrefs[8].text
                    etime = time.strftime("%Y-%m-%d", time.localtime())
                    resp = self.s.get(MX_URL + ahref, timeout=20)
                    soup = BeautifulSoup(resp.content, 'html.parser')
                    datas = {
                        '__EVENTTARGET': soup.select('#__EVENTTARGET')[0].attrs['value'],
                        '__EVENTARGUMENT': soup.select('#__EVENTARGUMENT')[0].attrs['value'],
                        '__VIEWSTATE': soup.select('#__VIEWSTATE')[0].attrs['value'],
                        '__EVENTVALIDATION': soup.select('#__EVENTVALIDATION')[0].attrs['value'],
                        'ctl00$ContentPlace$ddlBYear': khtime[:4],
                        'ctl00$ContentPlace$ddlBMonth': khtime[5:7],
                        'ctl00$ContentPlace$ddlEYear': etime[:4],
                        'ctl00$ContentPlace$ddlEMonth': etime[5:7],
                        'ctl00$ContentPlace$txtmybs': 100,
                        'ctl00$ContentPlace$btncx': '查询'
                    }
                    resp = self.s.post(MX_URL + ahref, data=datas, timeout=20,
                                   headers={'Cache-Control': 'max-age=0', 'Upgrade-Insecure-Requests': '1',
                                            'Accept-Language': 'zh-CN,zh;q=0.8',
                                            'Host': 'www.fzzfgjj.com:8011',
                                            'Origin': 'http://www.fzzfgjj.com:8011',
                                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'})

                    soup = BeautifulSoup(resp.content, 'html.parser')
                    tables = soup.findAll('table')
                    rows = tables[2].find_all('tr')
                    for row in rows:
                        if len(row.attrs)==0:
                            cell = [i.text.replace(' ', '').replace('\xa0', '') for i in row.find_all('td')]
                            sr=0
                            zc=0
                            hvny=''
                            arr = []
                            if '-' in cell[6]:
                                zc=cell[6]
                            else:
                                sr=cell[6]
                            if '汇缴' in cell[4]:
                                hjcs = hjcs + 1
                                hjsjpd=cell[4].replace('汇缴','')   #截取的时间有的是四位有的是六位
                                if len(hjsjpd)==4:
                                    hvny=cell[3][:2]+hjsjpd
                                elif len(hjsjpd)==6:
                                    hvny =hjsjpd
                                lx = '汇缴'
                                if hjrq=='':
                                    hjrq=hvny
                                if int(hvny)>int(hjrq):
                                    hjrq = hvny
                                    hjje=sr
                            else:
                                lx =cell[4]
                            dic = {
                                '时间': cell[3].replace('/', '-'),
                                '单位名称': '',
                                '支出': zc,
                                '收入':sr,
                                '汇缴年月': hvny,
                                '余额': '',
                                '类型': lx,
                                '个人账号': cell[2]
                            }
                            times = cell[3][:7].replace('/', '')
                            if years != times[:4]:
                                years = times[:4]
                                data['detail']['data'][years] = {}
                                if months != times[-2:]:
                                    months = times[-2:]
                            else:
                                if months != times[-2:]:
                                    months = times[-2:]
                                else:
                                    arr = data['detail']['data'][years][months]
                            arr.append(dic)
                            data['detail']['data'][years][months] = arr
                if len(ahrefs)>0:
                    ahref = ahrefs[3].attrs['href']
                    resp = self.s.get(MX_URL+ahref, timeout=20)
                    soup = BeautifulSoup(resp.content, 'html.parser')

                    enterdic = {"单位名称": '',
                                '个人公积金账号':soup.select('#ctl00_ContentPlace_txtgrgjjzh')[0].attrs['value'] if 'value' in soup.select('#ctl00_ContentPlace_txtgrgjjzh')[0].attrs.keys() else '',
                                '个人补贴账号':soup.select('#ctl00_ContentPlace_txtgrbtzh')[0].attrs['value'] if 'value' in soup.select('#ctl00_ContentPlace_txtgrbtzh')[0].attrs.keys() else '',
                                '单位公积金账号': soup.select('#ctl00_ContentPlace_txtdwgjjzh')[0].attrs['value'] if 'value' in soup.select('#ctl00_ContentPlace_txtdwgjjzh')[0].attrs.keys() else '',
                                '开户日期': soup.select('#ctl00_ContentPlace_txtkhrq')[0].attrs['value'] if 'value' in soup.select('#ctl00_ContentPlace_txtkhrq')[0].attrs.keys() else '',
                                '最后业务日期': soup.select('#ctl00_ContentPlace_txtsjgxrq')[0].attrs['value'] if 'value' in soup.select('#ctl00_ContentPlace_txtsjgxrq')[0].attrs.keys() else '',
                                '当前余额': soup.select('#ctl00_ContentPlace_txtgjjzhye')[0].attrs['value'] if 'value' in soup.select('#ctl00_ContentPlace_txtgjjzhye')[0].attrs.keys() else '',
                                '补贴账户余额': soup.select('#ctl00_ContentPlace_txtbtzhye')[0].attrs['value'] if 'value' in soup.select('#ctl00_ContentPlace_txtbtzhye')[0].attrs.keys() else '',
                                '公积金核定月工资额': soup.select('#ctl00_ContentPlace_txtgjjhdygze')[0].attrs['value'] if 'value' in soup.select('#ctl00_ContentPlace_txtgjjhdygze')[0].attrs.keys() else '',
                                '补贴核定月工资额': soup.select('#ctl00_ContentPlace_txtbthdygze')[0].attrs['value'] if 'value' in soup.select('#ctl00_ContentPlace_txtbthdygze')[0].attrs.keys() else '',
                                '公积金核定月缴交额': soup.select('#ctl00_ContentPlace_txtgjjhdyjje')[0].attrs['value'] if 'value' in soup.select('#ctl00_ContentPlace_txtgjjhdyjje')[0].attrs.keys() else '',
                                '补贴核定月缴交额': soup.select('#ctl00_ContentPlace_txtbthdyjje')[0].attrs['value'] if 'value' in soup.select('#ctl00_ContentPlace_txtbthdyjje')[0].attrs.keys() else '',
                                '联名卡卡号': soup.select('#ctl00_ContentPlace_txtlmkkh')[0].attrs['value'] if 'value' in soup.select('#ctl00_ContentPlace_txtlmkkh')[0].attrs.keys() else '',
                                '联名卡发放日期': soup.select('#ctl00_ContentPlace_txtlmkffrq')[0].attrs['value'] if 'value' in soup.select('#ctl00_ContentPlace_txtlmkffrq')[0].attrs.keys() else ''
                                }
                    gjjzhzt=soup.select('#ctl00_ContentPlace_ddlgjjzhzt')[0].findAll('option')
                    for i in range(0,len(gjjzhzt)):
                        if len(gjjzhzt[i].attrs)>1:
                            enterdic.setdefault('帐户状态',gjjzhzt[i].attrs['value'])
                    btgjjzhzt = soup.select('#ctl00_ContentPlace_ddlbtzhzt')[0].findAll('option')
                    for i in range(0, len(btgjjzhzt)):
                        if len(btgjjzhzt[i].attrs) > 1:
                            enterdic.setdefault('补贴账户状态', btgjjzhzt[i].attrs['value'])
                    enterarr.append(enterdic)
            data['companyList'] = sorted(enterarr, key=lambda x: x['开户日期'], reverse=True)
            self.result_identity['target_name'] = data['baseInfo']['姓名']
            self.result_identity['status'] = ''
            data['baseInfo']['最近汇缴日期'] = hjrq
            data['baseInfo']['最近汇缴金额'] = hjje
            data['baseInfo']['累计汇缴次数'] = hjcs
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)
    def _new_vc(self):
        resp = self.s.get(LOGIN_URL)
        soup = BeautifulSoup(resp.content, 'html.parser')
        self.g.soup=soup
        resp = self.s.get(VC_URL, timeout=25)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])


if __name__ == '__main__':
    from services.client import TaskTestClient

    meta = {'身份证号': '513029197209200490','密码': 'hxy.0922'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()

#身份证号：513029197209200490   密码：hxy.0922
