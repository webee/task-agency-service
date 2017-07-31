import random
from .mock import AbsSite, hash_str, rand_str
from .mock import login_user, login_required, logout_user
from .mock import req_method, resp_method, req_resp_method, pure_method


class TestSite(AbsSite):
    def __init__(self):
        super().__init__()
        # db
        self.users = {}
        self._gen_users()

    def _gen_users(self):
        self.users = {
            'a': {'username': 'a', 'password': 'b', 'x': random.randint(1, 3), 's': 'webee'},
            'c': {'username': 'c', 'password': 'd', 'x': random.randint(4, 6), 's': 'loves'},
            'x': {'username': 'x', 'password': 'y', 'x': random.randint(7, 9), 's': 'vivian'},
        }

    @req_resp_method
    def login(self, req, resp, username, password, vc):
        session = req.session
        hashed_vc = hash_str(vc.lower())
        if hashed_vc != session.get('vc'):
            raise ValueError('vc error')
        user = self.users.get(username)
        if not user:
            raise ValueError('user/password error')

        if user['password'] != password:
            raise ValueError('user/password error')

        login_user(resp, username)
        resp.del_session('vc')

        # regenerate users
        self._gen_users()


    @staticmethod
    @resp_method
    def logout(resp):
        logout_user(resp)
        return True

    @staticmethod
    @resp_method
    def get_vc(resp):
        vc = rand_str(4)
        resp.add_session('vc', hash_str(vc.lower()))
        return '*' + vc + '*'

    @pure_method
    def user_count(self):
        return len(self.users)

    @login_required
    @req_method
    def x(self, req):
        username = req.session.get('user')
        user = self.users[username]

        return user['x']

    @login_required
    @req_resp_method
    def s(self, req, resp, vc=''):
        session = req.session
        hashed_vc = hash_str(vc.lower())
        if hashed_vc != session.get('vc'):
            raise ValueError('vc error')
        resp.del_session('vc')

        username = req.session.get('user')
        user = self.users[username]

        return user['s']

    @login_required
    @req_method
    def update_x(self, req, x):
        username = req.get_session('user')
        user = self.users[username]
        user['x'] = x

        return True

    @login_required
    @req_method
    def add(self, req, n=0):
        username = req.session.get('user')
        user = self.users[username]

        return user['x'] + n
