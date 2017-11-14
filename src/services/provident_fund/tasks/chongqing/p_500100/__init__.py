import time
import io
from PIL import Image
from bs4 import BeautifulSoup
from services.service import SessionData, AbsTaskUnitSessionTask
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


USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3100.0 Safari/537.36"
LOGIN_PAGE_URL = 'http://www.cqgjj.cn/html/user/login.html'

class Task(AbsFetchTask):
    task_info = dict(
        city_name="重庆",
        help="""<li>初始密码为公积金账号后四位+00；可登录重庆住房公积金管理中心官网后进行修改。</li>
        <li>未验证注册用户首次登录时需进行身份验证，具体验证方式如下：用户通过输入公积金联名卡后六位（若用户未办理公积金联名卡的须输入个人公积金账号）验证登录。</li>""",
        developers=[{'name':'卜圆圆','email':'byy@qinqinxiaobao.com'}]
    )

    def _get_common_headers(self):
        return {'User-Agent':'Mozilla/5.0 (iPad; CPU OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1'}

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
        driver.get('https://www.cqgjj.cn/xxx')
        return driver

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '账号' in params, '缺少账号'
        assert '密码' in params, '缺少密码'
        assert 'vc' in params, '缺少验证码'
        # other check
        账号 = params['账号']
        密码 = params['密码']
        if len(密码) < 4:
            raise InvalidParamsError('账号或密码错误')
        if 账号.isdigit():
            if len(账号) < 5:
                raise InvalidParamsError('账号错误')
            return
        raise InvalidParamsError('账号或密码错误')
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
    def _unit_login(self, params: dict):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                id_num = params['账号']
                password = params['密码']
                vc = params['vc']
                self._do_login(id_num, password, vc)


                self.result_key = params.get('账号')
                # 保存到meta
                self.result_meta['账号'] = params.get('账号')
                self.result_meta['密码'] = params.get('密码')
                self.result_identity['task_name'] = '重庆'

                raise TaskNotImplementedError('查询服务维护中')
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)
        vc = self._new_vc()
        raise AskForParamsError([
            dict(key='账号', name='账号', cls='input', placeholder='账号/手机', value=params.get('账号', '')),
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


if __name__ == '__main__':
    from services.client import TaskTestClient

    meta = {'账号': '15123133361', '密码': 'haoran'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()
#账号': '15826126132', '密码': 'qinyu20070207'  账号': '15123133361', '密码': 'haoran'