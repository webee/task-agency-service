class Calc(object):
    def __init__(self, state=None):
        self.state = state or {}

    def __call__(self, *args, **kwargs):
        pass

    @property
    def s(self):
        return self.state['s']

    def run(self):
        if self.s == 'pre_add':
            pass
        elif self.s == 'pre_mul':
            pass
        pass

    def pre_add(self, params):
        try:
            pass
        except:
            pass
        pass

    def add(self, a, b):
        self.state['s'] = a + b

    def mul(self, n):
        self.state['res'] = self.state['s'] + n
