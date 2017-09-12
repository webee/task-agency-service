import html
import os
import time
import bs4
from services.webdriver import new_driver, DriverRequestsCoordinator
from services.commons import AbsFetchTask
from services.errors import InvalidParamsError, AskForParamsError, InvalidConditionError, PreconditionNotSatisfiedError
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


USER_AGENT = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0"
LOGIN_PAGE_URL = 'http://www.bjgjj.gov.cn/wsyw/wscx/gjjcx-login.jsp'
VC_IMAGE_URL = 'http://www.bjgjj.gov.cn/wsyw/servlet/PicCheckCode1?v='


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

    def _create_driver(self):
        driver = new_driver(user_agent=USER_AGENT)

        # 不加载验证码
        script = """
        var page = this;
        page.onResourceRequested = function(requestData, networkRequest) {
            var match = requestData.url.match(/PicCheckCode1/g);
            if (match != null) {
                //console.log('Request (#' + requestData.id + '): ' + JSON.stringify(requestData));
                //networkRequest.cancel(); // or .abort()
                networkRequest.abort();
            }
        };
        """
        driver.execute('executePhantomScript', {'script': script, 'args': []})

        return driver

    def _setup_task_units(self):
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _query(self, params: dict):
        t = params.get('t')
        if t == 'vc':
            return self._new_vc()

    def _new_vc(self):
        vc_url = VC_IMAGE_URL + str(int(time.time() * 1000))
        resp = self.s.get(vc_url)
        return dict(cls='data:image', content=resp.content, content_type=resp.headers.get('Content-Type'))

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '身份证号' not in params:
                params['身份证号'] = meta.get('身份证号')
            if '查询密码' not in params:
                params['查询密码'] = meta.get('查询密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # TODO: 进一步检查details
            if pr['key'] == '身份证号' and '身份证号' in meta:
                continue
            elif pr['key'] == '查询密码' and '查询密码' in meta:
                continue
            res.append(pr)
        return res

    def _check_login_params(self, params):
        assert params is not None, '缺少参数'
        assert '身份证号' in params, '缺少身份证号'
        assert '查询密码' in params, '缺少查询密码'
        assert 'vc' in params, '缺少验证码'

        # TODO: 检查身份证号
        # TODO: 检查密码
        # TODO: 检查验证码

    def _unit_login(self, params=None):
        err_msg = None
        if params:
            try:
                self._check_login_params(params)
                username = params['身份证号']
                password = params['查询密码']
                vc = params['vc']

                self._do_login(username, password, vc)
                # 登录成功
                self.result_key = username
                self.result_meta.update({
                    '身份证号': username,
                    '查询密码': password
                })
                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)

        raise AskForParamsError([
            dict(key='身份证号', name='身份证号', cls='input', value=params.get('身份证号', '')),
            dict(key='查询密码', name='个人编号', cls='input', value=params.get('查询密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _do_login(self, username, password, vc):
        """使用web driver模拟登录过程"""
        with self.dsc.get_driver_ctx() as driver:
            # 打开登录页
            driver.get(LOGIN_PAGE_URL)
            # 等待lk请求
            WebDriverWait(driver, 10).until(value_is_number((By.XPATH, '//*[@id="lk"]')))

            # 选择身份证号方式登录
            driver.find_element_by_xpath('/html/body/table[2]/tbody/tr[3]/td/table/tbody/tr/td/div/form/div[1]/ul/li[3]/a').click()

            username_input = driver.find_element_by_xpath('//*[@id="bh1"]')
            password_input = driver.find_element_by_xpath('//*[@id="mm1"]')
            vc_input = driver.find_element_by_xpath('//*[@id="login_tab_2"]/div/div[3]/input')
            submit_btn = driver.find_element_by_xpath('//*[@id="login_tab_2"]/div/div[4]/input[1]')

            # 用户名
            username_input.clear()
            username_input.send_keys(username)

            # 密码
            password_input.clear()
            password_input.send_keys(password)
            vc_input.clear()
            vc_input.send_keys(vc)
            # 提交
            submit_btn.click()

            if not driver.current_url == 'http://www.bjgjj.gov.cn/wsyw/wscx/gjjcx-choice.jsp':
                raise InvalidParamsError('登录失败，请检查输入')

            # 登录成功

            # 保存登录后的页面内容供抓取单元解析使用
            self.g.login_page_html = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
            self.g.current_url = driver.current_url

    def _unit_fetch(self):
        try:
            # TODO:
            soup = bs4.BeautifulSoup(self.g.login_page_html, 'html.parser')
            a = soup.select('a')[1]
            link = a.attrs['onclick'].split('"')[1]
            link = os.path.join(os.path.dirname(self.g.current_url), link)

            resp = self.s.get(link)
            self.result_data.update({
                'xxx': a.text,
                'link': link,
                'content': html.unescape(resp.text)
            })
            self.result_identity.update({
                'task_name': self.task_info['task_name']
            })
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    meta = {'身份证号': '141031199008250053', '查询密码': '101169'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()
