# cff---厦门  社保信息

from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError, InvalidConditionError, \
    PreconditionNotSatisfiedError
from services.commons import AbsFetchTask

import time
import requests
from bs4 import BeautifulSoup
import json
import ssl
import urllib3
import re


MAIN_URL = r'https://app.xmhrss.gov.cn/UCenter/index_grjbxx.xhtml'
LOGIN_URL = r"https://app.xmhrss.gov.cn/login.xhtml"
VC_URL = r"https://app.xmhrss.gov.cn/vcode.xhtml"
Detail_URL=r"https://app.xmhrss.gov.cn/UCenter/sbjfxxcx.xhtml"


class Task(AbsFetchTask):
    task_info = dict(
        city_name="厦门",
        help="""
        <li>初始密码是123456</li>
        <li>如您未在社保网站查询过您的社保信息，请到厦门社保网上服务平台完成“注册”然后再登录</li>
        <li>如未“交易密码”，请携带本人的社会保障卡和身份证件，到市、区社保经办机构或所在的社区劳动保障服务机构修改；也可以在“劳动保障自助服务机”上自行修改</li>
        """
    )

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36',
            'Accept-Encoding':'gzip, deflate, sdch',
            'Host': 'app.xmhrss.gov.cn',
        }

    def _prepare(self, data=None):
        super()._prepare()
        requests.packages.urllib3.disable_warnings()
        self.result_data['baseInfo']={}

    def _query(self, params: dict):
        """任务状态查询"""
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()
            # pass

    def _new_vc(self):
        resp = self.s.get(VC_URL,verify=False)
        return dict(cls='data:image', content=resp.content, content_type=resp.headers['Content-Type'])

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '社会保险号' in params, '缺少社会保险号'
        assert '密码' in params, '缺少密码'
        # other check
        用户名 = params['社会保险号']
        密码 = params['密码']

        if len(用户名) == 0:
            raise InvalidParamsError('社会保险号为空，请输入社会保险号')
        elif len(用户名) < 15:
            raise InvalidParamsError('社会保险号不正确，请重新输入')

        if len(密码) == 0:
            raise InvalidParamsError('密码为空，请输入密码！')
        elif len(密码) < 6:
            raise InvalidParamsError('密码不正确，请重新输入！')

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '社会保险号' not in params:
                params['社会保险号'] = meta.get('社会保险号')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '社会保险号' and '社会保险号' in meta:
                continue
            elif pr['key'] == '密码' and '密码' in meta:
                continue
            res.append(pr)
        return res

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)

                id_num = params.get("社会保险号")
                account_pass = params.get("密码")
                vc = params.get("vc")

                data = {
                    'id0000': id_num,
                    'userpwd': account_pass,
                    'validateCode': vc,
                    'date': str(time.time() * 1000)[0:13]
                }
                resp = self.s.post("https://app.xmhrss.gov.cn/login_dowith.xhtml", data=data)
                res=json.loads(resp.text)

                if(res['result']==False):
                    raise InvalidParamsError(res['msg'])
                elif (res['result']==True):

                    # 保存到meta
                    self.result_key = id_num
                    self.result_meta['社会保险号'] = id_num
                    self.result_meta['密码'] = account_pass

                    return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='社会保险号', name='社会保险号', cls='input', placeholder='请输入社会保险号', value=params.get('社会保险号', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _convert_type(self,num):
        resinfo=""
        if(num=="有效"):
            resinfo="正常"
        else:
            resinfo="异常"
        return resinfo

    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            # 个人信息
            resp = self.s.get(MAIN_URL)
            soup = BeautifulSoup(resp.content, 'html.parser')
            data = soup.find('table', {'class': 'tab3'}).findAll('tr')

            # 社保明细
            startTime = "199001"
            endTime = time.strftime("%Y%m", time.localtime())  # 查询结束时间

            # 社保缴费明细-----养老
            self.result['data']["old_age"] = { "data": {}}
            basedataE = self.result['data']["old_age"]["data"]
            modelE = {}
            peroldTotal=0.0
            detailEI = self.s.get(Detail_URL + "?xzdm00=2&zmlx00=&qsnyue="+startTime+"&jznyue="+endTime+"")
            sEI = BeautifulSoup(detailEI.content,'html.parser').find('table',{'class':'tab5'}).findAll("tr")

            for b in range(len(sEI)):
                td2 = sEI[b].findAll('td')
                urlE = "https://app.xmhrss.gov.cn/UCenter/" + sEI[b].find('a')['href']
                dateE = BeautifulSoup(self.s.get(urlE).content, 'html.parser').findAll("td")
                years = re.sub('\s', '', dateE[14].text)[0:4]
                months = re.sub('\s', '', dateE[14].text)[4:6]
                basedataE.setdefault(years, {})
                basedataE[years].setdefault(months, [])

                modelE = {
                    '缴费时间': re.sub('\s', '', dateE[14].text),
                    '缴费类型': re.sub('\s', '', dateE[10].text),
                    '缴费基数': re.sub('\s', '', dateE[34].text),
                    '公司缴费': float(re.sub('\s', '', dateE[28].text)),
                    '个人缴费': float(re.sub('\s', '', dateE[32].text)),
                    '缴费单位': re.sub('\s', '', dateE[4].text),
                }

                if ("已缴费" in re.sub('\s', '', dateE[0].text)):
                    peroldTotal += float(re.sub('\s', '', dateE[32].text))
                basedataE[years][months].append(modelE)


            self.result['data']["medical_care"] = {"data": {}}
            basedataH = self.result['data']["medical_care"]["data"]
            modelH = {}
            permedicalTotal=0.0
            # 社保明细-----医疗
            detailHI = self.s.get(Detail_URL + "?xzdm00=1&zmlx00=&qsnyue=" + startTime + "&jznyue=" + endTime + "")
            sHI = BeautifulSoup(detailHI.content, 'html.parser').find('table', {'class': 'tab5'}).findAll("tr")

            for a in range(len(sHI)):
                td = sHI[a].findAll('td')
                urlH = "https://app.xmhrss.gov.cn/UCenter/" + sHI[a].find('a')['href']
                dateH = BeautifulSoup(self.s.get(urlH).content, 'html.parser').findAll("td")
                yearH = re.sub('\s', '', dateH[14].text)[0:4]
                monthH = re.sub('\s', '', dateH[14].text)[4:6]
                basedataH.setdefault(yearH, {})
                basedataH[yearH].setdefault(monthH, [])

                modelH = {
                    '缴费时间': re.sub('\s', '', dateH[14].text),
                    '缴费类型': re.sub('\s', '', dateH[10].text),
                    '缴费基数': re.sub('\s', '', dateH[34].text),
                    '公司缴费': float(re.sub('\s', '', dateH[28].text)),
                    '个人缴费': float(re.sub('\s', '', dateH[32].text)),
                    '缴费单位': re.sub('\s', '', dateH[4].text),
                }

                if ("已缴费" in re.sub('\s', '', dateH[0].text)):
                    permedicalTotal += float(re.sub('\s', '', dateH[32].text))
                basedataH[yearH][monthH].append(modelH)


            self.result['data']["unemployment"] = {"data": {}}
            basedataI = self.result['data']["unemployment"]["data"]
            modelI = {}
            # 社保明细-----失业
            detailII = self.s.get(Detail_URL + "?xzdm00=4&zmlx00=&qsnyue=" + startTime + "&jznyue=" + endTime + "")
            sII = BeautifulSoup(detailII.content, 'html.parser').find('table', {'class': 'tab5'}).findAll("tr")

            for c in range(len(sII)):
                td3 = sII[c].findAll('td')
                urlI = "https://app.xmhrss.gov.cn/UCenter/" + sII[c].find('a')['href']
                dateI = BeautifulSoup(self.s.get(urlI).content, 'html.parser').findAll("td")
                yearI = re.sub('\s', '', dateI[14].text)[0:4]
                monthI = re.sub('\s', '', dateI[14].text)[4:6]
                basedataI.setdefault(yearI, {})
                basedataI[yearI].setdefault(monthI, [])

                modelI = {
                    '缴费时间': re.sub('\s', '', dateI[14].text),
                    '缴费类型': re.sub('\s', '', dateI[10].text),
                    '缴费基数': re.sub('\s', '', dateI[34].text),
                    '公司缴费': float(re.sub('\s', '', dateI[28].text)),
                    '个人缴费': float(re.sub('\s', '', dateI[32].text)),
                    '缴费单位': re.sub('\s', '', dateI[4].text),
                }

                basedataI[yearI][monthI].append(modelI)


            self.result['data']["injuries"] = {"data": {}}
            basedataC = self.result['data']["injuries"]["data"]
            modelC = {}
            # 社保明细-----工伤
            detailCI = self.s.get(Detail_URL + "?xzdm00=3&zmlx00=&qsnyue=" + startTime + "&jznyue=" + endTime + "")
            sCI = BeautifulSoup(detailCI.content, 'html.parser').find('table', {'class': 'tab5'}).findAll("tr")

            for d in range(len(sCI)):
                td4 = sCI[d].findAll('td')
                urlC = "https://app.xmhrss.gov.cn/UCenter/" + sCI[d].find('a')['href']
                dateC = BeautifulSoup(self.s.get(urlC).content, 'html.parser').findAll("td")
                yearC = re.sub('\s', '', dateC[14].text)[0:4]
                monthC = re.sub('\s', '', dateC[14].text)[4:6]
                basedataC.setdefault(yearC, {})
                basedataC[yearC].setdefault(monthC, [])

                modelC = {
                    '缴费时间': re.sub('\s', '', dateC[14].text),
                    '缴费类型': re.sub('\s', '', dateC[10].text),
                    '缴费基数': re.sub('\s', '', dateC[34].text),
                    '公司缴费': float(re.sub('\s', '', dateC[28].text)),
                    '个人缴费': "-",
                    '缴费单位': re.sub('\s', '', dateC[4].text),
                }

                basedataC[yearC][monthC].append(modelC)


            self.result['data']["maternity"] = {"data": {}}
            basedataB = self.result['data']["maternity"]["data"]
            modelB = {}
            # 社保明细-----生育
            detailBI = self.s.get(Detail_URL + "?xzdm00=5&zmlx00=&qsnyue=" + startTime + "&jznyue=" + endTime + "")
            sBI = BeautifulSoup(detailBI.content, 'html.parser').find('table', {'class': 'tab5'}).findAll("tr")

            for f in range(len(sBI)):
                td5 = sBI[f].findAll('td')
                urlB = "https://app.xmhrss.gov.cn/UCenter/" + sBI[f].find('a')['href']
                dateB = BeautifulSoup(self.s.get(urlB).content, 'html.parser').findAll("td")
                yearB = re.sub('\s', '', dateB[14].text)[0:4]
                monthB = re.sub('\s', '', dateB[14].text)[4:6]
                basedataB.setdefault(yearB, {})
                basedataB[yearB].setdefault(monthB, [])

                modelB = {
                    '缴费时间': re.sub('\s', '', dateB[14].text),
                    '缴费类型': re.sub('\s', '', dateB[10].text),
                    '缴费基数': re.sub('\s', '', dateB[34].text),
                    '公司缴费': float(re.sub('\s', '', dateB[28].text)),
                    '个人缴费': "-",
                    '缴费单位': re.sub('\s', '', dateB[4].text),
                }

                basedataB[yearB][monthB].append(modelB)


            #  个人基本信息
            # 缴费时长
            moneyCount=[len(sEI),len(sHI),len(sII),len(sCI),len(sBI)]

            self.result_data['baseInfo'] = {
                '姓名': data[0].findAll('td')[1].text,
                '身份证号': data[1].findAll('td')[1].text,
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '城市名称': '厦门',
                '城市编号': '350200',
                '缴费时长': max(moneyCount),
                '最近缴费时间': re.sub('\s','',sEI[len(sEI)-1].findAll("td")[3].text),
                '开始缴费时间': re.sub('\s','',sEI[0].findAll("td")[3].text),
                '个人养老累计缴费': peroldTotal,
                '个人医疗累计缴费': permedicalTotal,
                '状态': self._convert_type(data[3].findAll('td')[1].text.replace('\r', '').replace('\n', '').replace('\t', '').strip()),
                '工作状态': data[8].findAll('td')[1].text,
                '社会保障卡卡号': data[2].findAll('td')[1].text,
            }

            self.result['identity'] = {
                "task_name": "厦门",
                "target_name": data[0].findAll('td')[1].text,
                "target_id": self.result_meta['社会保险号'],
                "status": self._convert_type(data[3].findAll('td')[1].text.replace('\r', '').replace('\n', '').replace('\t', '').strip())
            }

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task(SessionData()))
    client.run()

    # 350524196209146816  123789


