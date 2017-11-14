# cff---长沙--湖南省省会   公积金信息

import time
import requests
from bs4 import BeautifulSoup

from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError, InvalidConditionError, \
    PreconditionNotSatisfiedError
from services.commons import AbsFetchTask

MAIN_URL = r'http://www.xzgjj.com:7001/wscx/zfbzgl/gjjxxcx/gjjxx_cx.jsp?'
LOGIN_URL = r"http://www.xzgjj.com:7001/wscx/"
VC_URL = r""
Detail_URL=r"http://www.xzgjj.com:7001/wscx/zfbzgl/gjjmxcx/gjjmx_cx.jsp?"


class Task(AbsFetchTask):
    task_info = dict(
        city_name="湖南省",
        help="""
            <li>初始化密码111111,请注意修改密码.</li>
            """
    )

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.79 Safari/537.36',
            'Accept-Encoding':'gzip, deflate',
            'Host': 'www.xzgjj.com:7001',
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


    def _short_type(self,keyname):
        res=""
        if('汇缴' in keyname):
            res="汇缴公积金"
        elif ('补缴' in keyname):
            res = "补缴公积金"
        elif('提取' in keyname):
            res="部分提取"
        else:
            res=keyname
        return res


    def _unit_login(self, params=None):
        err_msg = None
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                self.result_data['baseInfo'] = {}
                self.result_data['detail'] = {}
                self.result_data['companyList'] = []

                id_num = params.get("身份证号")
                account_pass = params.get("密码")

                data={
                    'password':account_pass,
                    'sfzh':id_num,
                    'dbname':'gjjmx9',
                    'dlfs':'0'
                }

                resp = self.s.post("http://www.xzgjj.com:7001/wscx/zfbzgl/zfbzsq/login_hidden.jsp?cxyd=%B5%B1%C7%B0%C4%EA%B6%C8", data=data)
                if(resp.text.find('alert')>0):
                    raise InvalidParamsError("登录失败，请核对用户名或者密码！")

                self.result_key = id_num
                self.result_meta['身份证号'] = id_num
                self.result_meta['密码'] = account_pass

                # 个人基本信息
                rsdata_url=resp.text.split('?')[1].split(';')[0].replace('"','')
                ss=self.s.get(MAIN_URL+rsdata_url)
                basedatass=BeautifulSoup(ss.text,'html.parser').find('table',{'class':'1'}).findAll('tr')

                self.result_data['baseInfo'] = {
                    '姓名':basedatass[0].findAll("td")[1].text.strip(),
                    '证件类型':'身份证',
                    '证件号':basedatass[1].findAll("td")[1].text.strip(),

                    '职工账号': basedatass[1].findAll("td")[3].text.strip(),
                    '开户日期':basedatass[3].findAll("td")[1].text.strip(),
                    '月缴基数':basedatass[4].findAll("td")[1].text.strip().replace('元','').replace(',',''),
                    '单位月缴额':basedatass[6].findAll("td")[1].text.strip().replace('元',''),
                    '个人月缴额':basedatass[7].findAll("td")[1].text.strip().replace('元',''),
                    '缴至年月':basedatass[10].findAll("td")[1].text.strip(),

                    '更新时间': time.strftime("%Y-%m-%d", time.localtime()),
                    '城市名称': '湖南省',
                    '城市编号': '430100'
                }

                self.result_data['companyList'].append({
                    "单位名称": basedatass[2].findAll("td")[1].text.strip(),
                    "单位登记号": "",
                    "所属管理部编号": "",
                    "所属管理部名称": "",
                    "当前余额": float(basedatass[9].findAll("td")[3].text.strip().replace('元','')),
                    "帐户状态": basedatass[3].findAll("td")[3].text.strip(),
                    "当年缴存金额": float(basedatass[8].findAll("td")[1].text.strip().replace('元','')),
                    "当年提取金额": float(basedatass[7].findAll("td")[3].text.strip().replace('元','')),
                    "上年结转余额": float(basedatass[5].findAll("td")[3].text.strip().replace('元','')),
                    "最后业务日期": basedatass[10].findAll("td")[1].text.strip(),
                    "转出金额": ""
                })


                # 公积金明细
                self.result_data['detail'] = {"data": {}}
                baseDetail = self.result_data["detail"]["data"]
                model = {}
                resTr=[]
                zgzh=rsdata_url.split('&')[0].split('=')[1]
                sfzh=rsdata_url.split('&')[1].split('=')[1]
                dwbm=rsdata_url.split('&')[3].split('=')[1]
                paramurl="zgzh="+zgzh+"&sfzh="+sfzh+"&dwbm="+dwbm+""
                times=time.strftime("%Y",time.localtime())

                # 往年历史查询
                for tm in range(0,10):
                    detailURL = self.s.get(Detail_URL + paramurl + "&cxydtwo=" + str(int(times) - (tm+1)) + "-" + str(int(times)-tm) + "")
                    trs = BeautifulSoup(detailURL.text, 'html.parser').find('table', {'class': '1'}).findAll("tr")
                    resTr.append(trs)

                # 当前年度信息查询
                detailURLs = self.s.get(Detail_URL + paramurl + "&cxydtwo=%B5%B1%C7%B0%C4%EA%B6%C8")
                trs2 = BeautifulSoup(detailURLs.text, 'html.parser').find('table', {'class': '1'}).findAll("tr")
                resTr.append(trs2)

                for ab in range(len(resTr)):
                    for tr in range(len(resTr[ab])):
                        if (resTr[ab][tr].findAll("td")[0].text!="日期" and resTr[ab][tr].findAll("td")[0].text!=''):
                            tds = resTr[ab][tr].findAll("td")
                            years = tds[0].text[0:4]
                            months = tds[0].text[5:7]
                            model = {
                                '时间': tds[0].text,
                                '类型': self._short_type(tds[5].text),
                                '汇缴年月': '',
                                '收入': float(tds[2].text.replace(',', '')),
                                '支出': float(tds[1].text.replace(',', '')),
                                '余额': float(tds[3].text.replace(',', '')),
                                '单位名称': basedatass[2].findAll("td")[1].text.strip()
                            }
                            baseDetail.setdefault(years, {})
                            baseDetail[years].setdefault(months, [])
                            baseDetail[years][months].append(model)


                # indentity
                    self.result['identity']={
                    "task_name": "湖南",
                    "target_name": basedatass[0].findAll("td")[1].text.strip(),
                    "target_id": self.result_meta['身份证号'],
                    "status": basedatass[3].findAll("td")[3].text.strip()
                }


                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input'),
            dict(key='密码', name='密码', cls='input'),
        ], err_msg)

    def _unit_fetch(self):
        try:

            return
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        return True


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task(SessionData()))
    client.run()

    # 431102199307239375  111111
