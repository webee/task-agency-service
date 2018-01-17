# cff---长沙--湖南省省会   公积金信息

import time
import requests
from bs4 import BeautifulSoup
import re
import json

from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError, InvalidConditionError, \
    PreconditionNotSatisfiedError
from services.commons import AbsFetchTask

LOGIN_URL = r"http://www.csgjj.com.cn:8001/login.do"
VC_URL=r"http://www.csgjj.com.cn:8001/CaptchaImg"
Detail_URL="http://www.csgjj.com.cn:8001/per/queryPerDeposit!queryPerByYear.do"


class Task(AbsFetchTask):
    task_info = dict(
        city_name="长沙",
        help="""
            <li>您可以登录中心新网厅个人版重新注册，也可以通过手机APP或微信公众号重新注册</li>
            <li>为保证信息安全，注册时需验证您在中心预留的手机号码，如果您没有预留或需要更改预留手机号码，可以通过本单位住房公积金专管员所使用的网厅单位版实时申报，也可以携带本人身份证原件到各管理部柜台申报</li>
            """,

        developers=[{'name': '程菲菲', 'email': 'feifei_cheng@chinahrs.net'}]
    )

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.79 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.csgjj.com.cn:8001',
        }


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
        assert '身份证号' in params, '缺少身份证号'
        #assert '账户名' in params, '缺少账户名'
        assert '密码' in params, '缺少密码'
        # other check
        身份证号 = params['身份证号']
        #账户名 = params['账户名']
        密码 = params['密码']

        if len(身份证号) == 0:
            raise InvalidParamsError('身份证号为空，请输入身份证号')
        elif len(身份证号) < 15:
            raise InvalidParamsError('身份证号不正确，请重新输入')

        # if len(账户名) == 0:
        #     raise InvalidParamsError('账户名为空，请输入账户名')

        if len(密码) == 0:
            raise InvalidParamsError('密码为空，请输入密码！')
        elif len(密码) < 6:
            raise InvalidParamsError('密码不正确，请重新输入！')

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '身份证号' not in params:
                params['身份证号'] = meta.get('身份证号')
            # if '账户名' not in params:
            #     params['账户名'] = meta.get('账户名')
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
            # elif pr['key'] == '账户名' and '账户名' in meta:
            #     continue
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

                # id_num = params.get("身份证号")
                # account_pass = params.get("密码")
                # #vc = params.get("vc")
                #
                # data={
                #     'username': id_num,
                #     'password': account_pass,
                #     'loginType': 4,
                #     'vertcode':'',
                #     'bsr':'chrome / 61.0.3163.79',
                #     'vertype': 1
                # }
                # resp=self.s.post(LOGIN_URL,data)
                # if 'html' not in resp.text:
                #     raise InvalidParamsError("登录失败，用户名或密码错误！")
                # else:
                #     # 保存到meta
                #     self.result_key = id_num
                #     self.result_meta['身份证号'] = id_num
                #     self.result_meta['密码'] = account_pass
                #     return

                raise TaskNotImplementedError('查询服务维护中')

            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input', placeholder='身份证号/手机号码/个人账号', value=params.get('身份证号', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            #dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch(self):
        try:
            self.result_data['baseInfo'] = {}
            self.result_data['detail'] = {"data": {}}
            self.result_data['companyList'] = []
            resps=self.s.get("http://www.csgjj.com.cn:8001/per/queryPerInfo.do")
            soup=BeautifulSoup(resps.content,'html.parser')

            # 基本信息
            if(soup.find('table',{'id':'user_info_table'})!=None):
                perData=soup.find('table',{'id':'user_info_table'}).findAll('tr')
                perDetal=soup.find('div',{'class':'glinfo'}).findAll('div')

                status=''
                restatus=perData[9].findAll('td')[1].text
                if '正常' in restatus:
                    status='缴存'
                else:
                    status='封存'

                # 个人基本信息
                self.result_data['baseInfo'] = {
                    '姓名': perDetal[1].text,
                    '证件号': perDetal[3].text,
                    '证件类型': '身份证',
                    '个人账号': perDetal[5].text,
                    '公积金帐号': '',
                    '缴存基数':perData[4].findAll('td')[1].text.replace('元',''),
                    '单位缴存比例': perData[5].find('span',{'id':'percorpscale'}).text,
                    '个人缴存比例': perData[5].find('span',{'id':'perperscale'}).text+'%',
                    '单位月缴存额':perData[7].find('span',{'id':'corpdepmny'}).text ,
                    '个人月缴存额': perData[7].find('span',{'id':'perdepmny'}).text,
                    '开户日期':perData[10].findAll('td')[1].text.replace('年','-').replace('月','-').replace('日',''),
                    '手机号': perDetal[7].text,

                    '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                    '城市名称': '长沙市',
                    '城市编号': '430100',

                    '最近汇款日期': '',
                    '最近汇款金额': '',
                    '累计汇款次数': 0,
                }

                # companyList
                self.result_data['companyList'].append({
                    "单位名称": perData[0].findAll('td')[1].find('span',{'id':'corpcode2'}).text,
                    "单位登记号": perData[1].findAll('td')[1].text,
                    "所属管理部编号": "",
                    "所属管理部名称": perData[2].findAll('td')[1].text,
                    "当前余额": perData[8].findAll('td')[1].text.replace('元',''),
                    "帐户状态": status,
                    "当年缴存金额": "",
                    "当年提取金额": "",
                    "上年结转余额": "",
                    "最后业务日期": perData[11].findAll('td')[1].text.replace('年','-').replace('月',''),
                    "转出金额": ""
                })

                # identity 信息
                self.result['identity'] = {
                    "task_name": "长沙",
                    "target_name": perDetal[1].text,
                    "target_id": perDetal[3].text,
                    "status": status
                }


            # 缴费明细
            dateinfo={
                'dto["startdate"]':'',  # 2017-01-01
                'dto["enddate"]':time.strftime('%Y-%m-%d',time.localtime()),
                'gridInfo["dataList_limit"]':100,
                'gridInfo["dataList_start"]':0
            }

            reDe=self.s.post(Detail_URL,dateinfo)
            detailInfo=json.loads(reDe.text)

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        return True


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task(SessionData()))
    client.run()

    #  622922198401181019   aaa123456


