import time
import io
import hashlib
from PIL import Image
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


USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3100.0 Safari/537.36"
LOGIN_PAGE_URL = 'https://weixin.szzfgjj.com/WheatInterface/index.html?view=my-account'
LOGIN_URL = 'https://nbp.szzfgjj.com/nbp/ydp/mainPri_new.jsp'
VC_URL = 'https://nbp.szzfgjj.com/nbp/ranCode.jsp?tab=card'
GJJMX_URL = 'http://www.aygjj.com/gjjcx/zfbzgl/gjjmxcx/gjjmx_cx.jsp'
class Task(AbsFetchTask):
    task_info = dict(
        city_name="深圳",
        help="""<li>如您首次在网上查询您的公积金账户，初始密码为身份证后六位，身份证号码有字母的用数字“0”代替。</li>
                <li>如您在公积金官网查询过您的公积金账户，请输入账户信息和密码登录即可。</li>""",
        developers=[{'name':'卜圆圆','email':'byy@qinqinxiaobao.com'}]
    )
    def _get_common_headers(self):
        return {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko'}

    def _query(self, params: dict):
        """任务状态查询"""
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()
    def _prepare(self, data=None):
        super()._prepare(data)
        self.dsc = DriverRequestsCoordinator(s=self.s, create_driver=self._create_driver)

    def _create_driver(self):
        driver = new_driver(user_agent=USER_AGENT, js_re_ignore='/web\/ImageCheck.jpg/g')
        driver.get('https://nbp.szzfgjj.com/xxx')
        return driver
    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '公积金账号' in params, '缺少公积金账号'
        assert '密码' in params, '缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check
        公积金账号 = params['公积金账号']
        密码 = params['密码']

        if len(公积金账号) == 0:
            raise InvalidParamsError('公积金账号为空，请输入公积金账号')
        elif len(公积金账号) != 11:
            raise InvalidParamsError('公积金账号不正确，请重新输入')

        if len(密码) == 0:
            raise InvalidParamsError('密码为空，请输入密码！')
        elif len(密码) < 6:
            raise InvalidParamsError('密码不正确，请重新输入！')
    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '公积金账号' not in params:
                params['公积金账号'] = meta.get('公积金账号')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params
    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '公积金账号' and '公积金账号' in meta:
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
                id_num = params['公积金账号']
                password = params['密码']
                vc = params['vc']
                #self._do_login(id_num, password, vc)
                m = hashlib.md5()
                m.update(password.encode(encoding='utf-8'))
                hashpsw = m.hexdigest()
                data = {
                    'task': 'pri',
                    'transcode': 'card',
                    'ssoLogin': '',
                    'issueName': '',
                    'UserCert': '',
                    'bjcaRanStr': '',
                    'ranStr': '',
                    'CardNo': id_num,
                    'QryPwd': '19ee8550b7b1af89',
                    'identifyCode': vc,
                    'sSignTxt': '',
                    'SUBMIT.x': '91',
                    'SUBMIT.y': '15'
                }
                resp = self.s.post(LOGIN_URL, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded',
                                                                  'Cache-Control': 'no-cache'})
                soup = self.s.soup
                errormsg = soup.select('.message')[0].text
                if errormsg and errormsg != id_num:
                    raise Exception(errormsg)
                else:
                    print('chengong')

                self.result_key = params.get('公积金账号')
                # 保存到meta
                self.result_meta['公积金账号'] = params.get('公积金账号')
                self.result_meta['密码'] = params.get('密码')
                self.result_identity['task_name'] = '深圳'

                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)
        vc = self._new_vc()
        raise AskForParamsError([
            dict(key='公积金账号', name='公积金账号', cls='input', placeholder='公积金账号', value=params.get('公积金账号', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)
    def _do_login(self, username, password, vc):
        """使用web driver模拟登录过程"""
        with self.dsc.get_driver_ctx() as driver:
            # 打开登录页
            driver.get(LOGIN_PAGE_URL)

            username_input = driver.find_element_by_xpath('//*[@id="pri"]/p[1]/label[2]/input')
            password_input = driver.find_element_by_xpath('//*[@id="pri"]/p[2]/label[2]')
            vc_input = driver.find_element_by_xpath('//*[@name="identifyCode"]')
            submit_btn = driver.find_element_by_xpath('//*[@id="pri"]/p[6]/input[1]')

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
            submit_btn.click()
            time.sleep(2)

            if driver.current_url != LOGIN_PAGE_URL:
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
    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)

    def _new_vc(self):
        vc_url = VC_URL  # + str(int(time.time() * 1000))
        resp = self.s.get(vc_url)
        return dict(content=resp.content, content_type=resp.headers['Content-Type'])
if __name__ == '__main__':
    from services.client import TaskTestClient

    meta = {'公积金账号': '21273561766', '密码': '140010'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()
#公积金账号" : "21273561766", "密码" : "140010"    "21259724046", "密码" : "244515" 20435172286", "密码" : "123654"
