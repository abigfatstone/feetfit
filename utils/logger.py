# -*- coding: utf-8 -*-
# import json
# import os
# import time
# from datetime import datetime
# from typing import Dict, Union
# pylint: disable=attribute-defined-outside-init
# pylint: disable=missing-function-docstring,missing-class-docstring

import asyncio
import dataclasses
import inspect
import json
import os
import sys
import time
import traceback
from asyncio import sleep as async_sleep
from functools import update_wrapper
from inspect import isasyncgenfunction, iscoroutinefunction
from typing import Any, Dict, Union

from pydantic import BaseModel

from utils import unified_logger
from utils.req_ctx import get_req_ctx

# from utils.encryptor import encrypt_instance
try:
    from cryptography.fernet import Fernet

    from config.config import get_encryption_key

    # 初始化加密器
    encryption_key = get_encryption_key()
    fernet_encryptor = Fernet(encryption_key)
    ENCRYPTION_AVAILABLE = True
except ImportError:
    fernet_encryptor = None
    ENCRYPTION_AVAILABLE = False


# ENV = os.getenv("apollo_aienv", "pro")
# ENV = "prod"


class LogInfo:
    log_enable = True
    log_sensitive_info = False

    log_setter = None

    def set_log_enable(self, enable: bool):
        self.log_enable = enable

    def set_log_sensitive_info(self, sensitive_info: bool):
        self.log_sensitive_info = sensitive_info

    def set_log_obj(self, project_dir, project_name, namespace, path):
        self.log_setter = unified_logger.Logger(project_dir, project_name, namespace, path).log_setter


log_info = LogInfo()


def serialize_input(_input):
    if isinstance(_input, BaseModel):
        return _input.model_dump()
    elif isinstance(_input, list):
        return [serialize_input(item) for item in _input]
    elif isinstance(_input, tuple):
        return tuple(serialize_input(item) for item in _input)
    elif isinstance(_input, dict):
        return {key: serialize_input(value) for key, value in _input.items()}
    else:
        return _input


def mask_info(info: str) -> str:
    length = len(info)
    if length <= 200:
        return info
    else:
        return f"{info[:100]}**********{info[-100:]}"


def log_setter(
    _input: Union[Dict, str] = "",
    level="info",
    encrypted_info="",
    author="",
    error="",
    cost_time=0.0,
    function=None,
    status=200,
    trace_id="",
    msg_id="",
    call_depth=2,  # 新增：调用栈深度参数，默认为2
):
    # 本地开发环境简化逻辑 - 使用新的dev模式
    if os.getenv("LoggerType", "").lower() == "simple":
        from utils.logger_dev import log_setter_dev

        # 调用开发模式的log_setter
        log_setter_dev(
            _input=str(_input),
            level=level,
            function=function or "unknown",
        )
        return

    # 是否开启日志
    log_enable = log_info.log_enable
    if log_enable is False and level in ["info", "warning"]:
        return

    func_name = function or sys._getframe(1).f_code.co_name  # pylint: disable=protected-access

    # 是否开启敏感数据日志
    log_sensitive_info = log_info.log_sensitive_info
    error = error or (traceback.format_exc() if level in ["error", "warning"] else error)

    if log_info.log_setter is None:
        try:
            from config.wellness.config import log_dir, project_dir, project_name

            log_info.set_log_obj(project_dir, project_name, project_name, log_dir)
            print("Auto-initialized log obj with default params from config.wellness.config.")
        except Exception:
            print("Warning: log obj is None.")
            return

    if trace_id == "":
        trace_id = get_req_ctx("trace_id")

    if isinstance(_input, dict):
        _input = serialize_input(_input)
        _input = json.dumps(_input, ensure_ascii=False)

    if isinstance(encrypted_info, dict):
        encrypted_info = serialize_input(encrypted_info)
        encrypted_info = json.dumps(encrypted_info, ensure_ascii=False)

    # 处理 encrypted_info：分别准备文件存储版本和屏幕显示版本
    file_encrypted_info = encrypted_info  # 文件存储版本
    display_encrypted_info = encrypted_info  # 屏幕显示版本

    if ENCRYPTION_AVAILABLE and fernet_encryptor:
        try:
            # 文件存储：加密
            file_encrypted_info = fernet_encryptor.encrypt(encrypted_info.encode()).decode()
            # 屏幕显示：遮蔽
            display_encrypted_info = mask_info(encrypted_info)
        except Exception:
            # 加密失败，全部遮蔽
            file_encrypted_info = mask_info(encrypted_info)
            display_encrypted_info = file_encrypted_info
    else:
        # 无加密，全部遮蔽
        file_encrypted_info = mask_info(encrypted_info)
        display_encrypted_info = file_encrypted_info

    log_info.log_setter(  # pylint: disable=protected-access
        get_req_ctx("data_sensitive_level", "public"),
        str(log_sensitive_info),
        level,
        func_name,
        _input,
        author,
        error,
        float(round(cost_time, 4)) if cost_time is not None else 0.0,
        trace_id=trace_id,
        url=get_req_ctx("path"),
        method=get_req_ctx("method"),
        status=status,
        msg_id=msg_id,
        encrypted_info=file_encrypted_info,  # 文件存储使用完整加密版本
        display_encrypted_info=display_encrypted_info,  # 新增：屏幕显示用遮蔽版本
        call_depth=call_depth,  # 传递调用栈深度
    )


