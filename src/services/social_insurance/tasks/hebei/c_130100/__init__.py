# cff---河北石家庄--社保账号采集

import time
import requests
import json
from bs4 import BeautifulSoup
import demjson

from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError, InvalidConditionError, \
    PreconditionNotSatisfiedError
from services.commons import AbsFetchTask


LoginUrl="http://grsbcx.sjz12333.gov.cn/login.do?method=begin"
VC_URL="http://grsbcx.sjz12333.gov.cn/jcaptcha"
Main_URL="http://grsbcx.sjz12333.gov.cn/ria_grid.do?method=query"
Half_URL="http://grsbcx.sjz12333.gov.cn/Report-ResultAction.do?linage=-1&encode=false&newReport=true&reportId="


class Task(AbsFetchTask):
    task_info = dict(
        city_name="石家庄",
        help="""
            <li>1.社会保障号为公民身份证号码</li>
            <li>2.请您使用社会保障卡服务密码或医保卡密码进行查询</li>
            """,

        developers=[{'name': '程菲菲', 'email': 'feifei_cheng@chinahrs.net'}]
    )

    def _get_common_headers(self):
        return {
            'User-Agent':'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.79 Safari/537.36',
            'Accept-Encoding':'gzip, deflate',
            'Host':'grsbcx.sjz12333.gov.cn',
            'Upgrade-Insecure-Requests':'1',
            'Accept-Language':'zh-CN,zh;q=0.8,en;q=0.6',
            'X-Requested-With':'XMLHttpRequest',
            #'Content-Type':'multipart/form-data'
        }


    def _new_vc(self):
        resp = self.s.get(VC_URL)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '社保号' in params, '缺少社保号'
        assert '密码' in params, '缺少密码'
        # other check
        证件号 = params['社保号']
        密码 = params['密码']

        if len(证件号) == 0:
            raise InvalidParamsError('社保号为空，请输入社保号！')
        elif len(证件号)!=15 and len(证件号)!=18:
            raise InvalidParamsError('社保号不正确，请重新输入！')

        if len(密码) == 0:
            raise InvalidParamsError('密码为空，请输入密码！')
        elif len(密码) < 6:
            raise InvalidParamsError('密码不正确，请重新输入！')

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '社保号' not in params:
                params['社保号'] = meta.get('社保号')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '社保号' and '社保号' in meta:
                continue
            elif pr['key'] == '密码' and '密码' in meta:
                continue
            res.append(pr)
        return res


    def _unit_login(self, params=None):
        err_msg = None
        if params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params.get("社保号")
                account_pass = params.get("密码")
                vc = params.get("vc")

                data = {
                    'Method':'P',
                    'pid':'1373174326875',  #  str(time.time()*1000)[0:13]
                    'j_username': id_num,
                    'j_password': account_pass,
                    'jcaptcha_response': vc
                }
                resp = self.s.post("http://grsbcx.sjz12333.gov.cn/j_unieap_security_check.do", data=data)

                if(resp.url!='http://grsbcx.sjz12333.gov.cn/enterapp.do?method=begin&name=/si&welcome=/si/pages/index.jsp'):
                    raise InvalidParamsError("登录失败，请重新登录！")
                else:
                    self.result_key = id_num
                    self.result_meta['社保号'] =id_num
                    self.result_meta['密码']=account_pass
                    return
                #raise TaskNotImplementedError('查询服务维护中')

            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='社保号', name='社保号', cls='input',value=params.get('社保号', '')),
            dict(key='密码', name='密码', cls='input:password',value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)


    def _unit_fetch(self):
        try:
            self.result_data['baseInfo'] = {}
            times=str(int(time.strftime("%Y",time.localtime()))-1)
            icard=self.result_meta['社保号']
            res=self.s.get(Half_URL+'a5c27955-1489-4f81-9781-18ee9ace9ec3&AS_AAE001='+times+'&AS_AAE135='+icard)
            soup=BeautifulSoup(res.text,'html.parser').findAll('tr')

            redetail=self.s.get(Half_URL+'da89388c-5c59-452f-b2bd-8f54effeda33&AS_AAE001='+times+'&AS_AAE135='+icard)
            soupDetail=BeautifulSoup(redetail.text,'html.parser').findAll('tr')

            # 明细
            datas='{header:{"code": -100, "message": {"title": "", "detail": ""}},body:{dataStores:{contentStore:{rowSet:{"primary":[],"filter":[],"delete":[]},name:"contentStore",pageNumber:1,pageSize:2147483647,recordCount:0,statementName:"si.treatment.ggfw.content",attributes:{"AAC002": ["'+icard+'", "12"],}},xzStore:{rowSet:{"primary":[],"filter":[],"delete":[]},name:"xzStore",pageNumber:1,pageSize:2147483647,recordCount:0,statementName:"si.treatment.ggfw.xzxx",attributes:{"AAC002": ["'+icard+'", "12"],}},sbkxxStore:{rowSet:{"primary":[],"filter":[],"delete":[]},name:"sbkxxStore",pageNumber:1,pageSize:2147483647,recordCount:0,statementName:"si.treatment.ggfw.sbkxx",attributes:{"AAC002": ["'+icard+'", "12"],}},grqyjlStore:{rowSet:{"primary":[],"filter":[],"delete":[]},name:"grqyjlStore",pageNumber:1,pageSize:2147483647,recordCount:0,statementName:"si.treatment.ggfw.grqyjlyj",attributes:{"AAE135": ["'+icard+'", "12"]}}},parameters:{"BUSINESS_ID": "UCI314", "BUSINESS_REQUEST_ID": "REQ-IC-Q-098-60", "CUSTOMVPDPARA": "", "PAGE_ID": ""}}}'
            totalresp=self.s.post(Main_URL,datas)
            totalinfo=demjson.decode(totalresp.text)['body']['dataStores']['xzStore']['rowSet']['primary']

            # 养老保险明细
            #
            self.result['data']["old_age"] = {"data": {}}
            basedataE = self.result['data']["old_age"]["data"]
            modelE = {}
            EICount= soupDetail[18].findAll('td')[0].text
            EIMoney=soupDetail[18].findAll('td')[1].text.replace(',','')
            EIType=totalinfo[0]['AAC008']

            # 医疗保险明细
            #
            self.result['data']["medical_care"] = {"data": {}}
            basedataH = self.result['data']["medical_care"]["data"]
            modelH = {}
            HIType = totalinfo[1]['AAC008']
            HCompany=totalinfo[1]['AAB004']
            sanxian='{header:{"code": -100, "message": {"title": "", "detail": ""}},body:{dataStores:{searchStore:{rowSet:{"primary":[],"filter":[],"delete":[]},name:"searchStore",pageNumber:1,pageSize:20,recordCount:0,context:{"BUSINESS_ID": "UOA017", "BUSINESS_REQUEST_ID": "REQ-OA-M-013-01", "CUSTOMVPDPARA": ""},statementName:"si.treatment.ggfw.yljf",attributes:{"AAC002": ["'+icard+'", "12"],}}},parameters:{"BUSINESS_ID": "UOA017", "BUSINESS_REQUEST_ID": "REQ-OA-M-013-01", "CUSTOMVPDPARA": "", "PAGE_ID": ""}}}'
            sanxianresp=self.s.post(Main_URL,sanxian)
            sanDetail=demjson.decode(sanxianresp.text)['body']['dataStores']['searchStore']['rowSet']['primary']
            for k in range(len(sanDetail)):
                if(sanDetail[k]['AC43_AAE140']=="城镇职工基本医疗保险"):
                    yearH = sanDetail[k]['AC43_AAE003'][0:4]
                    monthH = sanDetail[k]['AC43_AAE003'][4:6]
                    basedataH.setdefault(yearH, {})
                    basedataH[yearH].setdefault(monthH, [])

                    modelH = {
                        '缴费单位': HCompany,
                        '缴费类型': HIType,
                        '缴费时间': sanDetail[k]['AC43_AAE003'],
                        '缴费基数': sanDetail[k]['AC43_AAE018'],
                        '公司缴费': sanDetail[k]['AC43_AAE022'],
                        '个人缴费': sanDetail[k]['AC43_AAE021'],
                    }
                    basedataH[yearH][monthH].append(modelH)

            # 失业保险明细
            #
            self.result['data']["unemployment"] = {"data": {}}
            basedataI = self.result['data']["unemployment"]["data"]
            modelI = {}
            IIType = totalinfo[2]['AAC008']
            jsons='{header:{"code": -100, "message": {"title": "", "detail": ""}},body:{dataStores:{searchStore:{rowSet:{"primary":[],"filter":[],"delete":[]},name:"searchStore",pageNumber:1,pageSize:20,recordCount:0,context:{"BUSINESS_ID": "UOA017", "BUSINESS_REQUEST_ID": "REQ-OA-M-013-01", "CUSTOMVPDPARA": ""},statementName:"si.treatment.ggfw.syjf",attributes:{"AAC002": ["'+icard+'", "12"],}}},parameters:{"BUSINESS_ID": "UOA017", "BUSINESS_REQUEST_ID": "REQ-OA-M-013-01", "CUSTOMVPDPARA": "", "PAGE_ID": ""}}}'
            IIresp=self.s.post(Main_URL,jsons)
            iiDetail=demjson.decode(IIresp.text)['body']['dataStores']['searchStore']['rowSet']['primary']
            for b in range(len(iiDetail)):
                yearI = iiDetail[b]['AC43_AAE003'][0:4]
                monthI = iiDetail[b]['AC43_AAE003'][4:6]
                basedataI.setdefault(yearI, {})
                basedataI[yearI].setdefault(monthI, [])

                modelI = {
                    '缴费单位': totalinfo[2]['AAB004'],
                    '缴费类型': IIType,
                    '缴费时间': iiDetail[b]['AC43_AAE003'],
                    '缴费基数': iiDetail[b]['AC43_AAE018'],
                    '公司缴费': iiDetail[b]['AC43_AAE022'],
                    '个人缴费': iiDetail[b]['AC43_AAE021'],
                }
                basedataI[yearI][monthI].append(modelI)

            # 工伤保险明细
            #
            self.result['data']["injuries"] = {"data": {}}
            basedataC = self.result['data']["injuries"]["data"]
            modelC = {}


            # 生育保险明细
            #
            self.result['data']["maternity"] = {"data": {}}
            basedataB = self.result['data']["maternity"]["data"]
            modelB = {}
            BIType = totalinfo[3]['AAC008']
            for p in range(len(sanDetail)):
                if (sanDetail[p]['AC43_AAE140'] == "生育保险"):
                    yearB = sanDetail[p]['AC43_AAE003'][0:4]
                    monthB = sanDetail[p]['AC43_AAE003'][4:6]
                    basedataB.setdefault(yearB, {})
                    basedataB[yearB].setdefault(monthB, [])

                    modelB = {
                        '缴费单位': HCompany,
                        '缴费类型': BIType,
                        '缴费时间': sanDetail[p]['AC43_AAE003'],
                        '缴费基数': sanDetail[p]['AC43_AAE018'],
                        '公司缴费': sanDetail[p]['AC43_AAE022'],
                        '个人缴费': '',
                    }
                    basedataB[yearB][monthB].append(modelB)


            # 大病保险明细
            #
            self.result['data']["serious_illness"] = {"data": {}}
            basedataP=self.result['data']["serious_illness"]["data"]
            modelP={}
            for q in range(len(sanDetail)):
                if (sanDetail[q]['AC43_AAE140'] == "大额医疗费用补助"):
                    yearP=sanDetail[q]['AC43_AAE003'][0:4]
                    monthP=sanDetail[q]['AC43_AAE003'][4:6]
                    basedataP.setdefault(yearP, {})
                    basedataP[yearP].setdefault(monthP, [])

                    modelP={
                        '缴费单位':HCompany,
                        '缴费类型':HIType,
                        '缴费时间':sanDetail[q]['AC43_AAE003'],
                        '缴费基数':sanDetail[q]['AC43_AAE018'],
                        '公司缴费':sanDetail[q]['AC43_AAE022'],
                        '个人缴费':''
                    }
                    basedataP[yearP][monthP].append(modelP)


            # 个人基本信息
            status = ""
            if soup[10].findAll('td')[1].text != '':
                wuxiantype={
                    '养老':EIType,
                    '医疗':HIType,
                    '失业':IIType,
                    '生育':BIType
                }
                if(EIType=="正常参保"):
                    status='正常'
                else:
                    status='停缴'

                self.result_data['baseInfo'] = {
                    '姓名': soup[10].findAll('td')[1].text,
                    '身份证号': soup[10].findAll('td')[5].text,
                    '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                    '城市名称': '石家庄',
                    '城市编号': '130100',
                    '缴费时长': EICount,
                    '最近缴费时间': sanDetail[0]['AC43_AAE003'],
                    '开始缴费时间': sanDetail[len(sanDetail)-1]['AC43_AAE003'],
                    '个人养老累计缴费': EIMoney,
                    '个人医疗累计缴费': soup[40].findAll('td')[4].text,
                    '五险状态': wuxiantype,
                    '账户状态': status,

                    '个人编号': soup[11].findAll('td')[1].text,
                    '单位编号': soup[11].findAll('td')[3].text,
                    '开户日期': soup[12].findAll('td')[1].text,
                }

            # identity
            self.result['identity'] = {
                "task_name": "石家庄",
                "target_name": soup[10].findAll('td')[1].text,
                "target_id": self.result_meta['社保号'],
                "status": status
            }

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task(SessionData()))
    client.run()

    # 130105198609142416   777129
