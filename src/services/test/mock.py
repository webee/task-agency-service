import logging
import random
import string
from abc import ABCMeta, abstractmethod
from collections import namedtuple
from functools import wraps
from hashlib import md5
import pickle


def hash_str(s):
    return md5(s.encode()).hexdigest()


def hash_bin(b):
    return md5(b).hexdigest()


def rand_str(size):
    chars = string.digits + string.ascii_letters
    return ''.join(random.choice(chars) for _ in range(size))


class Request(object):
    def __init__(self, method):
        self.method = method
        self.meta = {}
        self.session = {}
        self.args = ()
        self.kwargs = {}

    def get_session(self, key):
        return self.session.get(key)

    def __repr__(self):
        return repr({
            'method': self.method,
            'meta': self.meta,
            'session': self.session,
            'args': self.args,
            'kwargs': self.kwargs
        })

    def __str__(self):
        return repr(self)


class Response(object):
    def __init__(self, method):
        self.method = method
        self.meta = {}
        self.session = {}
        self.data = None

    def del_session(self, key):
        if key in self.session:
            del self.session[key]

    def add_session(self, key, val):
        self.session[key] = val

    def __repr__(self):
        return repr({
            'method': self.method,
            'meta': self.meta,
            'session': self.session,
            'data': self.data
        })

    def __str__(self):
        return repr(self)


def extract_req_resp(*args):
    idx = 0
    for i, arg in enumerate(args):
        if isinstance(arg, Request):
            idx = i
            break
    req, resp = args[idx:idx+2]
    return idx, req, resp


def expanded_method(get_args=None):
    def _method(f):
        @wraps(f)
        def _wrap(*args, **kwargs):
            idx, req, resp = extract_req_resp(*args)
            if get_args is not None:
                args = get_args(args, idx, req, resp)
            else:
                args = [] + list(args[:idx]) + [req, resp] + list(req.args)
            resp.data = f(*args, **req.kwargs)
        return _wrap
    return _method


req_method = expanded_method(lambda args, idx, req, resp: [] + list(args[:idx]) + [req] + list(req.args))
resp_method = expanded_method(lambda args, idx, req, resp: [] + list(args[:idx]) + [resp] + list(req.args))
pure_method = expanded_method(lambda args, idx, req, resp: [] + list(args[:idx]) + list(req.args))
req_resp_method = expanded_method(lambda args, idx, req, resp: [] + list(args[:idx]) + [req, resp] + list(req.args))


MiddlewareWithMethods = namedtuple('MiddlewareWithMethods', ['methods', 'middleware'])


class AbsSite(metaclass=ABCMeta):
    def __init__(self):
        super().__init__()
        self.middlewares = []

    def request(self, req):
        method = req.method
        if not hasattr(self, method) or not callable(getattr(self, method)):
            raise NotImplementedError()

        resp = Response(method)
        resp.session = req.session

        f = getattr(self, method)
        for mwm in self.middlewares:
            if not mwm.methods or method in mwm.methods:
                f = lambda req, resp: mwm.middleware(req, resp, f)

        f(req, resp)

        return resp

    def register_middleware(self, methods, *middlewares):
        self.middlewares.extend([MiddlewareWithMethods(methods, m) for m in reversed(middlewares)])


class RequestMiddleware(metaclass=ABCMeta):
    def __call__(self, req, resp, f):
        self.do(req, f)

    @abstractmethod
    def do(self, req, resp, f):
        f(req, resp)


def _hash_user(user):
    return hash_bin(pickle.dumps(user) + b'abc.xyz')


def login_user(resp, user):
    resp.add_session('user', user)
    resp.add_session('user_hash', _hash_user(user))


def logout_user(resp):
    resp.del_session('user')
    resp.del_session('user_hash')


def login_required(f):
    @wraps(f)
    def _wrap(*args, **kwargs):
        _, req, resp = extract_req_resp(*args)
        user = req.session.get('user')
        user_hash = req.session.get('user_hash')
        if not user or not user_hash or _hash_user(user) != user_hash:
            raise PermissionError("login required")
        f(*args, **kwargs)

    return _wrap


class UserAgent(object):
    def __init__(self, site, session=None):
        super().__init__()
        self.site = site
        self.session = session or {}
        self.meta = {}

    def set_meta(self, key, val):
        self.meta[key] = val

    def del_meta(self, key):
        del self.meta[key]

    def __call__(self, method, *args, **kwargs):
        req = Request(method)
        req.meta = self.meta
        req.session = self.session
        req.args = args
        req.kwargs = kwargs

        resp = self._request(req)
        self.session = resp.session

        return resp.data

    def _request(self, req):
        return self.site.request(req)

    def register_request_filter(self, *req_filters):
        for req_filter in reversed(req_filters):
            _request = self._request
            self._request = lambda req: req_filter(req, _request)

    def __getattr__(self, method):
        return lambda *args, **kwargs: self(method, *args, **kwargs)


class BaseRequestFilter(metaclass=ABCMeta):
    def __call__(self, req, next_request):
        return self.do_filter(req, next_request)

    @abstractmethod
    def do_filter(self, req, next_request):
        return next_request(req)


class LogRequestFilter(BaseRequestFilter):
    def __init__(self):
        self.logger = logging.getLogger('request.filter.log')

    def do_filter(self, req, next_request):
        self.logger.debug('req: %s', req)
        resp = next_request(req)
        self.logger.debug('resp: %s', resp)

        return resp
