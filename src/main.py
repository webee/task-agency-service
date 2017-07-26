from gevent import monkey
from services.test import TestTasksManager

monkey.patch_all()

test_tasks_manager = TestTasksManager()

methods = {
    'test_fetch_start': test_tasks_manager.start,
    'test_fetch_resume': test_tasks_manager.resume,
}

if __name__ == '__main__':
    import zerorpc
    server = zerorpc.Server(methods, name='task-agency-service', heartbeat=30)
    server.bind('tcp://*:12345')
    server.run()
