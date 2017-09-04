from services.service import AbsTaskUnitSessionTask
from services.service import SessionData
from services.service import AskForParamsError, PreconditionNotSatisfiedError, TaskAbortedError


class Task(AbsTaskUnitSessionTask):
    def _prepare(self):
        """恢复状态，初始化结果"""
        super()._prepare()
        # state
        # state: dict = self.state
        # TODO: restore from state

        # result
        # result: dict = self.result
        # TODO: restore from result

    def _update_session_data(self):
        """保存任务状态"""
        super()._update_session_data()
        # state
        # state: dict = self.state
        # TODO: update state

        # result
        # result: dict = self.result
        # TODO: update temp result

    def _query(self, params: dict):
        """任务状态查询"""
        pass

    def _setup_task_units(self):
        """设置任务执行单元"""
        self._add_unit(self._unit_login)
        self._add_unit(self._unit_fetch, self._unit_login)

    def _unit_login(self, params=None):
        err_msg = None
        if params:
            # 使用提供的参数进行登录
            # TODO: 如果登录成功，则return
            # 否则raise AskForParamsError
            pass

        # key, name, cls
        #   input:, :password
        #       placeholder
        #       value
        #   data:, :image
        #       query
        raise AskForParamsError([
            dict(key='id_num', name='身份证号', cls='input'),
            dict(key='account_num', name='个人编号', cls='input'),
            dict(key='vc', name='验证码', cls='data:image', query={'t': 'vc'}),
        ], err_msg)

    def _unit_fetch(self):
        try:
            # TODO: 执行任务，如果没有登录，则raise PermissionError
            return
        except PermissionError as e:
            raise PreconditionNotSatisfiedError(e)


if __name__ == '__main__':
    from services.client import TaskTestClient
    client = TaskTestClient(Task(SessionData()))
    client.run()
