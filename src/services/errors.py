class InvalidParamsError(Exception):
    """参数不正常异常"""
    pass


class AskForParamsError(Exception):
    def __init__(self, param_requirements, err_msg=None, message='parameters required'):
        """
        请求参数异常
        :param param_requirements: 需要的参数说明
        :param err_msg: 参数检查错误
        :param message: 异常信息
        """
        super().__init__(message)
        self.param_requirements = param_requirements
        self.err_msg = err_msg


class TaskUnavailableError(Exception):
    """任务不可用异常"""
    pass


class InvalidConditionError(Exception):
    """条件不正常异常"""
    pass


class PreconditionNotSatisfiedError(Exception):
    """前置条件不满足异常"""
    pass
