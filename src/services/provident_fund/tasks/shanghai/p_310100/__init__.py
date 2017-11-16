import time
import hashlib
from PIL import Image
import io
import re
from urllib import parse
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
from services.webdriver import new_driver, DriverRequestsCoordinator, DriverType
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskNotAvailableError
from services.errors import InvalidParamsError, TaskNotImplementedError
from services.commons import AbsFetchTask
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class value_is_number(object):
    """判断元素value是数字"""

    def __init__(self, locator):
        self.locator = locator

    def __call__(self, driver):
        element = driver.find_element(*self.locator)
        val = element.get_attribute('value')
        return val and val.isnumeric()


USER_AGENT = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0"
LOGIN_PAGE_URL = 'https://persons.shgjj.com/'
MAIN_URL = 'http://www.aygjj.com/gjjcx/zfbzgl/zfbzsq/main_menu.jsp'
LOGIN_URL = 'https://persons.shgjj.com/MainServlet'
VC_URL = 'https://persons.shgjj.com/VerifyImageServlet'
GJJMX_URL = 'http://www.aygjj.com/gjjcx/zfbzgl/gjjmxcx/gjjmx_cx.jsp'
GJJ_URL = 'http://www.aygjj.com/gjjcx/zfbzgl/zfbzsq/gjjmx_cxtwo.jsp'


