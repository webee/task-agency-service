# 上海  社保信息
from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError, InvalidConditionError, \
    PreconditionNotSatisfiedError
from services.commons import AbsFetchTask
import time
from bs4 import BeautifulSoup

LOGIN_URL = "http://www.12333sh.gov.cn/sbsjb/wzb/129.jsp"
LOGIN_SUCCESS_URL = "http://www.12333sh.gov.cn/sbsjb/wzb/helpinfo.jsp?id=0"
VC_URL = "http://www.12333sh.gov.cn/sbsjb/wzb/Bmblist.jsp"


class Task(AbsFetchTask):
    task_info = dict(
        city_name="上海",
        help="""<li>用户名：输入公民身份证号码；</li>
        <li>密码：一般为6位数字；</li>
        <li>首次申请密码或遗忘网上登录密码，本人须携带有效身份证件至就近街道社区事务受理中心中就近社保分中心自助机具上申请办理。</li>
        """
    )

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.12333sh.gov.cn',
        }

    def _query(self, params: dict):
        """任务状态查询"""
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()
            # pass

    def _new_vc(self):
        resp = self.s.get(VC_URL)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '用户名' in params, '缺少用户名'
        assert '密码' in params, '缺少密码'
        # other check
        用户名 = params['用户名']
        密码 = params['密码']

        if len(用户名) == 0:
            raise InvalidParamsError('用户名为空，请输入用户名')
        elif len(用户名) < 4:
            raise InvalidParamsError('用户名不正确，请重新输入')

        if len(密码) == 0:
            raise InvalidParamsError('密码为空，请输入密码！')
        elif len(密码) < 6:
            raise InvalidParamsError('密码不正确，请重新输入！')

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '用户名' not in params:
                params['用户名'] = meta.get('用户名')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '用户名' and '用户名' in meta:
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
                self.result_key = params.get('用户名')

                id_num = params.get("用户名")
                account_pass = params.get("密码")
                vc = params.get("vc")

                data = {
                    'userid': id_num,
                    'userpw': account_pass,
                    'userjym': vc
                }
                resp = self.s.post("http://www.12333sh.gov.cn/sbsjb/wzb/dologin.jsp", data=data)
                # 检查是否登录成功
                if resp.status_code != 200:
                    raise InvalidParamsError("登录失败")

                if resp.url != LOGIN_SUCCESS_URL:
                    soup = BeautifulSoup(resp.content, 'html.parser')
                    spans = soup.select('tr > td > span')
                    err_msg = "登录失败"
                    if spans and len(spans) > 0:
                        err_msg = spans[0].text
                    raise InvalidParamsError(err_msg)

                # 保存到meta
                self.result_meta['用户名'] = params.get('用户名')
                self.result_meta['密码'] = params.get('密码')
                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='用户名', name='用户名', cls='input', placeholder='请输入身份证号', value=params.get('用户名', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError

            resp = self.s.get("http://www.12333sh.gov.cn/sbsjb/wzb/sbsjbcx.jsp")
            soup = BeautifulSoup(resp.content, 'html.parser')
            years = soup.find('xml', {'id': 'dataisxxb_sum3'}).findAll("jsjs")

            self.result['data']['baseInfo'] = {
                '姓名': soup.find('xm').text,
                '身份证号': self.result_meta['用户名'],
                '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                '城市名称': '上海市',
                '城市编号': '310100',
                '缴费时长': soup.find('xml', {'id': 'dataisxxb_sum4'}).find('jsjs2').text,
                '最近缴费时间': years[len(years) - 1].find('jsjs1').text,
                '开始缴费时间': years[0].find('jsjs1').text,
                '个人养老累计缴费': soup.find('xml', {'id': 'dataisxxb_sum4'}).find('jsjs3').text,
                '个人医疗累计缴费': ''
            }

            # 社保缴费明细
            # 养老
            self.result['data']['old_age'] = {
                "data": {}
            }
            dataBaseE = self.result['data']['old_age']["data"]
            modelE = {}

            details = soup.find('xml', {'id': 'dataisxxb_sum2'}).findAll("jsjs")
            dt = soup.findAll("jfdwinfo")

            for a in range(len(years)):
                yearE = details[a].find('jsjs1').text[0:4]
                monthE = details[a].find('jsjs1').text[4:6]

                dataBaseE.setdefault(yearE, {})
                dataBaseE[yearE].setdefault(monthE, [])

                modelE = {
                    '缴费时间': details[a].find('jsjs1').text,
                    '缴费单位': self._match_commapy(details[a].find('jsjs1').text, dt),
                    '缴费基数': details[a].find('jsjs3').text,
                    '缴费类型': '-',
                    '公司缴费': '-',
                    '个人缴费': details[a].find('jsjs4').text,
                    '实缴金额': self._match_money(details[a].find('jsjs1').text, years[a].find('jsjs1').text,
                                              years[a].find('jsjs3').text)
                }
                dataBaseE[yearE][monthE].append(modelE)

            # 医疗
            self.result['data']['medical_care'] = {
                "data": {}
            }
            dataBaseH = self.result['data']['medical_care']["data"]
            modelH = {}

            for b in range(len(details)):
                yearH = details[b].find('jsjs1').text[0:4]
                monthH = details[b].find('jsjs1').text[4:6]

                dataBaseH.setdefault(yearH, {})
                dataBaseH[yearH].setdefault(monthH, [])

                modelH = {
                    '缴费时间': details[b].find('jsjs1').text,
                    '缴费单位': self._match_commapy(details[b].find('jsjs1').text, dt),
                    '缴费基数': details[b].find('jsjs3').text,
                    '缴费类型': '-',
                    '公司缴费': '-',
                    '个人缴费': details[b].find('jsjs6').text,
                }
                dataBaseH[yearH][monthH].append(modelH)

            # 失业
            self.result['data']['unemployment'] = {
                "data": {}
            }
            dataBaseI = self.result['data']['unemployment']["data"]
            modelI = {}

            for c in range(len(details)):
                yearI = details[c].find('jsjs1').text[0:4]
                monthI = details[c].find('jsjs1').text[4:6]

                dataBaseI.setdefault(yearI, {})
                dataBaseI[yearI].setdefault(monthI, [])

                modelI = {
                    '缴费时间': details[c].find('jsjs1').text,
                    '缴费单位': self._match_commapy(details[c].find('jsjs1').text, dt),
                    '缴费基数': details[c].find('jsjs3').text,
                    '缴费类型': '-',
                    '公司缴费': '-',
                    '个人缴费': details[c].find('jsjs8').text,
                }
                dataBaseI[yearI][monthI].append(modelI)

            # 工伤
            self.result['data']['injuries'] = {
                "data": {
                    # '缴费时间': '-',
                    # '缴费单位': '-',
                    # '缴费基数': '-',
                    # '缴费类型': '-',
                    # '公司缴费': '-',
                    # '个人缴费': '-',
                }
            }

            # 生育
            self.result['data']['maternity'] = {
                "data": {}
            }

            self.result['identity'] = {
                "task_name": "上海",
                "target_name": soup.find('xm').text,
                "target_id": self.result_meta['用户名'],
                "status": ""
            }

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _match_money(self, dtime1, dtime2, fmoney):
        if (dtime1 == dtime2):
            return fmoney
        else:
            return ""

    def _match_commapy(self, dtime, dt):
        rescom = ""
        for tr in range(len(dt)):
            trd = dt[tr].find('jfsj').text.split('-')
            if (trd[0] <= dtime <= trd[1]):
                rescom = dt[tr].find('jfdw').text

        return rescom


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task(SessionData()))
    client.run()

    # 321322199001067241  123456       5002931643   123456
