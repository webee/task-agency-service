#烟台社保查询：
#地址：http://ytrsj.gov.cn:8081/hsp/logonDialog_withF.jsp
#账号：370302197811184822
#密码：qq781017
import hashlib
import random
import json
import io,sys
import base64
import datetime,time
from PIL import Image
from bs4 import BeautifulSoup
from services.webdriver import new_driver, DriverRequestsCoordinator, DriverType
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask

class value_is_number(object):
    """判断元素value是数字"""

    def __init__(self, locator):
        self.locator = locator

    def __call__(self, driver):
        element = driver.find_element(*self.locator)
        val = element.get_attribute('value')
        return val and val.isnumeric()


USER_AGENT = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0"

MAIN_URL = 'http://www.ytrsj.gov.cn:8081/hsp/logonDialog_withF.jsp'#mainFrame.jsp
LOGIN_URL = 'http://www.ytrsj.gov.cn:8081/hsp/logon.do'
VC_URL = 'http://www.ytrsj.gov.cn:8081/hsp/genAuthCode?_='
INFO_URL='http://www.ytrsj.gov.cn:8081/hsp/systemOSP.do'
YL_URL='http://www.ytrsj.gov.cn:8081/hsp/siAd.do'
YIL_URL='http://www.ytrsj.gov.cn:8081/hsp/siMedi.do'
GS_URL='http://www.ytrsj.gov.cn:8081/hsp/siHarm.do'
SHY_URL='http://www.ytrsj.gov.cn:8081/hsp/siBirth.do'
SY_URL='http://www.ytrsj.gov.cn:8081/hsp/siLost.do'


