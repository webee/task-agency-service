from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver


def create_driver():
    caps = {}
    caps.update(webdriver.DesiredCapabilities.PHANTOMJS)
    caps["phantomjs.page.settings.userAgent"] = ("Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0")
    caps["phantomjs.page.settings.loadImages"] = False
    driver = webdriver.Remote(command_executor='http://127.0.0.1:4444/wd/hub',
                              desired_capabilities=caps, keep_alive=False)

    driver.implicitly_wait(20)

    driver.execute_script("""
    var window = this;
    window.alert = function(msg){console.log('abc.xyz');document.cookie='_last_alert=' + escape(msg);};
    window.confirm = function(msg) {return true;};
    """)

    return driver


class DriverRequestsCoordinator(object):
    def __init__(self, d=None, s=None, create_driver=None, create_session=None):
        """同步web driver和requests session的cookie, 逻辑上driver先于session
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

        self._d_n = 0
        self._s_n = 0

    @property
    def d_is_created(self):
        return self._d is not None

    @property
    def d(self) -> RemoteWebDriver:
        if self._d:
            return self._d

        self._d = self._create_driver()
        self.inc_and_sync_d_cookies()
        return self._d

    @property
    def s(self):
        if self._s:
            return self._s

        self._s = self._create_session()
        return self._s

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

        for c in list(self.s.cookies):
            self.d.add_cookie(dict(name=c.name, value=c.value, path=c.path, secure=c.secure))

        self._d_n = self._s_n

    def inc_and_sync_s_cookies(self):
        self.inc_s()
        self.sync_s_cookies()

    def sync_d_cookies(self):
        """同步web driver的cookie到requests session"""
        if self._d_n <= self._s_n:
            return

        for c in self.d.get_cookies():
            cx = dict(name=c['name'], path=c['path'], domain=c['domain'], value=c['value'], secure=c['secure'])
            self.s.cookies.set(**cx)
        self._s_n = self._d_n

    def inc_and_sync_d_cookies(self):
        self.inc_d()
        self.sync_d_cookies()
