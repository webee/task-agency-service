#佛山社保查询：
#Code：440600
#地址：http://www.fssi.gov.cn/
#账号：440681198412040228
#密码：198412
import datetime
from PIL import Image
import io
import requests
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError

MAIN_URL = 'http://61.142.213.86/grwssb/action/MainAction'
LOGIN_URL = 'http://61.142.213.86/grwssb/action/GRLoginAction'
VCIMAGE_URL='http://61.142.213.86/grwssb/imagecheck.jsp'
VC_URL='http://61.142.213.86/grwssb/checkimage.jsp'

class Task(AbsTaskUnitSessionTask):
    # noinspection PyAttributeOutsideInit
    def _prepare(self):
        state: dict = self.state
        self.s = requests.Session()
        cookies = state.get('cookies')
        if cookies:
            self.s.cookies = cookies
        self.s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36'
        })

        # result
        result: dict = self.result
        result.setdefault('meta', {})
        result.setdefault('data', {})

    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_name, self._unit_login)

    def _update_session_data(self):
        super()._update_session_data()
        self.state['cookies'] = self.s.cookies
    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()
    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert 'id_num' in params, '缺少个人编号'
        assert 'password' in params, '缺少密码'
        # other check

    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params['id_num']
                pwd = params['password']

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

                self.result['key'] = '%s.%s' % ('real', id_num)
                self.result['meta'] = {
                    'task': 'real',
                    'id_num': id_num
                }
                return
            except Exception as e:
                err_msg = str(e)


        raise AskForParamsError([
            dict(key='id_num', name='个人编号', cls='input'),
            dict(key='password', name='密码',cls='input' ),
        ], err_msg)

    def _unit_fetch_name(self):
        try:
            data = self.result['data']
            #基本信息
            baseinfo_URL=MAIN_URL+'?ActionType=grcx_grjbzlcx&flag=true'
            resp = self.s.get(baseinfo_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            table_text = soup.select('.dataTable')[1]
            rows = table_text.find_all('tr')
            data['baseinfo'] = {}
            for row in rows:
                cell = [i.text for i in row.find_all('td')]
                data['baseinfo'].setdefault(cell[0], cell[1])
                if(len(cell)>3):
                    data['baseinfo'].setdefault(cell[2], cell[3])#.replace('\xa0', '')
                if len(cell)>5:
                    data['baseinfo'].setdefault(cell[4], cell[5])
            #五险arrtype={'01':'基本养老保险','02':'失业保险','03':'基本医疗保险','04':'工伤保险','05':'生育保险'}
            arrtype = {'grcx_ylbxjfcx': 'old_age', 'grcx_syebxjfcx': 'unemployment', 'grcx_yilbxjfcx': 'medical_care', 'grcx_gsbxjfcx': 'injuries', 'grcx_syubxjfcx': 'maternity'}
            for k, v in arrtype.items():
                newurl='?menuid='+ k +'&ActionType=grcx_ylbxjfcx&flag=true'
                arrtype_URL=MAIN_URL+newurl
                data[v] = {}
                data[v]['data'] = {}
                yearkeys = ''
                resp = self.s.get(arrtype_URL)
                soup = BeautifulSoup(resp.content, 'html.parser')
                tablelist=soup.select('.list_table')[0]
                titkeys = ''
                for td in tablelist.find('thead').findAll('td'):
                    if len(titkeys)<1:
                        titkeys =td.getText()
                    else:
                        titkeys=titkeys+','+td.getText()
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
                        if i == 7:
                            monthcount=int(td.getText())
                            values=monthcount/monthcount
                        if i==8:
                            values=float(td.getText())/monthcount
                        if i==9:
                            values=float(td.getText())/monthcount
                        if i==10:
                            values=float(td.getText())/monthcount
                        if i == 11:
                            values = float(td.getText()) / monthcount
                        dic.setdefault(titkeys.split(',')[i], values)
                        if i == 11:
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
                                    else:
                                        print(key)
                                dic['缴费起止时间']=monthkeys
                                dic1=dic.copy()
                                arr.append(dic1)
                                if len(months) > 0:
                                    data[v]['data'][yearkeys][months] = arr
                                else:
                                    data[v]['data'][yearkeys].setdefault(monthkeys[-2:], arr)
                        i = i + 1

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)


    def _new_vc(self):
        vc_url = VC_URL #+ str(int(time.time() * 1000))
        resp = self.s.get(vc_url)
        return dict(content=resp.content, content_type='text/html;charset=GB2312')

if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()