# def input_decider(sensitive_info: str, insensitive_info: str) -> Tuple[str, str]:
#     """
#     给定敏感信息和非敏感信息
#     返回_input和encrypted_info
#     """
#     if LOG_SENSITIVE_INFO:
#         return sensitive_info, ''
#     else:
#         return insensitive_info, sensitive_info


def safe_dump_json(json_str):
    """
    尝试将结果转为json格式,如果失败则返回原始结果
    """
    try:
        json.dumps(json_str)
    except Exception as _:  # pylint: disable=broad-except
        return str(json_str)
    return json_str


def recursion_dump_json(obj):
    """
    递归json obj, 导致无法直接json.dumps的obj转为str
    """
    try:
        dumps_failed = False
        try:
            json.dumps(obj)
        except Exception:
            dumps_failed = True

        if dumps_failed:
            if isinstance(obj, dict):
                new_obj = {}
                for key, value in obj.items():
                    new_obj[str(key)] = recursion_dump_json(value)
                obj = new_obj
            elif isinstance(obj, list):
                new_obj = []
                for _, value in enumerate(obj):
                    new_obj.append(recursion_dump_json(value))
                obj = new_obj
            elif dataclasses.is_dataclass(obj):
                obj = obj.__dict__
            elif isinstance(obj, BaseModel):
                obj = obj.model_dump()
            else:
                obj = str(obj)
        return obj
    except Exception as e:
        log_setter(level="error", _input=f"递归json obj失败: {e}")
        return {}


# Analytic func params
def get_func_params(func, args, kwargs):
    """
    解析函数参数并dumps成字符串返回
    """
    try:
        params = inspect.signature(func).bind(*args, **kwargs).arguments
        _ = params.pop("self") if "self" in params else None
        return recursion_dump_json(params)
    except Exception as e:  # pylint: disable=bare-except
        log_setter(level="error", _input=f"解析函数参数失败: {e}")
        return ""


def attempt_get_model_name(input_params):
    model_name = ""

    # 尝试遍历所有的key-value，读取key为model、model_name的值
    def dp_check(tmp_json):
        if isinstance(tmp_json, dict):
            for key, value in tmp_json.items():
                if isinstance(value, str) and "gpt" in value and key in ["model", "model_name"]:
                    return value
                elif isinstance(value, dict):
                    return dp_check(value)
        return ""

    if isinstance(log_items_input := input_params.get("_input", {}), dict):
        model_name = log_items_input.get("model_name", "")
        model_name = model_name or log_items_input.get("kwargs", {}).get("model", "") or dp_check(log_items_input)

    return model_name


class OutputTypeException(Exception):
    def __init__(self, message):
        super().__init__(message)


