#佛山社保查询：
#Code：440600
#地址：http://www.fssi.gov.cn/
#账号：440681198412040228
#密码：198412
import datetime,time
from PIL import Image
import io
import requests
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask

MAIN_URL = 'http://61.142.213.86/grwssb/action/MainAction'
LOGIN_URL = 'http://61.142.213.86/grwssb/action/GRLoginAction'
VCIMAGE_URL='http://61.142.213.86/grwssb/imagecheck.jsp'
VC_URL='http://61.142.213.86/grwssb/checkimage.jsp'

class Task(AbsFetchTask):
    task_info = dict(
        city_name="佛山",
        help="""<li>可向公司人事或者经办人索取公积金账号。</li>
            <li>如需设置密码，可登录公积金官网后进行设置。</li>
            """
    )
    def _get_common_headers(self):
        return { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36'
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
        assert '密码' in params, '缺少密码'
        # other check
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
            elif pr['key']=='other':
                continue
            res.append(pr)
        return res
    def _unit_login(self, params:dict):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params['身份证号']
                pwd = params['密码']

                resp = self.s.post(LOGIN_URL, data=dict(
                    UserID=id_num,
                    Password=pwd
                ))
                soup = BeautifulSoup(resp.content, 'html.parser')
                errormsg = soup.select('table')[1].text.replace('\n','')
                if errormsg:
                    if errormsg=='确 定退出系统':
                        #vc = self._new_vc()
                        vc_url=self.s.get(VC_URL)
                        Image.open(io.BytesIO(vc_url.content)).show()
                        vcts=input('验证码：')
                        data=dict(UserID=soup.find('input', {'name': 'UserID'})["value"],
                            GRBH=soup.find('input', {'name': 'GRBH'})["value"],
                            PASS=soup.find('input', {'name': 'PASS'})["value"],
                            CHECK= soup.find('input', {'name': 'CHECK'})["value"],
                            rtn=soup.find('input', {'name': 'rtn'})["value"],
                            imagecheck=vcts
                            )
                        resp = self.s.post(VCIMAGE_URL,data)
                        soup = BeautifulSoup(resp.content, 'html.parser')
                        vcmsg=soup.select('table')[0].find('p').text
                        if vcmsg:
                            raise Exception(vcmsg)
                        else:
                            data = dict(UserID=soup.find('input', {'name': 'UserID'})["value"],
                                        GRBH=soup.find('input', {'name': 'GRBH'})["value"],
                                        PASS=soup.find('input', {'name': 'PASS'})["value"],
                                        CHECK=soup.find('input', {'name': 'CHECK'})["value"],
                                        rtn=soup.find('input', {'name': 'rtn'})["value"]
                                        )
                            resp = self.s.post(MAIN_URL, data)
                            soup = BeautifulSoup(resp.content, 'html.parser')
                            self.html=soup

                    else:
                        raise Exception(errormsg)
                else:
                    print()

                self.result_key =id_num
                self.result_meta['身份证号'] = id_num
                self.result_meta['密码'] = pwd
                self.result_identity['task_name']='佛山'
                self.result_identity['target_id'] = id_num

                return
            except Exception as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input',value=params.get('身份证号', '')),
            dict(key='密码', name='密码',cls='input:password' , value=params.get('密码', ''))
        ], err_msg)

    def _unit_fetch_name(self):
        try:
            data = self.result_data
            #基本信息
            baseinfo_URL=MAIN_URL+'?ActionType=grcx_grjbzlcx&flag=true'
            resp = self.s.get(baseinfo_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            table_text = soup.select('.dataTable')[1]
            rows = table_text.find_all('tr')
            data['baseinfo'] = {
                '城市名称': '佛山',
                '城市编号': '440600',
                '更新时间': time.strftime("%Y-%m-%d", time.localtime())
            }
            for row in rows:
                cell = [i.text for i in row.find_all('td')]
                data['baseinfo'].setdefault(cell[0], cell[1])
                if cell[0]=='姓名':
                    self.result_identity['target_name']=cell[1]
                if cell[0]=='养老 实际缴费月数':
                    data['baseinfo'].setdefault('缴费时长', cell[1])
                if(len(cell)>3):
                    if cell[2]=='个人社保号':
                        data['baseinfo'].setdefault('社保编号', cell[3])
                    else:
                        data['baseinfo'].setdefault(cell[2], cell[3])#.replace('\xa0', '')
                if len(cell)>5:
                    data['baseinfo'].setdefault(cell[4], cell[5])
            self.result_identity['status'] = ''


            arrtime=[]
            grylsum=0.00
            gryilsum=0.00
            #五险arrtype={'01':'基本养老保险','02':'失业保险','03':'基本医疗保险','04':'工伤保险','05':'生育保险'}
            arrtype = {'grcx_ylbxjfcx': 'old_age', 'grcx_syebxjfcx': 'unemployment', 'grcx_yilbxjfcx': 'medical_care', 'grcx_gsbxjfcx': 'injuries', 'grcx_syubxjfcx': 'maternity'}
            for k, v in arrtype.items():
                newurl='?menuid='+ k +'&ActionType='+ k +'&flag=true'
                arrtype_URL=MAIN_URL+newurl
                data[v] = {}
                data[v]['data'] = {}
                yearkeys = ''
                #resp = self.s.get(arrtype_URL)
                resp=self.s.post(MAIN_URL,data=dict(menuid=k,ActionType=k,flag='true'))
                soup = BeautifulSoup(resp.content, 'html.parser')
                tablelist=soup.select('.list_table')[0]
                titkeys =[]
                for td in tablelist.find('thead').findAll('td'):
                    titlename=td.getText()
                    if titlename=='缴费起止时间':
                        titlename='缴费时间'
                    if titlename=='个人缴费(每月)(元)':
                        titlename='个人缴费'
                    if titlename=='单位缴费(每月)(元)':
                        titlename='公司缴费'
                    if titlename == '单位名称':
                        titlename = '缴费单位'
                    titkeys.append(titlename)
                for tr in tablelist.find('tbody').findAll('tr'):
                    dic = {}
                    i = 0
                    monthkeys = ''
                    monthcount=0
                    for td in tr.findAll('td'):
                        values=td.getText()
                        if i == 0:
                            monthkeyslist = td.getText().split('-')
                            if len(monthkeyslist) > 1:
                                values=monthkeyslist[0]
                                arrtime.append(monthkeyslist[0])
                        if i == 7:
                            monthcount=int(td.getText())
                            values=monthcount/monthcount
                        if i==8:
                            values=float(td.getText())/monthcount
                            if v=='old_age':
                                grylsum=grylsum+float(td.getText())
                            if v == 'medical_care':
                                gryilsum = gryilsum + float(td.getText())
                        if i==9:
                            values=float(td.getText())/monthcount
                        if i==10:
                            values=float(td.getText())/monthcount
                        if i == 11:
                            values = float(td.getText()) / monthcount
                        dic.setdefault(titkeys[i], values)
                        if i == 11 or len(titkeys)==i+1:
                            for y in range(-1,monthcount-1):
                                dic1={}
                                arr = []
                                months = ''
                                statatime=monthkeyslist[0]
                                endtime=monthkeyslist[1]
                                nowtime = datetime.date(int(statatime[:5]) + (int(statatime[-2:]) + y) // 12,
                                                        (int(statatime[-2:]) + y) % 12 + 1, 1).strftime('%Y-%m-%d')
                                strtimemonth = nowtime[:7].replace('-', '')
                                monthkeys=strtimemonth
                                if yearkeys != monthkeys[:4] or yearkeys == '':
                                    yearkeys = monthkeys[:4]
                                    data[v]['data'][yearkeys] = {}
                                for (key, value) in data[v]['data'][yearkeys].items():
                                    if key == monthkeys[-2:]:
                                        months = monthkeys[-2:]
                                        arr = value

                                dic['缴费起止时间']=monthkeys
                                dic1=dic.copy()
                                dic1.setdefault('缴费类型','正常应缴')
                                arr.append(dic1)
                                if months:
                                    data[v]['data'][yearkeys][months] = arr
                                else:
                                    data[v]['data'][yearkeys].setdefault(monthkeys[-2:], arr)
                        i = i + 1
                if v=='old_age':
                    data['baseinfo'].setdefault('个人养老累计缴费', grylsum)
                if v == 'medical_care':
                    data['baseinfo'].setdefault('个人医疗累计缴费', gryilsum)

            data['baseinfo'].setdefault('最近缴费时间', max(arrtime))
            data['baseinfo'].setdefault('开始缴费时间',min(arrtime))

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)


    def _new_vc(self):
        vc_url = VC_URL #+ str(int(time.time() * 1000))
        resp = self.s.get(vc_url)
        return dict(content=resp.content, content_type='text/html;charset=GB2312')

if __name__ == '__main__':
    from services.client import TaskTestClient
    #meta = {'身份证号': '440681198412040228', '密码': '198412'}prepare_data=dict(meta=meta)
    client = TaskTestClient(Task())
    client.run()
