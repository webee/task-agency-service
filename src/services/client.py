from services.service import AbsSessionTask


class TestClient(object):
    def __init__(self, task: AbsSessionTask):
        self.task = task

    def run(self):
        res = self.task.run()
        while True:
            # check ret
            ret = res['ret']
            if not ret:
                print(res['err_msg'])
                break

            # check done
            done = res['done']
            if done:
                print(res['data'])
                break

            # check error msg
            err_msg = res.get('err_msg')
            if err_msg:
                print('error:', err_msg)

            # collect parameters
            params = {}
            param_requirements = res['param_requirements']
            for pr in param_requirements:
                # parse parameter requirements
                if pr['cls'] == 'input':
                    params[pr['key']] = input('%s: ' % pr['name'])
                elif pr['cls'] == 'data':
                    data = pr['data']
                    while True:
                        print('data: %s' % data)
                        d = input('%s: ' % pr['name'])
                        if d:
                            break

                        # refresh data
                        r = self.task.query(pr['query'])
                        if r['ret']:
                            data = r['data']
                        else:
                            print('error:', r['err_msg'])
                    params[pr['key']] = d
            res = self.task.run(params)
