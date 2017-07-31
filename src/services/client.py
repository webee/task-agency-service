from services.service import AbsStatefulTask, AbsSessionTask
from PIL import Image
import io
import getpass


class TaskTestClient(object):
    def __init__(self, task: AbsStatefulTask):
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
                if isinstance(self.task, AbsSessionTask):
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
                if pr['cls'] == 'input:password':
                    # params[pr['key']] = getpass.getpass('%s: ' % pr['name'])
                    params[pr['key']] = input('%s: ' % pr['name'])
                elif pr['cls'] == 'data':
                    while True:
                        # query data
                        r = self.task.query(pr['query'])
                        if not r['ret']:
                            print('error:', r['err_msg'])
                            continue
                        data = r['data']

                        print('content: %s' % data['content'])
                        d = input('%s: ' % pr['name'])
                        if d:
                            break
                    params[pr['key']] = d
                elif pr['cls'] == 'data:image':
                    while True:
                        # query data
                        r = self.task.query(pr['query'])
                        if not r['ret']:
                            print('error:', r['err_msg'])
                            continue
                        data = r['data']

                        content = data['content']
                        Image.open(io.BytesIO(content)).show()
                        d = input('%s: ' % pr['name'])
                        if d:
                            break
                    params[pr['key']] = d
            res = self.task.run(params)


class ZeroRPCSessionTask(AbsStatefulTask):
    def __init__(self, client, service, task_id):
        super().__init__()
        self.client = client
        self._service = service
        self._task_id = task_id
        self._session_id = ''

    def query(self, params: dict = None):
        return self.client('%s_task_query' % self._service, params)

    def run(self, params: dict = None):
        if self._session_id:
            return self.client('%s_task_resume' % self._service, self._session_id, params)
        else:
            self._session_id, res = self.client('%s_task_start' % self._service, self._task_id, params)
            return res
