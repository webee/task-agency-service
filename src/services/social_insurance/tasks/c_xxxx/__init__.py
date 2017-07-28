from services.service import AbsTaskUnitSessionTask
from services.service import SessionData


class Task(AbsTaskUnitSessionTask):
    def _prepare(self):
        pass

    def _query(self, params: dict):
        pass

    def _setup_task_units(self):
        pass


if __name__ == '__main__':
    from services.client import TestClient
    client = TestClient(Task(SessionData()))
    client.run()