class Task(AbsFetchTask):
    # noinspection PyAttributeOutsideInit
    task_info = dict(
        city_name="烟台",
        help="""<li>如您未在社保网站查询过您的社保信息，请到烟台社保网上服务平台完成“注册”然后再登录。</li>
                <li>如您忘记密码，可使用注册时绑定的手机号或者电子邮箱进行密码找回；当不能通过手机和电子邮箱找回密码，需去社保机构现场重置密码。</li>""",
        developers=[{'name':'卜圆圆','email':'byy@qinqinxiaobao.com'}]
    )

    def _get_common_headers(self):
        return {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36'
        }

    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_name, self._unit_login)

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    def _prepare(self, data=None):
        super()._prepare(data)
        self.dsc = DriverRequestsCoordinator(s=self.s, create_driver=self._create_driver)

    def _create_driver(self):
        driver = new_driver(user_agent=USER_AGENT, js_re_ignore='/web\/ImageCheck.jpg/g')
        driver.get(MAIN_URL)
        return driver
    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '身份证号' in params, '缺少身份证号'
        assert '密码' in params,'缺少密码'
        assert 'vc' in params, '缺少验证码'
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
                #self._new_vc()
                #vc=input('验证码：')
                self._check_login_params(params)
                id_num = params['身份证号']
                password = params['密码']
                m = hashlib.md5()
                m.update(str(password).encode(encoding="utf-8"))
                pw = m.hexdigest()
                vc=params['vc']
                self._do_login(id_num, password, vc)

                # xmlstr='<?xml version = "1.0" encoding = "UTF-8"?><p><s tempmm = "'+password+'"/></p>'
                # resp = self.s.post(LOGIN_URL, data=dict(
                #     method='writeMM2Temp',
                #     _xmlString=xmlstr,
                #     _random=random.random()
                # ),headers={'Content-Type':'application/x-www-form-urlencoded;charset=UTF-8','X-Requested-With':'XMLHttpRequest'})
                # soup = BeautifulSoup(resp.content, 'html.parser')
                #
                # xmlstrs = '<?xml version="1.0" encoding="UTF-8"?><p> <s userid ="'+id_num+'"/> <s usermm="'+pw+'"/><s authcode="'+vc+'"/><s yxzjlx="A"/><s appversion="81002198533703667231184339811848228729"/><s dlfs=""/></p>'
                # resp = self.s.post(LOGIN_URL, data=dict(
                #     method='doLogon',
                #     _xmlString=xmlstrs,
                #     _random=random.random()
                # ), headers={'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                #            'X-Requested-With': 'XMLHttpRequest'})
                # soup = BeautifulSoup(resp.content, 'html.parser')
                errormsg = self.s.soup.text
                if errormsg:
                    if len(errormsg)>20:
                        dicts=eval(errormsg.replace('true','"true"'))
                        self.g.usersession_uuid=dicts['__usersession_uuid']
                    else:
                        raise InvalidParamsError(errormsg)

                    self.result_key=id_num
                    # 保存到meta
                    self.result_meta['身份证号'] = id_num
                    self.result_meta['密码'] = password

                    self.result_identity['task_name'] = '烟台'
                    self.result_identity['target_id'] = id_num

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)
        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input', value=params.get('身份证号', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)
    def _do_login(self, username, password, vc):
        """使用web driver模拟登录过程"""
        with self.dsc.get_driver_ctx() as driver:
            # 打开登录页
            driver.get(MAIN_URL)

            username_input = driver.find_element_by_xpath('//*[@id="yhmInput"]')
            password_input = driver.find_element_by_xpath('//*[@id="mmInput"]')
            vc_input = driver.find_element_by_xpath('//*[@id="authcode_result"]')
            submit_btn = driver.find_element_by_xpath('//*[@name="login_btn"]')

            # 用户名
            username_input.clear()
            username_input.send_keys(username)

            # 密码
            password_input.clear()
            password_input.send_keys(password)

            #验证码
            vc_input.clear()
            vc_input.send_keys(vc)
            Image.open(io.BytesIO(driver.get_screenshot_as_png())).show()
            # 提交
            driver.execute_script('onLogin("1.0.68","105","mainFrame.jsp?","1","")')
            #submit_btn.click()
            time.sleep(8)
            Image.open(io.BytesIO(driver.get_screenshot_as_png())).show()
            if driver.current_url != MAIN_URL:
                print('登录成功')
                # 保存登录后的页面内容供抓取单元解析使用
                login_page_html = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
                self.s.soup = BeautifulSoup(login_page_html, 'html.parser')


                # realname=soup.select('#xm')[0].text
            else:
                # FIXME: 尝试处理alert
                err_msg = '登录失败，请检查输入'
                alert = driver.switch_to.alert
                try:
                    err_msg = alert.text
                    # alert.accept()
                finally:
                    raise InvalidParamsError(err_msg)

    def _unit_fetch_name(self):
        try:
            data = self.result_data
            resp = self.s.post(INFO_URL, data=dict(
                    method='returnMain',
                    __usersession_uuid=self.g.usersession_uuid,
                    _random=random.random()
                ),headers={'Content-Type':'application/x-www-form-urlencoded;charset=UTF-8','X-Requested-With':'XMLHttpRequest'})
            soup = BeautifulSoup(resp.content, 'html.parser')
            arrcbsj=[soup.findAll('input')[6].attrs['value'],soup.findAll('input')[10].attrs['value'],soup.findAll('input')[14].attrs['value'],soup.findAll('input')[18].attrs['value'],soup.findAll('input')[22].attrs['value'],soup.findAll('input')[26].attrs['value']]
            baseinfoarr={'养老':'正常参保' if soup.findAll('input')[7].attrs['value']=='参保缴费' else '停缴',
                         '医疗': '正常参保' if soup.findAll('input')[11].attrs['value'] == '参保缴费' else '停缴',
                         '失业': '正常参保' if soup.findAll('input')[15].attrs['value'] == '参保缴费' else '停缴',
                         '工伤': '正常参保' if soup.findAll('input')[19].attrs['value'] == '参保缴费' else '停缴',
                         '生育': '正常参保' if soup.findAll('input')[23].attrs['value'] == '参保缴费' else '停缴',
                         soup.findAll('input')[25].attrs['value']: '正常参保' if soup.findAll('input')[27].attrs['value'] == '参保缴费' else '停缴'}
            data['baseInfo']={
                '姓名':soup.findAll('input')[0].attrs['value'],
                '身份证号': soup.findAll('input')[1].attrs['value'],
                '手机号码': soup.findAll('input')[2].attrs['value'],
                '家庭住址': soup.findAll('input')[3].attrs['value'],
                '通讯地址': soup.findAll('input')[4].attrs['value'],
                '五险状态': baseinfoarr,
                '开始缴费时间': min(arrcbsj),
                "更新时间": datetime.datetime.now().strftime('%Y-%m-%d'),
                '城市名称': '烟台',
                '城市编号': '370600'
            }
            self.result_identity['target_name'] = soup.findAll('input')[0].attrs['value']
            idtstatus='停缴'
            if '正常参保' in baseinfoarr.values():
                idtstatus='正常参保'
            self.result_identity['status'] = idtstatus

            #养老
            resp = self.s.post(YL_URL, data=dict(
                method='queryAgedPayHis',
                __usersession_uuid=self.g.usersession_uuid,
                _random=random.random()
            ), headers={'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                        'X-Requested-With': 'XMLHttpRequest'})
            soup = BeautifulSoup(resp.content, 'html.parser')
            spantext = soup.findAll('span')[1].text.split('，')
            data['baseInfo']['缴费时长']=int(spantext[0].replace('共缴费','').replace('个月',''))
            data['baseInfo']['最近缴费时间'] = spantext[3].replace('缴费年月为', '').replace('。','')
            #data['baseInfo']['开始缴费时间'] = spantext[2].replace('最早缴费年月为', '')
            selecttext=soup.findAll('option')
            ylsum=0.00
            for i in range(1,len(selecttext)):
                print(selecttext[i].text)

                self.result_data['old_age'] = {}
                self.result_data['old_age']['data'] = {}
                years = ''
                months = ''
                trinfo=soup.findAll('table')[1]
                for tr in trinfo.findAll('tr'):
                    arr = []
                    cell = [i.text for i in tr.find_all('td')]
                    if cell[0]=='':
                        cell=[i.attrs['value'] for i in tr.find_all('input')]
                        yearmonth = cell[1]
                        ylsum=ylsum+float(cell[4])
                        if years == '' or years != yearmonth[:4]:
                            years = yearmonth[:4]
                            self.result_data['old_age']['data'][years] = {}
                            if len(months) > 0:
                                if months == yearmonth[-2:]:
                                    self.result_data['old_age']['data'][years][months] = {}
                        if months == '' or months != yearmonth[-2:]:
                            months = yearmonth[-2:]
                            self.result_data['old_age']['data'][years][months] = {}
                        dicts={'险种': cell[0],
                                 '缴费时间': cell[1],
                               '缴费类型':'',
                               '缴费基数': cell[2].replace(',',''),
                               '公司缴费': cell[3],
                               '个人缴费': cell[4],
                               '单位编号':cell[5],
                               '缴费单位': cell[6]}
                        arr.append(dicts)
                        self.result_data['old_age']['data'][years][months] = arr
                data['baseInfo']['个人养老累计缴费'] =ylsum


            #医疗
            resp = self.s.post(YIL_URL, data=dict(
                method='queryMediPayHis',
                __usersession_uuid=self.g.usersession_uuid,
                _random=random.random()
            ), headers={'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                        'X-Requested-With': 'XMLHttpRequest'})
            soup = BeautifulSoup(resp.content, 'html.parser')
            selecttext = soup.findAll('option')
            yilsum = 0.00
            for i in range(1, len(selecttext)):
                print(selecttext[i].text)

                self.result_data['medical_care'] = {}
                self.result_data['medical_care']['data'] = {}
                years = ''
                months = ''
                trinfo = soup.findAll('table')[1]
                for tr in trinfo.findAll('tr'):
                    arr = []
                    cell = [i.text for i in tr.find_all('td')]
                    if cell[0] == '':
                        cell = [i.attrs['value'] for i in tr.find_all('input')]
                        yearmonth = cell[1]
                        yilsum = yilsum + float(cell[4])
                        if years == '' or years != yearmonth[:4]:
                            years = yearmonth[:4]
                            self.result_data['medical_care']['data'][years] = {}
                            if len(months) > 0:
                                if months == yearmonth[-2:]:
                                    self.result_data['medical_care']['data'][years][months] = {}
                        if months == '' or months != yearmonth[-2:]:
                            months = yearmonth[-2:]
                            self.result_data['medical_care']['data'][years][months] = {}
                        dicts = {'险种': cell[0],
                                 '缴费时间': cell[1],
                                 '缴费类型': '',
                                 '缴费基数': cell[2].replace(',',''),
                                 '公司缴费': cell[3],
                                 '个人缴费': cell[4],
                                 '单位编号': cell[5],
                                 '缴费单位': cell[6]}
                        arr.append(dicts)
                        self.result_data['medical_care']['data'][years][months] = arr
                data['baseInfo']['个人医疗累计缴费'] = yilsum

            # 工商
            resp = self.s.post(GS_URL, data=dict(
                method='queryHarmPayHis',
                __usersession_uuid=self.g.usersession_uuid,
                _random=random.random()
            ), headers={'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                        'X-Requested-With': 'XMLHttpRequest'})
            soup = BeautifulSoup(resp.content, 'html.parser')
            selecttext = soup.findAll('option')
            for i in range(1, len(selecttext)):
                    print(selecttext[i].text)

                    self.result_data['injuries'] = {}
                    self.result_data['injuries']['data'] = {}
                    years = ''
                    months = ''
                    trinfo = soup.findAll('table')[1]
                    for tr in trinfo.findAll('tr'):
                        arr = []
                        cell = [i.text for i in tr.find_all('td')]
                        if cell[0] == '':
                            cell = [i.attrs['value'] for i in tr.find_all('input')]
                            yearmonth = cell[1]
                            if years == '' or years != yearmonth[:4]:
                                years = yearmonth[:4]
                                self.result_data['injuries']['data'][years] = {}
                                if len(months) > 0:
                                    if months == yearmonth[-2:]:
                                        self.result_data['injuries']['data'][years][months] = {}
                            if months == '' or months != yearmonth[-2:]:
                                months = yearmonth[-2:]
                                self.result_data['injuries']['data'][years][months] = {}
                            dicts = {'险种': cell[0],
                                 '缴费时间': cell[1],
                                     '缴费类型': '',
                                     '缴费基数': cell[2].replace(',',''),
                                     '公司缴费': cell[3],
                                     '个人缴费': cell[4],
                                     '单位编号': cell[5],
                                     '缴费单位': cell[6]}
                            arr.append(dicts)
                            self.result_data['injuries']['data'][years][months] = arr

            # 生育
            resp = self.s.post(SHY_URL, data=dict(
                method='queryBirthPayHis',
                __usersession_uuid=self.g.usersession_uuid,
                _random=random.random()
            ), headers={'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                        'X-Requested-With': 'XMLHttpRequest'})
            soup = BeautifulSoup(resp.content, 'html.parser')
            selecttext = soup.findAll('option')
            for i in range(1, len(selecttext)):
                print(selecttext[i].text)

                self.result_data['maternity'] = {}
                self.result_data['maternity']['data'] = {}
                years = ''
                months = ''
                trinfo = soup.findAll('table')[1]
                for tr in trinfo.findAll('tr'):
                    arr = []
                    cell = [i.text for i in tr.find_all('td')]
                    if cell[0] == '':
                        cell = [i.attrs['value'] for i in tr.find_all('input')]
                        yearmonth = cell[1]
                        if years == '' or years != yearmonth[:4]:
                            years = yearmonth[:4]
                            self.result_data['maternity']['data'][years] = {}
                            if len(months) > 0:
                                if months == yearmonth[-2:]:
                                    self.result_data['maternity']['data'][years][months] = {}
                        if months == '' or months != yearmonth[-2:]:
                            months = yearmonth[-2:]
                            self.result_data['maternity']['data'][years][months] = {}
                        dicts = {'险种': cell[0],
                                 '缴费时间': cell[1],
                                 '缴费类型': '',
                                 '缴费基数': cell[2].replace(',',''),
                                 '公司缴费': cell[3],
                                 '个人缴费': cell[4],
                                 '单位编号': cell[5],
                                 '缴费单位': cell[6]}
                        arr.append(dicts)
                        self.result_data['maternity']['data'][years][months] = arr

            # 失业
            resp = self.s.post(SY_URL, data=dict(
                method='queryLostPayHis',
                __usersession_uuid=self.g.usersession_uuid,
                _random=random.random()
            ), headers={'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                        'X-Requested-With': 'XMLHttpRequest'})
            soup = BeautifulSoup(resp.content, 'html.parser')
            selecttext = soup.findAll('option')
            for i in range(1, len(selecttext)):
                print(selecttext[i].text)

                self.result_data['unemployment'] = {}
                self.result_data['unemployment']['data'] = {}
                years = ''
                months = ''
                trinfo = soup.findAll('table')[1]
                for tr in trinfo.findAll('tr'):
                    arr = []
                    cell = [i.text for i in tr.find_all('td')]
                    if cell[0] == '':
                        cell = [i.attrs['value'] for i in tr.find_all('input')]
                        yearmonth = cell[1]
                        if years == '' or years != yearmonth[:4]:
                            years = yearmonth[:4]
                            self.result_data['unemployment']['data'][years] = {}
                            if len(months) > 0:
                                if months == yearmonth[-2:]:
                                    self.result_data['unemployment']['data'][years][months] = {}
                        if months == '' or months != yearmonth[-2:]:
                            months = yearmonth[-2:]
                            self.result_data['unemployment']['data'][years][months] = {}
                        dicts = {'险种': cell[0],
                                 '缴费时间': cell[1],
                                 '缴费类型': '',
                                 '缴费基数': cell[2].replace(',',''),
                                 '公司缴费': cell[3],
                                 '个人缴费': cell[4],
                                 '单位编号': cell[5],
                                 '缴费单位': cell[6]}
                        arr.append(dicts)
                        self.result_data['unemployment']['data'][years][months] = arr
            # 大病
            resp = self.s.post(YIL_URL, data=dict(
                method='queryEmpJfxxZzCxDe',
                __usersession_uuid=self.g.usersession_uuid,
                _random=random.random()
            ), headers={'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                        'X-Requested-With': 'XMLHttpRequest'})
            soup = BeautifulSoup(resp.content, 'html.parser')
            selecttext = soup.findAll('option')
            for i in range(1, len(selecttext)):
                print(selecttext[i].text)

                self.result_data['serious_illness'] = {}
                self.result_data['serious_illness']['data'] = {}
                years = ''
                months = ''
                trinfo = soup.findAll('table')[1]
                for tr in trinfo.findAll('tr'):
                    arr = []
                    cell = [i.text for i in tr.find_all('td')]
                    if cell[0] == '':
                        cell = [i.attrs['value'] for i in tr.find_all('input')]
                        yearmonth = cell[1]
                        if years == '' or years != yearmonth[:4]:
                            years = yearmonth[:4]
                            self.result_data['serious_illness']['data'][years] = {}
                            if len(months) > 0:
                                if months == yearmonth[-2:]:
                                    self.result_data['unemployment']['data'][years][months] = {}
                        if months == '' or months != yearmonth[-2:]:
                            months = yearmonth[-2:]
                            self.result_data['serious_illness']['data'][years][months] = {}
                        dicts = {'险种': cell[0],
                                 '缴费时间': cell[1],
                                 '缴费类型': cell[6],
                                 '缴费基数': cell[2].replace(',',''),
                                 '公司缴费': '',
                                 '个人缴费': cell[3],
                                 '单位编号': cell[4],
                                 '缴费单位': cell[5]}
                        arr.append(dicts)
                        self.result_data['serious_illness']['data'][years][months] = arr
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        #randoms=random.random()
        #vc_url = VC_URL +str(randoms) #str(int(time.time() * 1000))
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
        imgsave=io.BytesIO()
        toImage.save(imgsave,"PNG")
        imgsave.seek(0)
        resp = imgsave.read()
        return dict(cls='data:image', content=resp)
if __name__ == '__main__':
    from services.client import TaskTestClient
    meta = {'身份证号': '370302197811184822', '密码': 'qq781017'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()
