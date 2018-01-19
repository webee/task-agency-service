# cff---无锡--江苏省   公积金信息

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

MAIN_URL = r'http://58.215.195.18:10010/zg_info.do'
LOGIN_URL = r"http://58.215.195.18:10010/login_person.jsp"
VC_URL = r"http://58.215.195.18:10010/jcaptcha?tmp="
Detail_URL="http://58.215.195.18:10010/mx_info.do?flag=1"


class Task(AbsFetchTask):
    task_info = dict(
        city_name="无锡",
        help="""
            <li></li>
            """,

        developers = [{'name': '程菲菲', 'email': 'feifei_cheng@chinahrs.net'}]
    )

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.79 Safari/537.36',
            'Accept-Encoding':'gzip, deflate',
            'Host': '58.215.195.18:10010',
            'Accept':'image/webp,image/apng,image/*,*/*;q=0.8'
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
        assert '身份证号' in params, '缺少身份证号'
        assert '密码' in params, '缺少密码'
        # other check
        身份证号 = params['身份证号']
        密码 = params['密码']

        if len(身份证号) == 0:
            raise InvalidParamsError('身份证号为空，请输入身份证号')
        elif len(身份证号) < 15:
            raise InvalidParamsError('身份证号不正确，请重新输入')

        if len(密码) == 0:
            raise InvalidParamsError('密码为空，请输入密码！')
        elif len(密码) < 6:
            raise InvalidParamsError('密码不正确，请重新输入！')

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
            res.append(pr)
        return res


    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params.get("身份证号")
                account_pass = params.get("密码")
                vc = params.get("vc")

                data={
                    'logontype':'1',
                    'loginname': id_num,
                    'type':'person',
                    'password': account_pass,
                    '_login_checkcode': vc,
                    'image.x':'25',
                    'image.y':'18',
                    'image':'submit'
                }
                resp = self.s.post("http://58.215.195.18:10010/logon.do", data=data)
                respInfo=BeautifulSoup(resp.content,'html.parser')
                if('出现错误' in respInfo.text):
                    raise InvalidParamsError(respInfo.findAll('font')[1].text.strip())
                else:
                    self.result_key = id_num
                    self.result_meta['身份证号'] =id_num
                    self.result_meta['密码']=account_pass

                    return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input',value=params.get('身份证号', '')),
            dict(key='密码', name='密码', cls='input:password',value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _short_type(self,keyname):
        res=""
        if(keyname=="公积金月对冲还贷"):
            res="对冲还贷"
        else:
            res=keyname
        return res


    def _unit_fetch(self):
        try:
            self.result_data['baseInfo'] = {}
            self.result_data['detail'] = {"data": {}}
            self.result_data['companyList']=[]
            resp = self.s.get(MAIN_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            datas = soup.find('table',{'id':'listView'}).findAll('tr')

            #公积金明细
            lastTime=""         #  最后一次汇补缴时间
            lastMoney=""        #  最后一次汇补缴金额
            continueCount=0     #  汇补缴累积次数
            resp2 = self.s.get(Detail_URL)
            soup2 = BeautifulSoup(resp2.content, 'html.parser')
            baseDetail = self.result_data["detail"]["data"]
            model = {}

            status = ""
            if (soup2.findAll('input')[0]['value'] == "正常汇缴"):
                status = "缴存"
            else:
                status = "封存"

            data2={
                'zjlx': '1',
                'hjstatus': soup2.findAll('input')[0]['value'],
                'submit': '查  询'
            }
            resDetail=self.s.post("http://58.215.195.18:10010/mx_info.do",data2)
            dataDetail=BeautifulSoup(resDetail.content,'html.parser').findAll('table')[1].findAll('tr')
            for p in range(1,len(dataDetail)):
                tds=dataDetail[p].findAll("td")
                oprateTime=tds[1].text.split(';')[0].split('=')[1]
                hjTime=tds[2].text.split(';')[0].split('=')[1].replace('"','').strip()
                years=hjTime[0:4]
                months=hjTime[4:6]
                model = {
                    '时间': oprateTime[2:6]+'-'+oprateTime[6:8]+'-'+oprateTime[8:10],
                    '类型': tds[3].text,
                    '汇缴年月': hjTime,
                    '收入': tds[4].text.replace('\n','').replace(',',''),
                    '支出': tds[5].text.replace('\n','').replace(',',''),
                    '余额': tds[6].text.replace('\n','').replace(',',''),
                    '单位名称': tds[0].text
                }

                if '汇缴' in tds[3].text:
                    lastTime=oprateTime[2:6]+'-'+oprateTime[6:8]+'-'+oprateTime[8:10]
                    lastMoney=tds[4].text.replace('\n','').replace(',','')
                    continueCount=continueCount+1

                baseDetail.setdefault(years, {})
                baseDetail[years].setdefault(months, [])
                baseDetail[years][months].append(model)


            # 开户日期
            times=datas[8].text.split(';')[0].split('=')[1]
            fomtime=times[2:6]+'-'+times[6:8]+'-'+times[8:10]

            pEMoney=float(datas[2].findAll("td")[1].text.replace('\n', '').replace('元', '').replace('()',''))/2

            # 个人基本信息
            self.result_data['baseInfo'] = {
                '姓名': datas[0].findAll("td")[3].text,
                '证件号': datas[1].findAll("td")[1].text,
                '证件类型': '身份证',
                '个人编号': datas[0].findAll("td")[1].text,
                '公积金帐号': '',

                '缴存基数': datas[4].findAll("td")[1].text,
                '单位缴存比例': datas[6].findAll("td")[1].text,
                '个人缴存比例': datas[5].findAll("td")[1].text,
                '单位月缴存额': pEMoney,
                '个人月缴存额': pEMoney,
                '开户日期': fomtime,

                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '城市名称': '无锡市',
                '城市编号': '320200',

                '最近汇款日期': lastTime,
                '最近汇款金额': lastMoney,
                '累计汇款次数': continueCount,
            }


            # companyList
            self.result_data['companyList'].append({
                "单位名称": datas[1].findAll("td")[3].text,
                "单位登记号": '',
                "所属管理部编号": "",
                "所属管理部名称": "",
                "当前余额": datas[3].findAll("td")[1].text.replace('\n','').replace('元','').replace('()','').replace(',',''),
                "帐户状态": '',
                "当年缴存金额": "",
                "当年提取金额": "",
                "上年结转余额": "",
                "最后业务日期": datas[7].text.split(';')[0].split('=')[1].replace('"','').strip(),
                "转出金额": ""
            })


            # identity 信息
            self.result['identity'] = {
                "task_name": "无锡",
                "target_name": datas[0].findAll("td")[3].text,
                "target_id": self.result_meta['身份证号'],
                "status": status
            }

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        resp = self.s.get(VC_URL)
        return dict(content=resp.content, cls='data:image')


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task(SessionData()))
    client.run()

    # 320923199111177271  177271

    # 411327199309200612  200612
