import io
from PIL import Image
import html
import os
from lxml import etree
import random
import time
import bs4
from services.webdriver import new_driver, DriverRequestsCoordinator, DriverType
from services.commons import AbsFetchTask
from services.errors import InvalidParamsError, AskForParamsError, InvalidConditionError, PreconditionNotSatisfiedError
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


USER_AGENT = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0"
LOGIN_PAGE_URL = 'http://gzlss.hrssgz.gov.cn/cas/login'
VC_IMAGE_URL = 'http://gzlss.hrssgz.gov.cn/cas/captcha.jpg?Rnd='


class value_is_number(object):
    """判断元素value是数字"""
    def __init__(self, locator):
        self.locator = locator

    def __call__(self, driver):
        element = driver.find_element(*self.locator)
        val = element.get_attribute('value')
        return val and val.isnumeric()


class Task(AbsFetchTask):
    task_info = {
        'task_name': '测试selenium登录[fast]',
        'help': '测试selenium登录[fast]'
    }

    def _get_common_headers(self):
        return {
            'User-Agent': USER_AGENT
        }

    def _prepare(self, data=None):
        super()._prepare(data)

        self.dsc = DriverRequestsCoordinator(s=self.s, create_driver=self._create_driver)
        # self.dsc = DriverRequestsCoordinator(s=self.s, create_driver=self._create_chrome_driver)

    def _create_chrome_driver(self):
        driver = new_driver(user_agent=USER_AGENT, driver_type=DriverType.CHROME)
        return driver

    def _create_driver(self):
        driver = new_driver(user_agent=USER_AGENT, js_re_ignore='/cas\/captcha.jpg/g')

        # 随便访问一个相同host的地址，方便之后设置cookie
        driver.get('http://gzlss.hrssgz.gov.cn/xxxx')

        return driver

    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    def _new_vc(self):
        vc_url = VC_IMAGE_URL + str(random.random())
        resp = self.s.get(vc_url)
        return dict(cls='data:image', content=resp.content, content_type=resp.headers.get('Content-Type'))

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

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '账号' in params, '缺少账号'
        assert '密码' in params, '缺少密码'
        # other check
        账号 = params['账号']
        密码 = params['密码']
        if len(密码) < 4:
            raise InvalidParamsError('账号或密码错误')
        if len(账号) < 4:
            raise InvalidParamsError('账号或密码错误')

    def _unit_login(self, params=None):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                username = params['账号']
                password = params['密码']
                vc = params['vc']

                self._do_login(username, password, vc)
                # 登录成功
                self.result_key = username
                self.result_meta.update({
                    '账号': username,
                    '密码': password
                })
                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='账号', name='账号', cls='input', value=params.get('账号', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _do_login(self, username, password, vc):
        """使用web driver模拟登录过程"""
        with self.dsc.get_driver_ctx() as driver:
            # 打开登录页
            driver.get(LOGIN_PAGE_URL)

            # FIXME: debug
            # for l in driver.get_log('browser'):
            #     print(l)

            username_input = driver.find_element_by_xpath('//*[@id="loginName"]')
            password_input = driver.find_element_by_xpath('//*[@id="loginPassword"]')
            vc_input = driver.find_element_by_xpath('//*[@id="validateCode"]')
            user_type_input = driver.find_element_by_xpath('//*[@id="usertype2"]')

            # 用户名
            username_input.clear()
            username_input.send_keys(username)

            # 密码
            password_input.clear()
            password_input.send_keys(password)

            # 验证码
            vc_input.clear()
            vc_input.send_keys(vc)

            # 选择类型
            user_type_input.click()

            # 登录
            driver.find_element_by_xpath('//*[@id="submitbt"]').click()

            # FIXME: debug
            # for l in driver.get_log('browser'):
            #     print(l)

            if driver.current_url.startswith('http://gzlss.hrssgz.gov.cn/cas/login'):
                err_msg = '登录失败，请检查输入'
                try:
                    err_msg = driver.find_element_by_xpath('//*[@id="*.errors"]').text
                finally:
                    raise InvalidParamsError(err_msg)

    def _unit_fetch(self):
        try:
            resp = self.s.get('http://gzlss.hrssgz.gov.cn/gzlss_web/business/tomain/main.xhtml')
            html = etree.HTML(resp.text)
            target = html.xpath('/html/body/div[1]/div[3]/span/font[1]')
            self.result_data.update({
                '姓名': target[0].text
            })
            self.result_identity.update({
                'task_name': self.task_info['task_name']
            })
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    # meta = {'账号': '441225199102281010', '密码': 'wtz969462'}
    meta = {'账号': '440104198710011919', '密码': 'jy794613'}
    # meta = {'账号': '441481198701204831', '密码': 'taifaikcoi168'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()
