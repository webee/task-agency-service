#重庆社保  (1、运行数据报错， 调试的时候没有错误能输出结果  2、只写了城镇的基本信息与五险 。没有写居民社保基本信息与两险【养老与医疗】)
#http://www.cqhrss.gov.cn//
#身份证：500221198702153827
#个人社保编号：2033560290
#密码：社保编号后六位
import datetime
import time
import json
import requests
import base64
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.service import AskForParamsError, PreconditionNotSatisfiedError

JsonMAIN_URL = 'http://ggfw.cqhrss.gov.cn/ggfw/QueryBLH_query.do'
MAIN_URL = 'http://ggfw.cqhrss.gov.cn/ggfw/QueryBLH_main.do'
LOGIN_URL = 'http://ggfw.cqhrss.gov.cn/ggfw/LoginBLH_login.do'
VCTEXT_URL='http://ggfw.cqhrss.gov.cn/ggfw/validateCodeBLH_valid.do'
VC_URL = 'http://ggfw.cqhrss.gov.cn/ggfw/validateCodeBLH_image.do?time='


class Task(AbsTaskUnitSessionTask):
    # noinspection PyAttributeOutsideInit
    def _prepare(self):
        state: dict = self.state
        self.s = requests.Session()
        cookies = state.get('cookies')
        if cookies:
            self.s.cookies = cookies
        self.s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36',
            'X - Requested - With': 'XMLHttpRequest'})

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
        assert 'id_num' in params, '缺少身份证号'
        assert 'psw' in params, '缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check

    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params['id_num']
                psw = params['psw']
                vc = params['vc']
                resp=self.s.post(VCTEXT_URL,data=dict(yzm=vc))
                data = resp.json()
                mas=data.get('message')
                if data.get('code')=='1':
                    resp = self.s.post(LOGIN_URL, data=dict(
                        sfzh=id_num,
                        password=base64.urlsafe_b64encode(psw.encode('utf-8')),
                        validateCode=vc
                    ))
                    data = resp.json()
                    code=data.get('code')
                    errormsg = data.get('message')
                    if errormsg!='操作成功!':
                        raise Exception(errormsg)

                self.result['key'] = '%s.%s' % ('real', id_num)
                self.result['meta'] = {
                    'task': 'real',
                    'id_num': id_num,
                    #'account_num': account_num,
                    'updated': time.time()
                }
                return
            except Exception as e:
                err_msg = str(e)

        vc = self._new_vc()
        raise AskForParamsError([
            dict(key='id_num', name='身份证号', cls='input'),
            dict(key='psw', name='密码', cls='input'),
            dict(key='vc', name='验证码', cls='data:image', data=vc, query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch_name(self):
        try:
            data = self.result['data']
            # 基本信息
            NewMAIN_URL=MAIN_URL+'?code=888'  #城镇
            resp = self.s.get(NewMAIN_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            tables = soup.findAll('table')
            data['baseinfo'] = {}
            #个人基础信息
            rows = tables[0].find_all('tr')
            for row in rows:
                cell = [i.text for i in row.find_all('td')]
                if (len(cell) > 1):
                    data['baseinfo'].setdefault(cell[0], cell[1])
                if (len(cell) > 3):
                    data['baseinfo'].setdefault(cell[2], cell[3])

            data['baseinfo'].setdefault('参保单位', tables[1].findAll('td')[2].text)
            #参保情况
            arr=tables[2].findAll('tr')[1].find_all('td')
            Fristarr={}   #各险种首次参保时间
            for i in range(1,len(arr)):
                scjf=tables[2].findAll('tr')[2].find_all('td')
                x=arr[i].text+scjf[0].text
                data['baseinfo'].setdefault(x, scjf[i].text)
                Fristarr.setdefault(arr[i].text,scjf[i].text)
                zt = tables[2].findAll('tr')[3].find_all('td')
                y=arr[i].text+zt[0].text
                data['baseinfo'].setdefault(y, zt[i].text)

            # 五险明细(险种比较多)
            Fristtype={'015':'养老','043':'失业','023':'医疗','052':'工伤','062':'生育'}
            arrtype = {'015': 'old_age', '043': 'unemployment', '023': 'medical_care', '052': 'injuries',
                       '062': 'maternity'}
            for k, v in arrtype.items():
                NewMAIN_URL = MAIN_URL + '?code='+k
                resp = self.s.get(NewMAIN_URL)
                soup = BeautifulSoup(resp.content, 'html.parser')
                tables = soup.select('.tabcon')[0].findAll('th')
                data[v] = {}
                data[v]['data'] = {}
                years=datetime.datetime.now().year
                Fristyear=Fristarr[Fristtype[k]]

                data1 = {
                    "code": k,
                    "year": years}
                resp = self.s.post(JsonMAIN_URL, data=data1)
                soup = BeautifulSoup(resp.content, 'html.parser')
                jsons = soup.text
                jsonread = json.loads(jsons)
                jsonPageCount=jsonread['page']['pageCount']
                #从首次参保日期开始（基本信息有首次参保时间）
                for datayears in range(int(Fristyear[:4]),years+1):
                    yearkeys = str(datayears)
                    data[v]['data'][yearkeys] = {}
                    #分页
                    for pages in range(1,jsonPageCount+1):
                        data1 = {
                            "code": k,
                            "year": yearkeys,
                            "currentPage": pages,
                            "goPage": ''}
                        resp = self.s.post(JsonMAIN_URL, data=data1)
                        soup = BeautifulSoup(resp.content, 'html.parser')
                        jsons = soup.text
                        jsonread = json.loads(jsons)
                        #有数据的时候执行
                        if(jsonread['code'][0]=='1'):
                            jsonlist = jsonread['result']
                            for i in range(0,len(jsonlist)):
                                dic={}
                                arr1=[]
                                months = ''
                                monthkeys=''
                                for dy in range(0,len(tables)):
                                    if len(tables[dy].attrs)<2:
                                        if tables[dy].attrs['name'] in jsonlist[i].keys():
                                            dic.setdefault(tables[dy].text, jsonlist[i][tables[dy].attrs['name']])
                                        else:
                                            dic.setdefault(tables[dy].text,'')
                                    if dy==0 and v!='injuries':
                                        monthkeys=jsonlist[i][tables[dy].attrs['name']].replace('-','')
                                    if v=='injuries' and dy==1:
                                        monthkeys = jsonlist[i][tables[dy].attrs['name']].replace('-', '')

                                for (key, value) in data[v]['data'][yearkeys].items():
                                    if key == monthkeys[-2:]:
                                        months = monthkeys[-2:]
                                        arr1 = value

                                arr1.append(dic)
                                if len(months) > 0:
                                    data[v]['data'][yearkeys][months] = arr1
                                else:
                                    data[v]['data'][yearkeys].setdefault(monthkeys[-2:], arr1)

                                print(dic)

            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        vc_url = VC_URL + str(int(time.time() * 1000))
        resp = self.s.get(vc_url)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()