class LogDecorate:
    def __init__(
        self,
        raise_exc: bool = False,
        failsafe: Any = "ERROR",
        log_input: bool = True,
        log_output: bool = True,
        func_name: str = "",
        only_fail: bool = False,
        error_to_warn: bool = False,
        retry_times: int = 0,
        retry_interval: float = 0.1,
        skip_exceptions: list = [],
        my_exception: Union[BaseException, None] = None,
        check_output: bool = False,
        timeout: Union[float, int, None] = None,
        total_timeout: Union[float, int, None] = None,
    ):
        """
        raise_fail: Boolen 是否将异常抛出
        failsafe: Any 异常时返回的默认值
        log_input: Boolen 是否记录输入
        log_output: Boolen 是否记录返回值
        func_name: str 日志打印对应的函数名
        retry_times: int 函数执行错误情况下的重试次数
        only_fail: bool 是否只记录失败的日志, 默认为False, True情况下只记录warning和error日志
        error_to_warn: bool 是否将error级别的日志转为warning级别
        retry_interval: float 重试间隔
        skip_exceptions: list 指定异常不做重试处理、日志为warning级别
        my_execption: 返回指定的异常
        check_output: bool 是否检查返回值类型，在设置failsafe的前提下，如果开启检查，返回值类型和failsafe不一致则返回failsafe并记录异常
        timeout: float 超时时间, 单位是秒， 只对异步函数有效, 每次重试超时时间
        total_timeout: float 总超时时间, 单位是秒， 只对异步函数有效, 无论重试多少次，总时间不超过total_timeout
        """
        self.raise_exc = raise_exc
        self.failsafe = failsafe
        self.log_input = log_input
        self.log_output = log_output
        self.func_name = func_name
        self.only_fail = only_fail
        self.error_to_warn = error_to_warn
        self.retry_times = retry_times
        self.retry_interval = retry_interval
        self.skip_exceptions = skip_exceptions
        self.my_exception = my_exception
        self.check_output = check_output
        self.timeout = timeout
        self.total_timeout = total_timeout

    def __call__(self, func) -> Any:
        self.load_params(func)

        async def async_gen_func(*args, **kwargs):
            async for i in self.async_gen_func(*args, **kwargs):
                yield i

        async def async_func(*args, **kwargs):
            return await self.async_func(*args, **kwargs)

        def sync_func(*args, **kwargs):
            return self.sync_func(*args, **kwargs)

        if isasyncgenfunction(func):
            wrapped = async_gen_func
        elif iscoroutinefunction(func):
            wrapped = async_func
        else:
            wrapped = sync_func

        update_wrapper(wrapped, func)
        return wrapped

    def load_params(self, func):
        self._func = func
        self.func_name = self.func_name or func.__name__
        # retry_times为0方便用户理解，0转为1方便代码逻辑处理
        self.retry_times = self.retry_times or 1

    async def async_gen_func(self, *args, **kwargs):
        _start_time, _local_retry_times, _error_msg, _error_obj, _log_items = self.before_call(self._func, args, kwargs)
        return_items = ""
        min_time_interval = 0
        max_time_interval = 0
        avg_time_interval = 0
        last_time = time.time()
        yield_count = 0
        first_rep = True

        while _local_retry_times > 0:
            try:
                async for value in self._func(*args, **kwargs):
                    return_items += str(value)

                    if first_rep:
                        first_rep = False
                        log_setter(
                            function="{{first rep}}" + self.func_name,
                            _input={"first rep": return_items},
                            cost_time=round((time.time() - last_time) * 1000, 2),
                            # model_name=attempt_get_model_name(_log_items),
                        )

                    # 统计平均耗时、最大耗时、最小耗时
                    curr_time = time.time()
                    min_time_interval = min(min_time_interval, (curr_time - last_time))
                    max_time_interval = max(max_time_interval, (curr_time - last_time))
                    yield_count += 1
                    last_time = curr_time
                    avg_time_interval = (curr_time - _start_time) / yield_count
                    yield value
                _error_obj, _error_msg = self.__check_output(return_items)
                break
            except Exception as e:  # pylint: disable=broad-except
                _local_retry_times, _error_obj, _error_msg = await self.exception_handler(
                    e, _local_retry_times, _error_obj, _error_msg
                )

        _log_items["time_delay_analysis"] = {
            "min_time_interval": round(min_time_interval * 1000, 2),
            "max_time_interval": round(max_time_interval * 1000, 2),
            "avg_time_interval": round(avg_time_interval * 1000, 2),
            "count": yield_count,
        }

        _log_items, _error_obj, _error_msg, _start_time, _local_retry_times = self.after_call(
            return_items,
            _log_items,
            _error_obj,
            _error_msg,
            _start_time,
            _local_retry_times,
        )

        # 返回值处理
        if not _error_obj:
            ...
        elif self.raise_exc:
            raise _error_obj
        elif self.failsafe is not None:
            yield self.failsafe

    async def async_func(self, *args, **kwargs):
        result = None

        _start_time, _local_retry_times, _error_msg, _error_obj, _log_items = self.before_call(self._func, args, kwargs)
        while _local_retry_times > 0 and (self.total_timeout is None or time.time() - _start_time < self.total_timeout):
            try:
                if self.timeout is None:
                    result = await self._func(*args, **kwargs)
                else:
                    result = await asyncio.wait_for(self._func(*args, **kwargs), timeout=self.timeout)
                _error_obj, _error_msg = self.__check_output(result)
                break
            except Exception as e:  #  pylint: disable=broad-except
                _local_retry_times, _error_obj, _error_msg = await self.exception_handler(
                    e, _local_retry_times, _error_obj, _error_msg
                )

        _log_items, _error_obj, _error_msg, _start_time, _local_retry_times = self.after_call(
            result,
            _log_items,
            _error_obj,
            _error_msg,
            _start_time,
            _local_retry_times,
        )
        # 返回值处理
        if not _error_obj:
            ...
        elif self.raise_exc:
            raise _error_obj
        elif self.failsafe is not None:
            result = self.failsafe

        return result

    def sync_func(self, *args, **kwargs):
        result = None
        _start_time, _local_retry_times, _error_msg, _error_obj, _log_items = self.before_call(self._func, args, kwargs)
        while _local_retry_times > 0:
            try:
                result = self._func(*args, **kwargs)
                _error_obj, _error_msg = self.__check_output(result)
                break
            except Exception as e:  #  pylint: disable=broad-except
                # _local_retry_times, _error_obj, _error_msg = asyncio.run(
                #     self.exception_handler(e, _local_retry_times, _error_obj, _error_msg)
                # )
                _local_retry_times, _error_obj, _error_msg = 0, e, str(e)
        _log_items, _error_obj, _error_msg, _start_time, _local_retry_times = self.after_call(
            result,
            _log_items,
            _error_obj,
            _error_msg,
            _start_time,
            _local_retry_times,
        )
        # 返回值处理
        if not _error_obj:
            ...
        elif self.raise_exc:
            raise _error_obj
        elif self.failsafe is not None:
            result = self.failsafe

        return result

    # 通用处理逻辑
    def before_call(self, func, args, kwargs):
        # pylint: disable=attribute-defined-outside-init
        _start_time = time.time()
        _local_retry_times = self.retry_times
        _error_msg = ""
        _error_obj = None
        _log_items = {}
        if self.log_input:
            _log_items["_input"] = get_func_params(func, args, kwargs)

        return _start_time, _local_retry_times, _error_msg, _error_obj, _log_items

    def __check_output(self, result):
        _error_obj = None
        _error_msg = ""
        try:
            if self.failsafe is not None and self.check_output is True:
                if not isinstance(result, type(self.failsafe)):
                    _error_obj = OutputTypeException(
                        f"Return type error, expect {type(self.failsafe)}, but got {type(result)}"
                    )
                    _error_msg = str(_error_obj)
        except Exception as e:
            log_setter(
                level="warning",
                error="logger checkout error: " + str(e) + "\t" + traceback.format_exc(),
            )

        return _error_obj, _error_msg

    def after_call(
        self,
        result,
        _log_items,
        _error_obj,
        _error_msg,
        _start_time,
        _local_retry_times,
    ):
        # 后处理
        if self.log_output:
            _log_items["_output"] = recursion_dump_json(result)
        retry_message = ""
        if _error_obj and self.retry_times > 1:
            retry_message = f"\nFailed after {self.retry_times - _local_retry_times} retries."
        elif _error_obj and _local_retry_times - self.retry_times > 0:
            retry_message = f"\nSuccessful after {_local_retry_times - self.retry_times} retries."

        # 结束日志
        if self.only_fail is False or _error_obj:
            if _error_obj:
                if self.error_to_warn:
                    level = "warning"
                elif isinstance(_error_obj, tuple(self.skip_exceptions)):  # type: ignore
                    level = "warning"
                else:
                    level = "error"
            else:
                level = "info"

            log_setter(
                level=level,
                function="{{Done}}" + self.func_name,
                # _input=_log_items,
                error=_error_msg + retry_message,
                cost_time=round((time.time() - _start_time) * 1000, 2),
                encrypted_info=_log_items,
                call_depth=2,
                # model_name=attempt_get_model_name(_log_items),
            )
        return _log_items, _error_obj, _error_msg, _start_time, _local_retry_times

    async def exception_handler(self, exc_obj, _local_retry_times, _error_obj, _error_msg):
        # 针对skip_exceptions,直接重试次数为0
        if isinstance(exc_obj, tuple(self.skip_exceptions)):  # type: ignore
            _local_retry_times = 1

        _local_retry_times -= 1
        if _local_retry_times > 0:
            await async_sleep(self.retry_interval)
        _error_obj = exc_obj
        _error_msg = str(exc_obj) + "\t" + traceback.format_exc()

        return _local_retry_times, _error_obj, _error_msg


class ExecutionTimeLogger:
    """
    异常上下文管理器
    对代码块自动进行计时，记录日志, 并且捕获异常
    可代替try except
    """

    def __init__(
        self,
        level="info",
        _input="",
        author="",
        function="",
        is_error=True,
        catch_exc=True,
    ) -> None:
        self.level = level
        self._input = _input
        self.author = author
        self.function = function
        self.is_error = is_error
        self.catch_exc = catch_exc
        self.error_msg = ""

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        execution_time = round((end_time - self.start_time) * 1000, 2)

        if exc_tb:
            self.level = "error" if self.is_error else "warning"
            self.error_msg = str(traceback.format_exception(exc_type, exc_val, exc_tb))

        log_setter(
            level=self.level,
            _input=self._input,
            author=self.author,
            cost_time=execution_time,
            function=self.function or sys._getframe(1).f_code.co_name,
            error=self.error_msg,
        )

        return self.catch_exc


def startup_logger(enable, sensitive_info, project_dir, project_name, log_namespace, log_path):
    print("startup logger done.")
    log_info.set_log_enable(enable)
    log_info.set_log_sensitive_info(sensitive_info)
    log_info.set_log_obj(project_dir, project_name, log_namespace, log_path)
