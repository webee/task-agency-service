from services.service import AbsSessionTask
from PIL import Image
import io


class TestClient(object):
    def __init__(self, task: AbsSessionTask):
        self.task = task

    def run(self):
        res = self.task.run()
        while True:
            # check ret
            ret = res['ret']
            if not ret:
                print('err_msg: ', res['err_msg'])
                break

            # check done
            done = res['done']
            if done:
                print('ret: ', res['data'])
                print('result: ', self.task.result)
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
                elif pr['cls'] == 'data:image':
                    data = pr['data']
                    while True:
                        content = data['content']
                        Image.open(io.BytesIO(content)).show()
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
