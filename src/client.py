import zerorpc
from services.client import TaskTestClient, ZeroRPCSessionTask


if __name__ == '__main__':
    c = zerorpc.Client()
    c.connect('tcp://127.0.0.1:12345')

    client = TaskTestClient(ZeroRPCSessionTask(c, 'test', 'simple'))
    client.run()
