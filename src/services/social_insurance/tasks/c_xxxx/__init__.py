from services.service import AbsTaskUnitSessionTask
from services.service import SessionData


class Task(AbsTaskUnitSessionTask):
    def _update_session_data(self):
        pass

    def _prepare(self):
        pass

    def _query(self, params: dict):
        pass

    def _setup_task_units(self):
        pass


if __name__ == '__main__':
    from services.client import TaskTestClient
    client = TaskTestClient(Task(SessionData()))
    client.run()
