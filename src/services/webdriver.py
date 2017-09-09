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


def new_driver(user_agent=None):
    """实例化一个PhantomJS driver"""
    service_args = []
    service_args.append('--ignore-ssl-errors=true')
    service_args.append('--webdriver-logfile=/tmp/ghostdriver.log')
    caps = {}
    caps.update(webdriver.DesiredCapabilities.PHANTOMJS)
    caps["phantomjs.page.settings.userAgent"] = user_agent or "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0"
    caps["phantomjs.page.settings.loadImages"] = False
    driver = webdriver.PhantomJS(service_args=service_args, desired_capabilities=caps)
    driver.implicitly_wait(10)

    driver.execute_script("""
        var window = this;
        window.alert = function(msg){document.cookie='_last_alert=' + escape(msg);};
        window.confirm = function(msg) {return true;};
    """)

    driver.command_executor._commands['executePhantomScript'] = ('POST', '/session/$sessionId/phantom/execute')

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

    def d_quit(self):
        if self.d_is_created:
            self.d.quit()
            self._d = None

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
    def get_driver_ctx(self, quit=True, excpeted_exceptions=()):
        try:
            yield self.d
        except excpeted_exceptions:
            raise
        except Exception:
            logger.warning(traceback.format_exc())
        if quit:
            self.d_quit()

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

        if not (self._d and self.s):
            return

        for c in list(self.s.cookies):
            try:
                self.d.add_cookie(dict(name=c.name, value=c.value, domain=c.domain, path=c.path, secure=c.secure))
            except:
                pass

        self._d_n = self._s_n

    def inc_and_sync_s_cookies(self):
        self.inc_s()
        self.sync_s_cookies()

    def sync_d_cookies(self):
        """同步web driver的cookie到requests session"""
        if self._d_n <= self._s_n:
            return

        if not (self._d and self.s):
            return

        for c in self.d.get_cookies():
            cx = dict(name=c['name'], path=c['path'], domain=c['domain'], value=c['value'], secure=c['secure'])
            self.s.cookies.set(**cx)
        self._s_n = self._d_n

    def inc_and_sync_d_cookies(self):
        self.inc_d()
        self.sync_d_cookies()
