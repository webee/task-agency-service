class InvalidParamsError(Exception):
    """参数不正常异常
    如果发现参数不正常，则抛此异常或者AssertionError
    """
    pass


class AskForParamsError(Exception):
    def __init__(self, param_requirements, err_msg=None, details=None, message='parameters required'):
        """
        请求参数异常
        :param param_requirements: 需要的参数说明
        :param err_msg: 参数检查错误
        :param details: 可能的需求细节
        :param message: 异常信息
        """
        super().__init__(message)
        self.param_requirements = param_requirements
        self.err_msg = err_msg
        self.details = details


class TaskNotAvailableError(Exception):
    """任务不可用异常
    任务目标不可用时，抛此异常
    """
    pass


class TaskNotImplementedError(TaskNotAvailableError):
    """任务未实现异常
    任务功能未完全实现时，抛此异常
    """
    pass


class InvalidConditionError(Exception):
    """条件不正常异常
    检查发现执行环境不满足时，抛此异常
    """
    pass


class PreconditionNotSatisfiedError(Exception):
    """前置条件不满足异常"""
    pass
