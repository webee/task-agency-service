from gevent import monkey
monkey.patch_all()


def get_test_methods() -> dict:
    from services.service import SessionTasksManager
    from services.service import UUIDSessionIDGenerator
    from services.service import MemorySessionStorage
    from services.service import PathTaskClassFinder

    uuid_session_id_generator = UUIDSessionIDGenerator()
    memory_session_storage = MemorySessionStorage()
    test_task_finder = PathTaskClassFinder(lambda task_id: 'services.test.tasks.t_%s' % task_id, 'Task')
    test_tasks_manager = SessionTasksManager(uuid_session_id_generator,
                                             memory_session_storage,
                                             test_task_finder)
    return {
        'task_start': test_tasks_manager.start,
        'task_resume': test_tasks_manager.resume,
        'task_query': test_tasks_manager.query,
    }


def get_methods():
    methods = {}

    for name, method in get_test_methods().items():
        methods['test_' + name] = method

    return methods


if __name__ == '__main__':
    import zerorpc
    server = zerorpc.Server(get_methods(), name='task-agency-service', heartbeat=30)
    server.bind('tcp://*:12345')
    server.run()
