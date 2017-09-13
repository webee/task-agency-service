import html
import os
import time
from urllib import parse

import bs4
import re

from services.webdriver import new_driver, DriverRequestsCoordinator
from services.commons import AbsFetchTask
from services.errors import InvalidParamsError, AskForParamsError, InvalidConditionError, PreconditionNotSatisfiedError
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0'
LOGIN_PAGE_URL = 'http://www.bjgjj.gov.cn/wsyw/wscx/gjjcx-login.jsp'
VC_IMAGE_URL = 'http://www.bjgjj.gov.cn/wsyw/servlet/PicCheckCode1?v='


class value_is_number(object):
    def __init__(self, locator):
        self.locator = locator

    def __call__(self, driver):
        element = driver.find_element(*self.locator)
        val = element.get_attribute('value')
        return val and val.isnumeric()


class Task(AbsFetchTask):
    task_info = dict(
        city_name="北京市",
        expect_time=10,
        help="""<li>首次登陆查询功能，验证方式必须选择联名卡号；初始密码为身份证后四位阿拉伯数字+00。为了保证您的个人信息安全，请您及时修改初始密码，如有问题请拨打“住房公积金热线12329”咨询</li>
            """
    )

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
        vc_url = VC_IMAGE_URL + str(int(time.time())*1000)
        resp = self.s.get(vc_url)
        return dict(cls='data:image', content=resp.content, content_type=resp.headers.get('Content-Type'))

    def _params_handler(self, params: dict):
        if not (self.is_start and not params):
            meta = self.prepared_meta
            if '身份证编号' not in params:
                params['身份证编号'] = meta.get('身份证编号')
            if '密码' not in params:
                params['密码'] = meta.get('密码')
        return params

    def _param_requirements_handler(self, param_requirements, details):
        meta = self.prepared_meta
        res = []
        for pr in param_requirements:
            # 身份证登录
            if pr['key'] == 'type' and 'type' in meta and pr['key'] == "3":
                if pr['key'] == '身份证编号' and '身份证编号' in meta:
                    continue
                elif pr['key'] == '密码' and '密码' in meta:
                    continue
            # 联名卡登录
            elif pr['key'] == 'type' and 'type' in meta and pr['key'] == "1":
                if pr['key'] == '联名卡号' and '联名卡号' in meta:
                    continue
                elif pr['key'] == '查询密码' and '查询密码' in meta:
                    continue
            res.append(pr)
        return res

    def _check_login_parama(self, params):
        assert params is not None, '缺少参数'
        assert 'type' in params, '缺少登录类型'
        if params["type"] == "1":
            assert '联名卡号' in params, '缺少联名卡号'
            assert '查询密码' in params, '缺少密码'
        elif params["type"] == "3":
            assert '身份证编号' in params, '缺少身份证号码'
            assert '密码' in params, '缺少密码'
        assert 'vc' in params, '缺少验证码'

        # TODO: 检验身份证
        # TODO: 检验密码
        # TODO: 检验验证码

    def _unit_login(self, params=None):
        err_msg = None
        if params:
            try:
                self._check_login_parama(params)
                username = params['身份证编号']
                password = params['密码']
                vc = params['vc']

                self._do_login(username, password, vc)
                # 登录成功
                self.result_key = username
                self.result_meta.update({
                    '身份证编号': username,
                    '密码': password
                })
                return
            except (AssertionError, InvalidParamsError) as e:
                err_msg = str(e)
        raise AskForParamsError([
            dict(key='身份证编号', name='身份证号', cls='input', value=params.get('身份证编号', '')),
            dict(key='密码', name='密码', cls='input:password', value=params.get('密码', '')),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'})
        ],  err_msg)

    def _do_login(self, username, password, vc):
        """使用 web driver 模拟登录过程"""
        with self.dsc.get_driver_ctx() as driver:
            # 打开页面
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

            # 验证码
            vc_input.clear()
            vc_input.send_keys(vc)

            # 提交
            submit_btn.click()

            if not driver.current_url == "http://www.bjgjj.gov.cn/wsyw/wscx/gjjcx-choice.jsp":
                raise InvalidParamsError('登录失败，请检查输入')

            # 登录成功

            # 保存登录后的页面内容供抓取单元解析使用
            self.g.login_page_html = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
            self.g.current_url = driver.current_url

    def _unit_fetch(self):
        try:
            # TODO:
            self.result_data["baseInfo"] = {}
            self.result_data["companyList"] = []
            self.result_data["detail"] = {"data": {}}
            soup = bs4.BeautifulSoup(self.g.login_page_html, 'html.parser')
            companyList = soup.findAll("table", {"id": "new-mytable"})
            name = ''
            target_id = ''
            paymentStart = ''
            if len(companyList) > 0:
                trs = companyList[0].findAll("tr")
                i = 0
                for tr in trs:
                    tds = tr.findAll("td")
                    if tr != trs[0]:
                        a = tds[1].findAll("a")[0]
                        link = a.attrs['onclick'].split('"')[1]
                        link = parse.urljoin(self.g.current_url, link)
                        resp = self.s.get(link)
                        try:
                            result = bs4.BeautifulSoup(resp.text, 'html.parser')
                            if result:
                                table = result.findAll("table")[1]
                                if table:
                                    _tds = table.findAll("td")
                                    name = _tds[27].text
                                    target_id = _tds[33].text
                                    paymentStart = _tds[45].text

                                    self.result_data["baseInfo"] = {
                                         "姓名": _tds[27].text,
                                         "证件号": _tds[33].text,
                                         "证件类型": _tds[31].text,
                                         "个人登记号": _tds[29].text
                                    }
                                    self.result_data["companyList"].append({
                                        "最后业务日期": re.sub('\s', '', _tds[53].text),
                                        "单位名称": _tds[37].text,
                                        "单位登记号": _tds[35].text,
                                        "所属管理部编号": _tds[39].text,
                                        "所属管理部名称": _tds[41].text,
                                        "当前余额": re.sub('\s', '', _tds[43].text),
                                        "帐户状态": _tds[45].text,
                                        "当年缴存金额": re.sub('\s', '', _tds[47].text),
                                        "当年提取金额": re.sub('\s', '', _tds[49].text),
                                        "上年结转余额": re.sub('\s', '', _tds[51].text),
                                        "转出金额": re.sub('\s', '', _tds[55].text)
                                    })

                                detail_tag = result.findAll("span", {"class": "style2"})
                                if len(detail_tag) > 0:
                                    detail_a = detail_tag[1].findAll("a")[0]
                                    detail_link = detail_a.attrs['onclick'].split("'")[1]
                                    detail_link = parse.urljoin(self.g.current_url, detail_link)
                                    detail_resp = self.s.get(detail_link)
                                    detail_result = bs4.BeautifulSoup(detail_resp.content, 'html.parser')
                                    detail_table = detail_result.find("table", {"id": "new-mytable3"})
                                    if detail_table:
                                        detail_trs = detail_table.findAll("tr")
                                        for detail_tr in detail_trs:
                                            detail_tds = detail_tr.findAll("td")
                                            if detail_tr != detail_trs[0]:
                                                date = re.sub('\s', '', detail_tds[0].text)
                                                try:
                                                    self.result_data["detail"]["data"][date[0:4]]
                                                except KeyError:
                                                    self.result_data["detail"]["data"][date[0:4]] = {}
                                                try:
                                                    self.result_data["detail"]["data"][date[0:4]][date[4:6]]
                                                except KeyError:
                                                    self.result_data["detail"]["data"][date[0:4]][date[4:6]] = []
                                                self.result_data["detail"]["data"][date[0:4]][date[4:6]].append({
                                                    "时间": date[0:4] + "-" + date[4:6] + "-" + date[6:],
                                                    "类型": re.sub('\s', '', detail_tds[2].text),
                                                    "汇缴年月": re.sub('\s', '', detail_tds[1].text),
                                                    "收入": re.sub('\s', '', detail_tds[3].text),
                                                    "支出": re.sub('\s', '', detail_tds[4].text),
                                                    "余额": re.sub('\s', '', detail_tds[5].text),
                                                    "单位名称": _tds[37].text
                                                })
                                    pass
                        except:
                            pass

                        i = i + 1

            self.result_identity.update({
                'task_name': self.task_info['city_name'],
                'target_name': name,
                'target_id': target_id,
                'status': paymentStart,
            })
        except InvalidConditionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient

    meta = {'身份证编号': '141031199008250053', '密码': '101169'}
    client = TaskTestClient(Task(prepare_data=dict(meta=meta)))
    client.run()






