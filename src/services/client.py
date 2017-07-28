from services.service import SessionTask
from PIL import Image
import io


class TaskTestClient(object):
    def __init__(self, task: SessionTask):
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
                    params[pr['key']] = d
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


class ZeroRPCSessionTask(SessionTask):
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
