# cff---宁波--浙江省   公积金信息

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

MAIN_URL = r'http://www.nbgjj.com/GJJQuery?'
LOGIN_URL = r"http://www.nbgjj.com/perlogin.jhtml"
VC_URL = r"http://www.nbgjj.com/website/trans/ValidateImg"


class Task(AbsFetchTask):
    task_info = dict(
        city_name="宁波",
        help="""
            <li>个人公积金查询初始密码为“111111”，如果您是首次登录，需要将初始密码修改为新的密码以确保账户安全。</li>
            <li>北仑、奉化、宁海、镇海、象山、慈溪、余姚、鄞州系统已接入宁波市本级系统，可在上述页面直接查询住房公积金个人帐户信息，查询规则与宁波市本级一致。</li>
            """
    )

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.79 Safari/537.36',
            'Accept-Encoding':'gzip, deflate',
            'Host': 'www.nbgjj.com',
        }

    def _prepare(self, data=None):
        super()._prepare()
        self.result_data['baseInfo']={}
        self.result_data['detail'] = {}
        self.result_data['companyList']={}

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
        assert '账号' in params, '缺少账号'
        assert '密码' in params, '缺少密码'
        # other check
        账号 = params['账号']
        密码 = params['密码']

        if len(账号) == 0:
            raise InvalidParamsError('账号为空，请输入账号')

        if len(密码) == 0:
            raise InvalidParamsError('密码为空，请输入密码！')
        elif len(密码) < 6:
            raise InvalidParamsError('密码不正确，请重新输入！')

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '账号' not in params:
                params['账号'] = meta.get('账号')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '账号' and '账号' in meta:
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
                id_num = params.get("账号")
                account_pass = params.get("密码")
                vc=params.get("vc")

                if(len(id_num)==15 or len(id_num)==18):
                    data = {
                        'tranCode': '142501',
                        'task': '',
                        'accnum': '',
                        'certinum': id_num,
                        'pwd': account_pass,
                        'verify': vc,
                    }
                    ltype="身份证号"
                elif(len(id_num)<=12):
                    data = {
                        'tranCode': '142501',
                        'task': '',
                        'accnum': id_num,
                        'certinum': '',
                        'pwd': account_pass,
                        'verify': vc,
                    }
                    ltype="公积金账号"

                resp=self.s.post("http://www.nbgjj.com/GJJQuery",data=data)
                if 'msg' in resp.text:         # 判断是否登录成功
                    raise InvalidParamsError(json.loads(resp.text)['msg'])


                # 个人基本信息
                accnum=resp.cookies['gjjaccnum']
                res=self.s.get(MAIN_URL+"tranCode=142503&task=&accnum="+accnum)
                resdata=json.loads(res.text)
                self.result_data['baseInfo'] = {
                    '姓名':resdata['accname'],
                    '证件号':resdata['certinum'],
                    '证件类型':'身份证',
                    '公积金账号':resdata['accnum'],
                    '缴存基数':resdata['basenum'],
                    '开户日期':resdata['begdate'],
                    '更新时间':time.strftime("%Y-%m-%d",time.localtime()),
                    '城市名称':'宁波市',
                    '城市编号':'330200'
                }

                # 公司信息
                self.result_data['companyList'] = {
                    "单位名称": resdata['unitaccname'],
                    "单位登记号": "",
                    "所属管理部编号": "",
                    "所属管理部名称": "",
                    "当前余额": resdata['amt'],
                    "帐户状态": resdata['freeuse1'],
                    "当年缴存金额": "",
                    "当年提取金额": "",
                    "上年结转余额": "",
                    "最后业务日期": resdata['lpaym'],
                    "转出金额": ""
                }

                # identity 信息
                self.result['identity']={
                    "task_name": "宁波",
                    "target_name": resdata['accname'],
                    "target_id": id_num,
                    "status": resdata['freeuse1']
                }

                # 缴费明细
                starttime=str(datetime.datetime.now()-datetime.timedelta(days=365*3))[0:10]    # 开始时间
                endtime=str(datetime.datetime.now())[0:10]                                      # 结束时间
                detailurl=self.s.get(MAIN_URL+"tranCode=142504&task=ftp&indiacctype=1&accnum="+accnum+"&begdate="+starttime+"&enddate="+endtime)
                detailData=json.loads(detailurl.text)
                self.result_data['detail'] = {"data": {}}
                baseDetail = self.result_data["detail"]["data"]
                model = {}
                for aa in range(len(detailData)):
                    years=detailData[aa]["trandate"][0:4]
                    months=detailData[aa]["trandate"][5:7]
                    model={
                        '时间':detailData[aa]["trandate"],
                        '类型':detailData[aa]["ywtype"].strip(),
                        '汇缴年月': detailData[aa]["trandate"],
                        '收入':detailData[aa]["amt"],
                        '支出':"-",
                        '余额': detailData[aa]["bal"],
                        '单位名称':detailData[aa]["unitaccname"].strip()
                    }

                    baseDetail.setdefault(years, {})
                    baseDetail[years].setdefault(months, [])
                    baseDetail[years][months].append(model)


                self.result_key = id_num
                self.result_meta[ltype] =id_num
                self.result_meta['密码']=account_pass

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='账号', name='账号', cls='input'),
            dict(key='密码', name='密码', cls='input'),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch(self):
        try:

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        resp = self.s.get(VC_URL)
        return dict(cls='data:image', content=resp.content, content_type=resp.headers['Content-Type'])


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task(SessionData()))
    client.run()

    # 330227198208247314  111111

    # 0122831927 111111