class Task(AbsFetchTask):
    task_info = dict(
        city_name="上海",
        help="""<li>如您未在公积金网站查询过您的公积金信息，请到上海公积金管理中心官网网完成“注册”然后再登录。</li>
                <li>用户名指的是在注册时自行设置的2-12位英文字母或数字（区分大小写）。</li>
                """,
        developers=[{'name':'卜圆圆','email':'byy@qinqinxiaobao.com'}]
    )

    def _get_common_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3100.0 Safari/537.36'
        }

    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch_name, self._unit_login)

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    # noinspection PyMethodMayBeStatic
    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '用户名' in params, '缺少用户名'
        assert '密码' in params, '缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check
        用户名 = params['用户名']
        密码 = params['密码']

        if len(用户名) == 0:
            raise InvalidParamsError('用户名为空，请输入用户名')
        elif len(用户名) < 5:
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

    def _prepare(self, data=None):
        super()._prepare(data)
        self.dsc = DriverRequestsCoordinator(s=self.s, create_driver=self._create_driver)

    def _create_driver(self):
        driver = new_driver(user_agent=USER_AGENT, js_re_ignore='/web\/ImageCheck.jpg/g')
        driver.get(LOGIN_PAGE_URL)

        return driver

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

    def _unit_login(self, params=None):
        err_msg = None
        params
        if not self.is_start or params:
            # 非开始或者开始就提供了参数
            try:
                self._check_login_params(params)
                id_num = params['用户名']
                password = params['密码']
                vc = params['vc']
                # self._do_login(id_num, password, vc)

                m = hashlib.md5()
                m.update(password.encode(encoding='utf-8'))
                hashpsw = m.hexdigest()
                data = {
                    'password_md5': hashpsw,
                    'username': id_num,
                    'password': password,
                    'imagecode': vc,
                    'ID': '0',
                    'SUBMIT.x': '35',
                    'SUBMIT.y': '8'
                }
                resp = self.s.post(LOGIN_URL, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded',
                                                                  'Cache-Control': 'max-age=0',
                                                                  'Upgrade-Insecure-Requests': '1'})
                soup = BeautifulSoup(resp.content, 'html.parser')
                errormsg = soup.findAll('font')[0].text
                if errormsg and errormsg != id_num:
                    raise InvalidParamsError(errormsg)
                else:
                    self.g.soup = soup

                self.result_key = id_num
                self.result_meta['用户名'] = id_num
                self.result_meta['密码'] = password
                self.result_identity['task_name'] = '上海'
                self.result_identity['target_id'] = id_num

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        vc = self._new_vc()
        raise AskForParamsError([
            dict(key='用户名', name='用户名', cls='input'),
            dict(key='密码', name='密码', cls='input:password'),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _do_login(self, username, password, vc):
        """使用web driver模拟登录过程"""
        with self.dsc.get_driver_ctx() as driver:
            # 打开登录页
            driver.get(LOGIN_PAGE_URL)
            Image.open(io.BytesIO(driver.get_screenshot_as_png())).show()
            username_input = driver.find_element_by_xpath(
                '/html/body/form/table/tbody/tr/td[2]/table[2]/tbody/tr/td/table/tbody/tr[2]/td[2]/input')
            password_input = driver.find_element_by_xpath(
                '/html/body/form/table/tbody/tr/td[2]/table[2]/tbody/tr/td/table/tbody/tr[3]/td[2]/input')
            vc_input = driver.find_element_by_xpath(
                '/html/body/form/table/tbody/tr/td[2]/table[2]/tbody/tr/td/table/tbody/tr[4]/td[2]/input')
            submit_btn = driver.find_element_by_xpath(
                '/html/body/form/table/tbody/tr/td[2]/table[2]/tbody/tr/td/table/tbody/tr[5]/td[2]/input[1]')
            ok = driver.find_element_by_name("SUBMIT")
            Image.open(io.BytesIO(driver.get_screenshot_as_png())).show()
            # 用户名
            username_input.clear()
            username_input.send_keys(username)

            # 密码
            password_input.clear()
            password_input.send_keys(password)
            vc_input.clear()
            vc_input.send_keys(vc)

            Image.open(io.BytesIO(driver.get_screenshot_as_png())).show()

            login_page_html = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
            # 提交

            ok.click()
            submit_btn.click()
            time.sleep(5)
            # WebDriverWait(driver, 10).until(
            #     lambda driver:
            #         EC.invisibility_of_element_located((By.XPATH, 'html/body/div[2]/div/div/div/div[1]/div/div[2]/div[2]/div/div[1]/a[1]'))(driver)
            #     or EC.element_to_be_clickable((By.XPATH, '//*[@id="div_dialog_login"]/div/div/div/form/div[5]/input[1]'))(driver))
            #
            # login_btn = driver.find_element_by_xpath('html/body/div[2]/div/div/div/div[1]/div/div[2]/div[2]/div/div[1]/a[1]')
            # s = login_btn.get_attribute('style')
            Image.open(io.BytesIO(driver.get_screenshot_as_png())).show()
            # if not s:
            #     # failed
            #     err_msg = driver.find_element_by_xpath('//*[@id="div_dialog_login"]/div/div/div/form/div[3]/font').text
            #     raise InvalidParamsError(err_msg)
            #     # TODO
            # else:
            #     # success
            #     print('success')
            # Image.open(io.BytesIO(driver.get_screenshot_as_png())).show()

    def _unit_fetch_name(self):
        try:
            # 基本信息
            soup = self.g.soup
            table = soup.select('.table')[0]
            data = self.result_data
            data['baseInfo'] = {
                '城市名称': '上海',
                '城市编号': '310100',
                '证件号': '',
                '证件类型': '',
                '个人登记号': '',
                '更新时间': time.strftime("%Y-%m-%d", time.localtime())
            }
            for tr in table.findAll('tr'):
                cell = [i.text for i in tr.find_all('td')]
                if len(cell) > 1:
                    data['baseInfo'].setdefault(cell[0].replace(' ', '').replace('所属单位','单位名称').replace('末次缴存年月','汇缴年月').replace('账户余额','当前余额').replace('当前账户状态','账户状态').replace('绑定手机号','手机号').replace('月缴存额','月应缴额'),
                                                cell[1].replace('\r\n             ', '').replace('  >>>住房公积金本年度账户明细',
                                                                                                 '').replace(
                                                    '\xa0\xa0\xa0\xa0\xa0【修改】', '').replace('             ', '').replace('年','').replace('月','').replace('日',''))

            self.result_identity['target_name']=data['baseInfo']['姓名']
            self.result_identity['status'] = data['baseInfo']['账户状态']
            # 内容
            infourl = LOGIN_URL + '?ID=11'
            resp = self.s.get(infourl)
            soup = BeautifulSoup(resp.content, 'html.parser')
            data['detail'] = {}
            data['detail']['data'] = {}
            enterarr = []
            enterdic = {}
            enterfullname = ''
            infotable = soup.select('.table')[0].findAll('tr')
            years = ''
            months = ''

            for y in range(2, len(infotable)):
                dic = {}
                arr = []
                cell = [i.text for i in infotable[y].find_all('td')]
                if len(cell) > 4:
                    if cell[3] == '支取':
                        dic = {
                            '时间': cell[0].replace('年', '-').replace('月', '-').replace('日', ''),
                            '单位名称': cell[1],
                            '支出': cell[2],
                            '收入': 0,
                            '汇缴年月': '',
                            '余额': '',
                            '类型': cell[3],
                            '业务原因': cell[4].replace('\xa0', '')
                        }
                    else:
                        strname=cell[3].replace('年', '').replace('月', '')
                        strtype =cell[3]
                        strtime =''
                        if len(re.findall(r"汇缴(.+?)公积金", strname))>0:
                            strtype=strname[:2]
                            strtime=strname[2:8]

                        dic = {
                            '时间': cell[0].replace('年', '-').replace('月', '-').replace('日', ''),
                            '单位名称': cell[1],
                            '支出': 0,
                            '收入': cell[2],
                            '汇缴年月': strtime,
                            '余额': '',
                            '类型':strtype ,
                            '业务原因': cell[4].replace('\xa0', '')
                        }

                    times = cell[0][:7].replace('年', '')
                    if years != times[:4]:
                        years = times[:4]
                        data['detail']['data'][years] = {}
                        if months != times[-2:]:
                            months = times[-2:]
                    else:
                        if months != times[-2:]:
                            months = times[-2:]
                        else:
                            arr = data['detail']['data'][years][months]
                    arr.append(dic)
                    data['detail']['data'][years][months] = arr
                    print(arr)
                    if enterfullname == '':
                        enterfullname = cell[1]
                        enterdic = {
                            "单位名称": cell[1],
                            "单位登记号": "",
                            "所属管理部编号": "",
                            "所属管理部名称": "",
                            "当前余额": data['baseInfo']['当前余额'],
                            "帐户状态": data['baseInfo']['账户状态'],
                            "当年缴存金额": 0,
                            "当年提取金额": 0,
                            "上年结转余额": 0,
                            "最后业务日期": cell[0].replace('年', '-').replace('月', '-').replace('日', ''),
                            "转出金额": 0
                        }

                    elif enterfullname != cell[1]:
                        enterfullname = cell[1]
                        enterarr.append(enterdic)
                        enterdic = {
                            "单位名称": cell[1],
                            "单位登记号": "",
                            "所属管理部编号": "",
                            "所属管理部名称": "",
                            "当前余额": data['baseInfo']['当前余额'],
                            "帐户状态": '转出',
                            "当年缴存金额": 0,
                            "当年提取金额": 0,
                            "上年结转余额": 0,
                            "最后业务日期": cell[0].replace('年', '-').replace('月', '-').replace('日', ''),
                            "转出金额": 0
                        }
            enterarr.append(enterdic)
            data['companyList'] = enterarr
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        vc_url = VC_URL  # + str(int(time.time() * 1000))
        resp = self.s.get(vc_url)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])


if __name__ == '__main__':
    from services.client import TaskTestClient

    client = TaskTestClient(Task())
    client.run()
    # 	用户名：Candina，密码：123456
