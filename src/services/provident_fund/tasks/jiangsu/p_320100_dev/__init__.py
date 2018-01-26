# cff---南京--江苏省   公积金信息

import time
import requests
from bs4 import BeautifulSoup
import json
import datetime

from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError, InvalidConditionError, \
    PreconditionNotSatisfiedError
from services.commons import AbsFetchTask

MAIN_URL = r''
LOGIN_URL = r"http://www.njgjj.com/login-per.jsp"
Post_URL="http://www.njgjj.com/per.login"
VC_URL = r"http://www.njgjj.com/vericode.jsp"


class Task(AbsFetchTask):
    task_info = dict(
        city_name="南京",
        help="""
            <li>个人初始密码为公积金账号后四位加00</li>
            """,

        developers = [{'name': '程菲菲', 'email': 'feifei_cheng@chinahrs.net'}]
    )

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.79 Safari/537.36',
            'Accept-Encoding':'gzip, deflate',
            'Host': 'www.njgjj.com',
            'X-Requested-With':'XMLHttpRequest'
        }

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '证件号码' in params, '缺少证件号码'
        assert '密码' in params, '缺少密码'
        # other check
        证件号码 = params['证件号码']
        密码 = params['密码']

        if len(证件号码) == 0:
            raise InvalidParamsError('证件号码为空，请输入证件号码')
        elif len(证件号码) < 15:
            raise InvalidParamsError('证件号码不正确，请重新输入')

        if len(密码) == 0:
            raise InvalidParamsError('密码为空，请输入密码！')
        elif len(密码) < 6:
            raise InvalidParamsError('密码不正确，请重新输入！')

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '证件号码' not in params:
                params['证件号码'] = meta.get('证件号码')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '证件号码' and '证件号码' in meta:
                continue
            elif pr['key'] == '密码' and '密码' in meta:
                continue
            res.append(pr)
        return res


    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params.get("证件号码")
                account_pass = params.get("密码")
                vc = params.get("vc")

                data={
                    'certinum': id_num,
                    'perpwd': account_pass,
                    'vericode': vc
                }

                resp = self.s.post(Post_URL, data=data)
                respInfo=BeautifulSoup(resp.content,'html.parser')
                infos=respInfo.find('li',{'class':'text'})
                if(infos!=None):
                    raise InvalidParamsError(infos.text)
                else:
                    self.result_key = id_num
                    self.result_meta['证件号码'] =id_num
                    self.result_meta['密码']=account_pass

                    return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='证件号码', name='证件号码', cls='input',value=params.get('证件号码', '')),
            dict(key='密码', name='密码', cls='input:password',value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)


    def _converType(self,strname):
        resstring=""
        if '汇缴' in strname:
            resstring='汇缴'
        elif '还贷' in strname:
            resstring='还贷'
        else:
            resstring=strname
        return resstring

    def _unit_fetch(self):
        try:
            self.result_data['baseInfo'] = {}
            self.result_data['detail'] = {"data": {}}
            self.result_data['companyList']=[]

            # 基本信息
            res=self.s.get("http://www.njgjj.com/init.summer?_PROCID=80000003")
            soup=BeautifulSoup(res.content,'html.parser')
            uunum=soup.find('input',{'id':'accnum'})['value']
            username=soup.find('input',{'id':'accname'})['value']
            personid=soup.find('input',{'id':'certinum'})['value']
            times=str(time.time()*1000)[0:13]
            data={
                'accname':username,
                'accnum':uunum,
                'prodcode':1,
                '_PROCID':'80000003',
                '_PAGEID': 'step1',
                'certinum':personid,
            }
            resp=self.s.post("http://www.njgjj.com/command.summer?uuid="+times,data)
            soupData=json.loads(resp.text)['data']
            status = ""
            if (soupData['indiaccstate'] == "0"):
                status = '缴存'
            else:
                status = '封存'


            # 缴费明细
            resDetail = self.s.get("http://www.njgjj.com/init.summer?_PROCID=70000002")
            soopDetail = BeautifulSoup(resDetail.content, 'html.parser')
            ghosts =soopDetail.find('textarea', {'name': 'DATAlISTGHOST'}).text
            pools =soopDetail.find('textarea', {'name': '_DATAPOOL_'}).text

            # data2={
            #     'begdate':str(int(time.strftime("%Y",time.localtime()))-10)+time.strftime("-%m-%d",time.localtime()),
            #     'enddate':time.strftime("%Y-%m-%d",time.localtime()),
            #     '_PROCID':'70000002',
            #     #'accnum': uunum,
            #     '_PAGEID':'step1',
            #     'accname':username,
            #     '_ACCNUM': uunum,
            #     '_IS':'-27157826'  # resDetail.text.split('=')[46].split(',')[4].split(':')[1].replace('"','')
            # }
            #respDetail=self.s.post("http://www.njgjj.com/command.summer?uuid="+times+"",data2)

            #ghostss='rO0ABXNyABNqYXZhLnV0aWwuQXJyYXlMaXN0eIHSHZnHYZ0DAAFJAARzaXpleHAAAAABdwQAAAAKc3IAJWNvbS55ZHlkLm5icC5lbmdpbmUucHViLkRhdGFMaXN0R2hvc3RCsjhA3j2pwwIAA0wAAmRzdAASTGphdmEvbGFuZy9TdHJpbmc7TAAEbmFtZXEAfgADTAADc3FscQB+AAN4cHQAEHdvcmtmbG93LmNmZy54bWx0AAlkYXRhbGlzdDJ0AL5zZWxlY3QgaW5zdGFuY2UsIHVuaXRhY2NudW0xLCB1bml0YWNjbmFtZSwgYWNjbnVtMSwgYWNjbmFtZTEsIGNlcnRpbnVtLCB0cmFuc2RhdGUsIHJlYXNvbiAsIGRwYnVzaXR5cGUsIGJhc2VudW0sIHBheXZvdWFtdCwgc2Vxbm8gZnJvbSBkcDA3NyB3aGVyZSBpbnN0YW5jZSA9LTI2ODM3MzY4IG9yZGVyIGJ5IHRyYW5zZGF0ZSBkZXNjeA=='
            #poolss='rO0ABXNyABZjb20ueWR5ZC5wb29sLkRhdGFQb29sp4pd0OzirDkCAAZMAAdTWVNEQVRFdAASTGphdmEvbGFuZy9TdHJpbmc7TAAGU1lTREFZcQB+AAFMAAhTWVNNT05USHEAfgABTAAHU1lTVElNRXEAfgABTAAHU1lTV0VFS3EAfgABTAAHU1lTWUVBUnEAfgABeHIAEWphdmEudXRpbC5IYXNoTWFwBQfawcMWYNEDAAJGAApsb2FkRmFjdG9ySQAJdGhyZXNob2xkeHA/QAAAAAAAGHcIAAAAIAAAABV0AAdfQUNDTlVNdAAQMzIwMTAwMDI3NTcxMTg4N3QAA19SV3QAAXd0AAtfVU5JVEFDQ05VTXB0AAdfUEFHRUlEdAAFc3RlcDF0AANfSVNzcgAOamF2YS5sYW5nLkxvbmc7i+SQzI8j3wIAAUoABXZhbHVleHIAEGphdmEubGFuZy5OdW1iZXKGrJUdC5TgiwIAAHhw//////5mfoh0AAxfVU5JVEFDQ05BTUV0ADnljZfkuqzmg6DkvJfkurrlipvotYTmupDmnI3liqHmnInpmZDlhazlj7jnrKzkuIDliIblhazlj7h0AAZfTE9HSVB0ABEyMDE4MDEwMzE1MzY1Njc5NnQACF9BQ0NOQU1FdAAG6LCI56uLdAAJaXNTYW1lUGVydAAFZmFsc2V0AAdfUFJPQ0lEdAAINzAwMDAwMDJ0AAtfU0VORE9QRVJJRHQAEjMyMTEwMjE5ODYwODIwMDAzNnQAEF9ERVBVVFlJRENBUkROVU10ABIzMjExMDIxOTg2MDgyMDAwMzZ0AAlfU0VORFRJTUV0AAoyMDE4LTAxLTAzdAALX0JSQU5DSEtJTkR0AAEwdAAJX1NFTkREQVRFdAAKMjAxOC0wMS0wM3QAE0NVUlJFTlRfU1lTVEVNX0RBVEVxAH4AInQABV9UWVBFdAAEaW5pdHQAB19JU0NST1BxAH4AIHQACV9QT1JDTkFNRXQAGOS4quS6uuaYjue7huS/oeaBr+afpeivonQAB19VU0JLRVlwdAAIX1dJVEhLRVlxAH4AIHh0AAhAU3lzRGF0ZXQAB0BTeXNEYXl0AAlAU3lzTW9udGh0AAhAU3lzVGltZXQACEBTeXNXZWVrdAAIQFN5c1llYXI='

            datas={
                'dynamicTable_page':'/ydpx/70000002/700002_01.ydpx',
                'dynamicTable_id':'datalist2',
                'dynamicTable_currentPage': 0,
                'dynamicTable_nextPage': 1,
                'dynamicTable_pageSize': 10,
                'dynamicTable_paging': 'true',
                'DATAlISTGHOST':ghosts,
                '_DATAPOOL_':pools,
                'dynamicTable_configSqlCheck':'0',
                'errorFilter':'1=1',
                'begdate':str(int(time.strftime("%Y",time.localtime()))-10)+time.strftime("-%m-%d",time.localtime()),
                'enddate':time.strftime("%Y-%m-%d",time.localtime()),
                '_PROCID':'70000002',
                '_CHANNEL':1,
                '_APPLY':0,
                'accname':username,
                'accnum':uunum,
            }
            respDetail2 = self.s.post("http://www.njgjj.com/dynamictable?uuid=" + times + "", datas)

            baseDetail = self.result_data["detail"]["data"]
            model = {}
            lastTime = ""  # 最后一次汇补缴时间
            lastMoney = ""  # 最后一次汇补缴金额
            continueCount = 0  # 汇补缴累积次数
            infoDetail=json.loads(respDetail2.text)['data']['data']

            for q in range(len(infoDetail)):
                if '汇缴' in infoDetail[q]['reason']:
                    lastTime= infoDetail[q]['transdate']
                    lastMoney= infoDetail[q]['basenum']
                    break

            for p in range(len(infoDetail)):
                tds=infoDetail[p]
                years=tds['transdate'][0:4]
                months=tds['transdate'][5:7]
                if '还贷' not in tds['reason']:
                    model = {
                        '时间': tds['transdate'],
                        '类型': self._converType(tds['reason']),
                        '汇缴年月': '',
                        '收入': tds['basenum'],
                        '支出': '',
                        '余额': tds['payvouamt'],
                        '单位名称': tds['unitaccname']
                    }
                else:
                    model = {
                        '时间': tds['transdate'],
                        '类型': self._converType(tds['reason']),
                        '汇缴年月': '',
                        '收入': '',
                        '支出': tds['basenum'],
                        '余额': tds['payvouamt'],
                        '单位名称': tds['unitaccname']
                    }

                if '汇缴' in tds['reason']:
                    continueCount=continueCount+1

                baseDetail.setdefault(years, {})
                baseDetail[years].setdefault(months, [])
                baseDetail[years][months].append(model)


            # 个人基本信息
            self.result_data['baseInfo'] = {
                '姓名': username,
                '证件号': personid,
                '证件类型': '身份证',
                '个人编号': uunum,
                '公积金帐号': soupData['cardnocsp'],

                '单位缴存比例': str(int(float(soupData['unitprop']) * 100)) + '%',
                '个人缴存比例': str(int(float(soupData['indiprop']) * 100)) + '%',
                '开户日期': soupData['opnaccdate'],
                '手机号': soupData['linkphone'],
                '月应缴额': soupData['amt2'],

                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '城市名称': '南京市',
                '城市编号': '320100',

                '最近汇款日期': lastTime,
                '最近汇款金额': lastMoney,
                '累计汇款次数': continueCount,
            }

            # companyList
            self.result_data['companyList'].append({
                "单位名称": soupData['_UNITACCNAME'],
                "单位登记号": soupData['unitaccnum'],
                "所属管理部编号": "",
                "所属管理部名称": "",
                "当前余额": soupData['amt1'],
                "帐户状态": status,
                "当年缴存金额": "",
                "当年提取金额": "",
                "上年结转余额": "",
                "最后业务日期": soupData['lpaym'],
                "转出金额": ""
            })

            # identity 信息
            self.result['identity'] = {
                "task_name": "南京",
                "target_name": username,
                "target_id": self.result_meta['证件号码'],
                "status":status
            }

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        resp = self.s.get(VC_URL)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task(SessionData()))
    client.run()

    # 321102198608200036  860820

    # 320112197211230410  002568
    #