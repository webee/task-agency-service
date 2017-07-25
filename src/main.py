from tasks.test.mock import UserAgent, LogRequestFilter
from tasks.test.mock_site import TestSite


if __name__ == '__main__':
    ua = UserAgent(TestSite())
    ua.register_request_filter(LogRequestFilter())
    print(ua.get_vc())
    vc = input("vc:")
    print(ua.login('a', 'b', vc))

    print(ua.get_vc())
    vc = input("vc:")
    print(ua.s(vc='vc'))
