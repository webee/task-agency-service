# cff---济南  社保信息

from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError, InvalidConditionError, \
    PreconditionNotSatisfiedError
from services.commons import AbsFetchTask

import time
import requests
from bs4 import BeautifulSoup
import json
import base64
from PIL import Image
import io
import hashlib


LOGIN_URL = r"http://60.216.99.138/hsp/logonDialog.jsp"
VC_URL = r"http://60.216.99.138/hsp/genAuthCode"


class Task(AbsFetchTask):
    task_info = dict(
        city_name="济南",
        help="""
        <li>如您未在社保网站查询过您的社保信息，请到济南社保网上服务平台完成“注册”并获取密码</li>
        <li>如您还未获取社保卡，可向公司经办人索取，或者凭身份证到当地社保网点查询</li>
        """
    )

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36',
            'Accept-Encoding':'gzip, deflate, sdch',
            'Host': '60.216.99.138',
            'X-Requested-With':'XMLHttpRequest'
        }

    def _prepare(self, data=None):
        super()._prepare()
        self.result_data['baseInfo']={}

    def _query(self, params: dict):
        """任务状态查询"""
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()
            # pass

    def _new_vc(self):
        resps = json.loads(self.s.get(VC_URL).text)
        firstNum = resps['numLeftBase64']
        oprate = resps['operatorBase64']
        lastNum = resps['numRightBase64']
        equla = resps['equalsBase64']

        arr = [firstNum, oprate, lastNum, equla]
        toImage = Image.new('RGB', (110, 50), (255, 255, 255))
        for i in range(4):
            fromImge = Image.open(io.BytesIO(base64.b64decode(arr[i])))
            if (fromImge.mode == "P"):
                fromImge.convert("RGB")
            loc = (i * 22 + 15, 10)
            toImage.paste(fromImge, loc)

        toImage.show()

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '身份证号' in params, '缺少身份证号'
        assert '密码' in params, '密码'
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

    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)

                id_num = params.get("身份证号")
                account_pass = params.get("密码")
                m = hashlib.md5()
                m.update(str(account_pass).encode(encoding="utf-8"))
                pw = m.hexdigest()

                self._new_vc()
                vc = input("请输入运算后的结果：")

                _xmlString = "<?xml version='1.0' encoding='UTF-8'?><p><s userid='" + id_num + "'/><s usermm='" + pw + "'/><s authcode='" + vc + "'/><s yxzjlx='A'/><s appversion='1.0.60'/><s dlfs='undefined'/></p>"

                resp = self.s.post("http://60.216.99.138/hsp/logon.do?method=doLogon&_xmlString=" + _xmlString)
                if('true' not in resp.text):
                    raise InvalidParamsError(resp.text)
                else:
                    uuid = resp.text.split(',')[2].split(':')[1].replace('"', '').replace('"', '')
                    res = self.s.get("http://60.216.99.138/hsp/hspUser.do?method=fwdQueryPerInfo&__usersession_uuid=" + uuid)
                    soup = BeautifulSoup(res.content, 'html.parser').findAll("tr")

                    # 保存到meta
                    self.result_key = id_num
                    self.result_meta['身份证号'] = id_num
                    self.result_meta['密码'] = account_pass


                    # 养老保险缴费明细
                    self.result['data']["old_age"] = {"data": {}}
                    basedataE = self.result['data']["old_age"]["data"]
                    modelE = {}
                    oldresp=self.s.get("http://60.216.99.138/hsp/siAd.do?method=queryAgedPayHis&__usersession_uuid=" + uuid )
                    oldData=BeautifulSoup(oldresp.text,'html.parser')
                    oldCount=oldData.findAll('font',{'class':'font'})[0].text   # 养老累积缴费月数
                    oldTotal=oldData.findAll('font',{'class':'font'})[1].text   # 养老累积缴费金额
                    oldStart=oldData.findAll('p')[2].text.split(':')[1].replace('\n','')[0:4]   # 养老开始日期
                    oldEnd=oldData.findAll('p')[3].text.split(':')[1].replace('\n','')[0:4]   # 养老结束日期

                    for yr in range(int(oldStart),int(oldEnd)+1):
                        detailEI=self.s.get("http://60.216.99.138/hsp/siAd.do?method=queryAgedPayHis&__usersession_uuid=" + uuid + "&year=" + str(yr) + "")
                        sEI = BeautifulSoup(detailEI.content, 'html.parser').find('table',{'class': 'defaultTableClass'}).findAll("tr")
                        for a in range(1,len(sEI)):
                            td = sEI[a].findAll("td")
                            years=td[0].find(type="text")["value"][0:4]
                            months=td[0].find(type="text")["value"][5:7]
                            basedataE.setdefault(years, {})
                            basedataE[years].setdefault(months, [])

                            modelE = {
                                '缴费时间': td[0].find(type="text")["value"],
                                '缴费类型':'',
                                '缴费基数': str(td[1].find(type="text")["value"]).replace(',', ''),
                                '公司缴费':'-',
                                '个人缴费': td[2].find(type="text")["value"],
                                '缴费单位': soup[9].findAll("td")[1].find(type="text")["value"],
                            }
                            basedataE[years][months].append(modelE)

                    # 医疗保险缴费明细
                    self.result['data']["medical_care"] = {"data": {}}
                    basedataH = self.result['data']["medical_care"]["data"]
                    modelH = {}
                    permedicalTotal = 0.0
                    medresp = self.s.get("http://60.216.99.138/hsp/siMedi.do?method=queryMediPayHis&__usersession_uuid=" + uuid)
                    medData = BeautifulSoup(medresp.text, 'html.parser')
                    medCount = medData.findAll('font', {'class': 'font'})[0].text  # 医疗累积缴费月数
                    medStart = medData.findAll('p')[2].text.split(':')[1].replace('\n', '')[0:4]  # 医疗开始日期
                    medEnd = medData.findAll('p')[3].text.split(':')[1].replace('\n', '')[0:4]  # 医疗结束日期

                    for yr2 in range(int(medStart),int(medEnd)+1):
                        detailHI=self.s.get("http://60.216.99.138/hsp/siMedi.do?method=queryMediPayHis&__usersession_uuid=" + uuid + "&year=" + str(yr2) + "")
                        sHI = BeautifulSoup(detailHI.content, 'html.parser').find('table',{'class': 'defaultTableClass'}).findAll("tr")
                        for b in range(1,len(sHI)):
                            td2 = sHI[b].findAll("td")
                            yearH=td2[0].find(type="text")["value"][0:4]
                            monthH=td2[0].find(type="text")["value"][5:7]
                            basedataH.setdefault(yearH, {})
                            basedataH[yearH].setdefault(monthH, [])

                            modelH = {
                                '缴费时间': td2[0].find(type="text")["value"],
                                '缴费类型':'',
                                '缴费基数': str(td2[1].find(type="text")["value"]).replace(',', ''),
                                '公司缴费':'-',
                                '个人缴费': td2[2].find(type="text")["value"],
                                '缴费单位': soup[9].findAll("td")[1].find(type="text")["value"],
                            }
                            basedataH[yearH][monthH].append(modelH)

                    # 失业保险缴费明细
                    self.result['data']["unemployment"] = {"data": {}}
                    basedataI = self.result['data']["unemployment"]["data"]
                    modelI = {}
                    uplresp = self.s.get("http://60.216.99.138/hsp/siLost.do?method=queryLostPayHis&__usersession_uuid=" + uuid)
                    uplData = BeautifulSoup(uplresp.text, 'html.parser')
                    uplCount = uplData.findAll('font', {'class': 'font'})[0].text  # 失业累积缴费月数
                    uplStart = uplData.findAll('p')[1].text.split(':')[1].replace('\n', '')[0:4]  # 失业开始日期
                    uplEnd = uplData.findAll('p')[2].text.split(':')[1].replace('\n', '')[0:4]  # 失业结束日期

                    for yr3 in range(int(uplStart), int(uplEnd) + 1):
                        detailII = self.s.get("http://60.216.99.138/hsp/siLost.do?method=queryLostPayHis&__usersession_uuid=" + uuid + "&year=" + str(yr3) + "")
                        sII = BeautifulSoup(detailII.content, 'html.parser').find('table', {'class': 'defaultTableClass'}).findAll("tr")
                        for c in range(1, len(sII)):
                            td3 = sII[c].findAll("td")
                            yearI = td3[0].find(type="text")["value"][0:4]
                            monthI = td3[0].find(type="text")["value"][5:7]
                            basedataI.setdefault(yearI, {})
                            basedataI[yearI].setdefault(monthI, [])

                            modelI = {
                                '缴费时间': td3[0].find(type="text")["value"],
                                '缴费类型': td3[4].find(type="text")["value"],
                                '缴费基数': str(td3[1].find(type="text")["value"]).replace(',', ''),
                                '公司缴费': '-',
                                '个人缴费': td3[2].find(type="text")["value"],
                                '缴费单位': soup[9].findAll("td")[1].find(type="text")["value"],
                            }
                            basedataI[yearI][monthI].append(modelI)

                    # 工伤保险缴费明细
                    self.result['data']["injuries"] = {"data": {}}
                    basedataC = self.result['data']["injuries"]["data"]
                    modelC = {}
                    injresp = self.s.get("http://60.216.99.138/hsp/siHarm.do?method=queryHarmPayHis&__usersession_uuid=" + uuid)
                    injData = BeautifulSoup(injresp.text, 'html.parser')
                    injCount = injData.findAll('font', {'class': 'font'})[0].text  # 失业累积缴费月数
                    injStart = injData.findAll('p')[1].text.split(':')[1].replace('\n', '')[0:4]  # 失业开始日期
                    injEnd = injData.findAll('p')[2].text.split(':')[1].replace('\n', '')[0:4]  # 失业结束日期

                    for yr4 in range(int(injStart), int(injEnd) + 1):
                        detailCI = self.s.get("http://60.216.99.138/hsp/siHarm.do?method=queryHarmPayHis&__usersession_uuid=" + uuid + "&year=" + str(yr4) + "")
                        sCI = BeautifulSoup(detailCI.content, 'html.parser').find('table', {'class': 'defaultTableClass'}).findAll("tr")
                        for d in range(1, len(sCI)):
                            td4 = sCI[d].findAll("td")
                            yearC = td4[0].find(type="text")["value"][0:4]
                            monthC = td4[0].find(type="text")["value"][5:7]
                            basedataC.setdefault(yearC, {})
                            basedataC[yearC].setdefault(monthC, [])

                            modelC = {
                                '缴费时间': td4[0].find(type="text")["value"],
                                '缴费类型': td4[2].find(type="text")["value"],
                                '缴费基数': '-',
                                '公司缴费': '-',
                                '个人缴费': '-',
                                '缴费单位': soup[9].findAll("td")[1].find(type="text")["value"],
                            }
                            basedataC[yearC][monthC].append(modelC)

                    # 生育保险缴费明细
                    self.result['data']["maternity"] = {"data": {}}
                    basedataB = self.result['data']["maternity"]["data"]
                    modelB = {}
                    matnresp = self.s.get("http://60.216.99.138/hsp/siBirth.do?method=queryBirthPayHis&__usersession_uuid=" + uuid)
                    matnData = BeautifulSoup(matnresp.text, 'html.parser')
                    matnCount = matnData.findAll('font', {'class': 'font'})[0].text  # 失业累积缴费月数
                    matnStart = matnData.findAll('p')[1].text.split(':')[1].replace('\n', '')[0:4]  # 失业开始日期
                    matnEnd = matnData.findAll('p')[2].text.split(':')[1].replace('\n', '')[0:4]  # 失业结束日期

                    for yr5 in range(int(matnStart), int(matnEnd) + 1):
                        detailBI = self.s.get("http://60.216.99.138/hsp/siBirth.do?method=queryBirthPayHis&__usersession_uuid=" + uuid + "&year=" + str(yr5) + "")
                        sBI = BeautifulSoup(detailBI.content, 'html.parser').find('table', {'class': 'defaultTableClass'}).findAll("tr")
                        for f in range(1, len(sBI)):
                            td5 = sBI[f].findAll("td")
                            yearB = td5[0].find(type="text")["value"][0:4]
                            monthB = td5[0].find(type="text")["value"][5:7]
                            basedataB.setdefault(yearB, {})
                            basedataB[yearB].setdefault(monthB, [])

                            modelB = {
                                '缴费时间': td5[0].find(type="text")["value"],
                                '缴费类型': td5[2].find(type="text")["value"],
                                '缴费基数': '-',
                                '公司缴费': '-',
                                '个人缴费': '-',
                                '缴费单位': soup[9].findAll("td")[1].find(type="text")["value"],
                            }
                            basedataB[yearB][monthB].append(modelB)


                    # 状态
                    status=""
                    if(sCI[len(sCI)-1].findAll("td")[2].find(type="text")["value"]=="正常缴费"):
                        status="正常"
                    else:
                        status="异常"

                    # 个人基本信息
                    self.result_data['baseInfo'] = {
                        '姓名': soup[0].findAll("td")[1].find(type="text")["value"],
                        '身份证号': self.result_meta['身份证号'],
                        '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                        '城市名称': '济南',
                        '城市编号': '370100',
                        '缴费时长': int(oldCount),
                        '最近缴费时间': oldData.findAll('p')[3].text.split(':')[1].replace('\n',''),
                        '开始缴费时间': oldData.findAll('p')[2].text.split(':')[1].replace('\n',''),
                        '个人养老累计缴费': float(oldTotal.replace(',','')),
                        '个人医疗累计缴费': '',
                        '状态': status,
                        '出生日期': soup[1].findAll("td")[3].find(type="text")["value"]
                    }

                    self.result_identity.update({
                        "task_name": "济南",
                        "target_name": soup[0].findAll("td")[1].find(type="text")["value"],
                        "target_id": self.result_meta['身份证号'],
                        "status": status
                    })

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input', placeholder='身份证号', value=params.get('身份证号', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
        ], err_msg)

    def _convert_type(self,num):
        resinfo=""
        if(num=="有效"):
            resinfo="正常"
        else:
            resinfo="异常"
        return resinfo

    def _unit_fetch(self):
        True
    #     try:
    #         # TODO: 执行任务，如果没有登录，则raise PermissionError
    #         # 个人信息
    #         resp = self.s.get(MAIN_URL)
    #         soup = BeautifulSoup(resp.content, 'html.parser')
    #         data = soup.find('table', {'class': 'tab3'}).findAll('tr')
    #
    #         # 社保明细
    #         startTime = "199001"
    #         endTime = time.strftime("%Y%m", time.localtime())  # 查询结束时间
    #
    #         # 社保缴费明细-----养老
    #         self.result['data']["old_age"] = { "data": {}}
    #         basedataE = self.result['data']["old_age"]["data"]
    #         modelE = {}
    #         peroldTotal=0.0
    #         detailEI = self.s.get(Detail_URL + "?xzdm00=2&zmlx00=&qsnyue="+startTime+"&jznyue="+endTime+"")
    #         sEI = BeautifulSoup(detailEI.content,'html.parser').find('table',{'class':'tab5'}).findAll("tr")
    #
    #         for b in range(len(sEI)):
    #             td2 = sEI[b].findAll('td')
    #             urlE = "https://app.xmhrss.gov.cn/UCenter/" + sEI[b].find('a')['href']
    #             dateE = BeautifulSoup(self.s.get(urlE).content, 'html.parser').findAll("td")
    #             years = re.sub('\s', '', dateE[14].text)[0:4]
    #             months = re.sub('\s', '', dateE[14].text)[4:6]
    #             basedataE.setdefault(years, {})
    #             basedataE[years].setdefault(months, [])
    #
    #             modelE = {
    #                 '缴费时间': re.sub('\s', '', dateE[14].text),
    #                 '缴费类型': re.sub('\s', '', dateE[10].text),
    #                 '缴费基数': re.sub('\s', '', dateE[34].text),
    #                 '公司缴费': float(re.sub('\s', '', dateE[28].text)),
    #                 '个人缴费': float(re.sub('\s', '', dateE[32].text)),
    #                 '缴费单位': re.sub('\s', '', dateE[4].text),
    #                 '单位划入帐户': float(re.sub('\s', '', dateE[38].text)),
    #                 '个人划入帐户': float(re.sub('\s', '', dateE[40].text))
    #             }
    #
    #             if ("已缴费" in re.sub('\s', '', dateE[0].text)):
    #                 peroldTotal += float(re.sub('\s', '', dateE[32].text))
    #             basedataE[years][months].append(modelE)
    #
    #
    #         self.result['data']["medical_care"] = {"data": {}}
    #         basedataH = self.result['data']["medical_care"]["data"]
    #         modelH = {}
    #         permedicalTotal=0.0
    #         # 社保明细-----医疗
    #         detailHI = self.s.get(Detail_URL + "?xzdm00=1&zmlx00=&qsnyue=" + startTime + "&jznyue=" + endTime + "")
    #         sHI = BeautifulSoup(detailHI.content, 'html.parser').find('table', {'class': 'tab5'}).findAll("tr")
    #
    #         for a in range(len(sHI)):
    #             td = sHI[a].findAll('td')
    #             urlH = "https://app.xmhrss.gov.cn/UCenter/" + sHI[a].find('a')['href']
    #             dateH = BeautifulSoup(self.s.get(urlH).content, 'html.parser').findAll("td")
    #             yearH = re.sub('\s', '', dateH[14].text)[0:4]
    #             monthH = re.sub('\s', '', dateH[14].text)[4:6]
    #             basedataH.setdefault(yearH, {})
    #             basedataH[yearH].setdefault(monthH, [])
    #
    #             modelH = {
    #                 '缴费时间': re.sub('\s', '', dateH[14].text),
    #                 '缴费类型': re.sub('\s', '', dateH[10].text),
    #                 '缴费基数': re.sub('\s', '', dateH[34].text),
    #                 '公司缴费': float(re.sub('\s', '', dateH[28].text)),
    #                 '个人缴费': float(re.sub('\s', '', dateH[32].text)),
    #                 '缴费单位': re.sub('\s', '', dateH[4].text),
    #                 '单位划入帐户': float(re.sub('\s', '', dateH[38].text)),
    #                 '个人划入帐户': float(re.sub('\s', '', dateH[40].text))
    #             }
    #
    #             if ("已缴费" in re.sub('\s', '', dateH[0].text)):
    #                 permedicalTotal += float(re.sub('\s', '', dateH[32].text))
    #             basedataH[yearH][monthH].append(modelH)
    #
    #
    #         self.result['data']["unemployment"] = {"data": {}}
    #         basedataI = self.result['data']["unemployment"]["data"]
    #         modelI = {}
    #         # 社保明细-----失业
    #         detailII = self.s.get(Detail_URL + "?xzdm00=4&zmlx00=&qsnyue=" + startTime + "&jznyue=" + endTime + "")
    #         sII = BeautifulSoup(detailII.content, 'html.parser').find('table', {'class': 'tab5'}).findAll("tr")
    #
    #         for c in range(len(sII)):
    #             td3 = sII[c].findAll('td')
    #             urlI = "https://app.xmhrss.gov.cn/UCenter/" + sII[c].find('a')['href']
    #             dateI = BeautifulSoup(self.s.get(urlI).content, 'html.parser').findAll("td")
    #             yearI = re.sub('\s', '', dateI[14].text)[0:4]
    #             monthI = re.sub('\s', '', dateI[14].text)[4:6]
    #             basedataI.setdefault(yearI, {})
    #             basedataI[yearI].setdefault(monthI, [])
    #
    #             modelI = {
    #                 '缴费时间': re.sub('\s', '', dateI[14].text),
    #                 '缴费类型': re.sub('\s', '', dateI[10].text),
    #                 '缴费基数': re.sub('\s', '', dateI[34].text),
    #                 '公司缴费': float(re.sub('\s', '', dateI[28].text)),
    #                 '个人缴费': float(re.sub('\s', '', dateI[32].text)),
    #                 '缴费单位': re.sub('\s', '', dateI[4].text),
    #                 '单位划入帐户': float(re.sub('\s', '', dateI[38].text)),
    #                 '个人划入帐户': float(re.sub('\s', '', dateI[40].text))
    #             }
    #
    #             basedataI[yearI][monthI].append(modelI)
    #
    #
    #         self.result['data']["injuries"] = {"data": {}}
    #         basedataC = self.result['data']["injuries"]["data"]
    #         modelC = {}
    #         # 社保明细-----工伤
    #         detailCI = self.s.get(Detail_URL + "?xzdm00=3&zmlx00=&qsnyue=" + startTime + "&jznyue=" + endTime + "")
    #         sCI = BeautifulSoup(detailCI.content, 'html.parser').find('table', {'class': 'tab5'}).findAll("tr")
    #
    #         for d in range(len(sCI)):
    #             td4 = sCI[d].findAll('td')
    #             urlC = "https://app.xmhrss.gov.cn/UCenter/" + sCI[d].find('a')['href']
    #             dateC = BeautifulSoup(self.s.get(urlC).content, 'html.parser').findAll("td")
    #             yearC = re.sub('\s', '', dateC[14].text)[0:4]
    #             monthC = re.sub('\s', '', dateC[14].text)[4:6]
    #             basedataC.setdefault(yearC, {})
    #             basedataC[yearC].setdefault(monthC, [])
    #
    #             modelC = {
    #                 '缴费时间': re.sub('\s', '', dateC[14].text),
    #                 '缴费类型': re.sub('\s', '', dateC[10].text),
    #                 '缴费基数': re.sub('\s', '', dateC[34].text),
    #                 '公司缴费': float(re.sub('\s', '', dateC[28].text)),
    #                 '个人缴费': "-",
    #                 '缴费单位': re.sub('\s', '', dateC[4].text),
    #                 '单位划入帐户': float(re.sub('\s', '', dateC[38].text)),
    #                 '个人划入帐户': float(re.sub('\s', '', dateC[40].text))
    #             }
    #
    #             basedataC[yearC][monthC].append(modelC)
    #
    #
    #         self.result['data']["maternity"] = {"data": {}}
    #         basedataB = self.result['data']["maternity"]["data"]
    #         modelB = {}
    #         # 社保明细-----生育
    #         detailBI = self.s.get(Detail_URL + "?xzdm00=5&zmlx00=&qsnyue=" + startTime + "&jznyue=" + endTime + "")
    #         sBI = BeautifulSoup(detailBI.content, 'html.parser').find('table', {'class': 'tab5'}).findAll("tr")
    #
    #         for f in range(len(sBI)):
    #             td5 = sBI[f].findAll('td')
    #             urlB = "https://app.xmhrss.gov.cn/UCenter/" + sBI[f].find('a')['href']
    #             dateB = BeautifulSoup(self.s.get(urlB).content, 'html.parser').findAll("td")
    #             yearB = re.sub('\s', '', dateB[14].text)[0:4]
    #             monthB = re.sub('\s', '', dateB[14].text)[4:6]
    #             basedataB.setdefault(yearB, {})
    #             basedataB[yearB].setdefault(monthB, [])
    #
    #             modelB = {
    #                 '缴费时间': re.sub('\s', '', dateB[14].text),
    #                 '缴费类型': re.sub('\s', '', dateB[10].text),
    #                 '缴费基数': re.sub('\s', '', dateB[34].text),
    #                 '公司缴费': float(re.sub('\s', '', dateB[28].text)),
    #                 '个人缴费': "-",
    #                 '缴费单位': re.sub('\s', '', dateB[4].text),
    #                 '单位划入帐户': float(re.sub('\s', '', dateB[38].text)),
    #                 '个人划入帐户': float(re.sub('\s', '', dateB[40].text))
    #             }
    #
    #             basedataB[yearB][monthB].append(modelB)
    #
    #
    #         # 五险状态
    #         social_type={
    #             '养老':re.sub('\s','',sEI[len(sEI)-1].findAll('td')[2].text),
    #             '医疗':re.sub('\s','',sEI[len(sHI)-1].findAll('td')[2].text),
    #             '失业':re.sub('\s','',sEI[len(sII)-1].findAll('td')[2].text),
    #             '工伤':re.sub('\s','',sEI[len(sCI)-1].findAll('td')[2].text),
    #             '生育':re.sub('\s','',sEI[len(sBI)-1].findAll('td')[2].text)
    #         }
    #
    #         #  个人基本信息
    #         # 缴费时长
    #         moneyCount=[len(sEI),len(sHI),len(sII),len(sCI),len(sBI)]
    #
    #         self.result_data['baseInfo'] = {
    #             '姓名': data[0].findAll('td')[1].text,
    #             '身份证号': data[1].findAll('td')[1].text,
    #             '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
    #             '城市名称': '厦门',
    #             '城市编号': '350200',
    #             '缴费时长': max(moneyCount),
    #             '最近缴费时间': re.sub('\s','',sEI[len(sEI)-1].findAll("td")[3].text),
    #             '开始缴费时间': re.sub('\s','',sEI[0].findAll("td")[3].text),
    #             '个人养老累计缴费': peroldTotal,
    #             '个人医疗累计缴费': permedicalTotal,
    #             '五险状态': social_type,
    #             '状态': self._convert_type(data[3].findAll('td')[1].text.replace('\r', '').replace('\n', '').replace('\t', '').strip()),
    #             '工作状态': data[8].findAll('td')[1].text,
    #             '社会保障卡卡号': data[2].findAll('td')[1].text,
    #         }
    #
    #         self.result['identity'] = {
    #             "task_name": "厦门",
    #             "target_name": data[0].findAll('td')[1].text,
    #             "target_id": self.result_meta['idCard'],
    #             "status": self._convert_type(data[3].findAll('td')[1].text.replace('\r', '').replace('\n', '').replace('\t', '').strip())
    #         }
    #
    #         return
    #     except InvalidConditionError as e:
    #         raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task(SessionData()))
    client.run()

    # 371402199708176125  1314.bing

