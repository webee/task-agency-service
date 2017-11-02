import os
import logging
import traceback
from contextlib import contextmanager
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver


logger = logging.getLogger(__name__)


def create_driver(user_agent=None):
    """连接远程有driver"""
    caps = {}
    caps.update(webdriver.DesiredCapabilities.PHANTOMJS)
    caps["phantomjs.page.settings.userAgent"] = user_agent or "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0"
    caps["phantomjs.page.settings.loadImages"] = False
    driver = webdriver.Remote(command_executor='http://127.0.0.1:4444/wd/hub',
                              desired_capabilities=caps, keep_alive=False)

    driver.implicitly_wait(20)

    driver.execute_script("""
    var window = this;
    window.alert = function(msg){document.cookie='_last_alert=' + escape(msg);};
    window.confirm = function(msg) {return true;};
    """)

    return driver


class DriverType(object):
    PHANTOMJS = 0
    CHROME = 1


def new_driver(driver_type=DriverType.PHANTOMJS, **kwargs):
    if driver_type == DriverType.PHANTOMJS:
        return new_phantomjs_driver(**kwargs)
    elif driver_type == DriverType.CHROME:
        return new_chrome_driver(**kwargs)

    raise RuntimeError('unknown driver type')


def new_chrome_driver(*args, **kwargs):
    options = webdriver.ChromeOptions()
    # prefs = {"profile.managed_default_content_settings.images": 2}
    # options.add_experimental_option("prefs", prefs)
    cap = webdriver.DesiredCapabilities.CHROME
    cap['loggingPrefs'] = {'browser': 'ALL'}

    driver = webdriver.Chrome(chrome_options=options, desired_capabilities=cap)

    return driver


def new_phantomjs_driver(*args, user_agent=None, js_re_ignore='/^$/g', **kwargs):
    """实例化一个PhantomJS driver"""
    service_args = []
    service_args.append('--load-images=no')
    service_args.append('--disk-cache=yes')
    service_args.append('--ignore-ssl-errors=true')
    caps = {}
    caps.update(webdriver.DesiredCapabilities.PHANTOMJS)
    caps["phantomjs.page.settings.userAgent"] = user_agent or "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0"
    caps["phantomjs.page.settings.loadImages"] = False
    service_log_path = None
    if os.path.exists('/tmp'):
        service_log_path = '/tmp/ghostdriver.log'
    driver = webdriver.PhantomJS(service_args=service_args, desired_capabilities=caps, service_log_path=service_log_path)
    driver.set_window_size(1920, 1080)
    driver.implicitly_wait(10)

    driver.command_executor._commands['executePhantomScript'] = ('POST', '/session/$sessionId/phantom/execute')
    # 不加载某些url
    script = """
        var page = this;
        page.onResourceRequested = function(requestData, networkRequest) {
            var match = requestData.url.match(%s);
            if (match != null) {
                //networkRequest.cancel(); // or .abort()
                networkRequest.abort();
            } else {
                page.browserLog.push('request: ' + requestData.url + ': ' + JSON.stringify(requestData));
            }
        }
        page.onResourceReceived = function(response) {
            page.browserLog.push('response: ' + response.url + ': ' + JSON.stringify(response));
        }
        page.onUrlChanged = function(targetUrl) {
            page.browserLog.push('-> ' + targetUrl);
        }
        page.customHeaders = {'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.6,en;q=0.4,ja;q=0.2,la;q=0.2'}
        
        // alert
        page.onAlert = function(msg){
            console.log('ALERT: ' + msg);
            page.browserLog.push('alert: ' + msg);
            page.addCookie({name: '_last_alert', value: escape(msg)});
        }
        /*
        page.alert = function(msg){
            page.browserLog.push('alert: ' + msg);
            page.addCookie({name: '_last_alert', value: escape(msg)});
        }
        page.confirm = function(msg) {return true;}
        */
        """ % js_re_ignore
    driver.execute('executePhantomScript', {'script': script, 'args': []})

    return driver


class DriverRequestsCoordinator(object):
    def __init__(self, d=None, s=None, create_driver=None, create_session=None):
        """同步web driver和requests session的cookie
        :param d: web driver
        :param s: requests session
        :param create_driver: driver factory
        :param create_session: session factory
        """
        assert d or create_driver, '无法确定driver'
        assert s or create_session, '无法确定session'

        self._d = d
        self._s = s
        self._create_driver = create_driver
        self._create_session = create_session

        self._d_n = 1 if self._d is not None else 0
        self._s_n = 1 if self._s is not None else 0

    @property
    def d_is_created(self):
        return self._d is not None

    def d_quit(self, do_sync=True):
        if self.d_is_created:
            if do_sync:
                # 同步cookie到session
                self.inc_and_sync_d_cookies()
            self.d.quit()
            self._d = None
            self._d_n = 0

    @property
    def d(self) -> RemoteWebDriver:
        if self._d:
            return self._d

        self._d = self._create_driver()
        self.sync_s_cookies()
        return self._d

    @property
    def s(self):
        if self._s:
            return self._s

        self._s = self._create_session()
        self.sync_d_cookies()
        return self._s

    @contextmanager
    def get_driver_ctx(self, do_quit=True, do_sync=True, excepted_exceptions=()):
        try:
            yield self.d
        except excepted_exceptions:
            # 为了兼容老方法
            do_quit = False
            raise
        except Exception:
            raise
        finally:
            if do_quit:
                self.d_quit(do_sync)

    def create_driver(self):
        return self.d

    def create_session(self):
        return self.s

    def inc_d(self):
        """driver前进"""
        self._d_n += 1

    def inc_s(self):
        """session前进"""
        self._s_n += 1

    def sync_s_cookies(self):
        """同步requests session的cookie到web driver"""
        if self._s_n <= self._d_n:
            return

        if not (self._d and self._s):
            return

        self._d.delete_all_cookies()
        with_domain = self._d.current_url == 'about:blank'
        for c in list(self._s.cookies):
            try:
                d = dict(name=c.name, value=c.value, path=c.path)
                if with_domain:
                    d['domain'] = c.domain
                self._d.add_cookie(d)
            except:
                logger.debug(traceback.format_exc())

        self._d_n = self._s_n

    def inc_and_sync_s_cookies(self):
        self.inc_s()
        self.sync_s_cookies()

    def sync_d_cookies(self):
        """同步web driver的cookie到requests session"""
        if self._d_n <= self._s_n:
            return

        if not (self._s and self._d):
            return

        self._s.cookies.clear()
        for c in self._d.get_cookies():
            cx = dict(name=c['name'], path=c['path'], domain=c['domain'], value=c['value'], secure=c['secure'])
            self._s.cookies.set(**cx)
        self._s_n = self._d_n

    def inc_and_sync_d_cookies(self):
        self.inc_d()
        self.sync_d_cookies()
