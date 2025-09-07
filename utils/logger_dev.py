"""
开发模式通用日志封装

提供装饰器和简化的日志记录函数，支持函数调用层级缩进和统一格式化
"""

import functools
import inspect
import os
import traceback
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Callable, Optional

# 使用 ContextVar 确保异步环境下的线程安全
_function_depth: ContextVar[int] = ContextVar("function_depth", default=0)


def _is_simple_mode() -> bool:
    """
    检查是否启用simple模式（缩进模式）

    Returns:
        bool: True表示启用缩进，False表示禁用缩进
    """
    return os.getenv("LoggerType", "").lower() == "simple"


def _get_current_indent() -> str:
    """
    获取当前函数调用层级的缩进字符串

    Returns:
        str: 缩进字符串（制表符），非simple模式返回空字符串
    """
    if not _is_simple_mode():
        return ""

    depth = _function_depth.get(0)
    # 限制最大深度为5，避免层级太多无法阅读
    depth = min(depth, 5)
    return "|\t" * depth


def _increment_depth() -> None:
    """增加函数调用深度，仅在simple模式下有效"""
    if not _is_simple_mode():
        return

    current_depth = _function_depth.get(0)
    # 限制最大深度为5
    if current_depth < 5:
        _function_depth.set(current_depth + 1)


def _decrement_depth() -> None:
    """减少函数调用深度，仅在simple模式下有效"""
    if not _is_simple_mode():
        return

    current_depth = _function_depth.get(0)
    _function_depth.set(max(0, current_depth - 1))


def _format_function_name(function_name: str) -> str:
    """
    格式化函数名，确保长度一致便于阅读

    规则：
    1. 只保留最后两段（按.分割）
    2. 总长度固定为25个字符
    3. 如果超过25个字符，两段各取12个字符重新拼接
    4. 如果不超过25个字符，末尾补'.'至25个字符

    Args:
        function_name: 原始函数名

    Returns:
        str: 格式化后的函数名（固定25个字符）
    """
    # 按.分割，取最后两段
    parts = function_name.split(".")
    if len(parts) >= 2:
        last_two = ".".join(parts[-2:])
    else:
        last_two = function_name

    # 如果长度超过25个字符，两段各取12个字符重新拼接
    if len(last_two) > 25:
        if len(parts) >= 2:
            first_part = parts[-2][:12]
            second_part = parts[-1][:12]
            formatted = f"{first_part}.{second_part}"
        else:
            # 只有一段的情况，直接截取25个字符
            formatted = last_two[:25]
    else:
        formatted = last_two

    # 如果不足25个字符，末尾补'.'
    return formatted.ljust(25, ".")


def _format_multiline_message(msg: str, current_time: str, function_name: str, level: str, indent: str) -> str:
    """
    格式化多行消息，确保每行都有正确的时间戳、function名和缩进

    Args:
        msg: 原始消息（可能包含换行符）
        current_time: 当前时间字符串
        function_name: 格式化后的函数名
        level: 日志级别
        indent: 缩进字符串

    Returns:
        str: 格式化后的完整消息
    """
    lines = msg.split("\n")
    if len(lines) <= 1:
        return f"[{current_time}][{function_name}][{level}]:{indent}{msg}"

    formatted_lines = []
    # 第一行正常格式
    formatted_lines.append(f"[{current_time}][{function_name}][{level}]:{indent}{lines[0]}")

    # 后续行需要对齐
    prefix_length = len(f"[{current_time}][{function_name}][{level}]:")
    padding = " " * prefix_length

    for line in lines[1:]:
        formatted_lines.append(f"{padding}{indent}{line}")

    return "\n".join(formatted_lines)


def _format_multiline_message_with_trace_id(msg: str, current_time: str, function_name: str, level: str, indent: str, trace_id: str) -> str:
    """
    格式化多行消息，包含trace-id，确保每行都有正确的时间戳、function名和缩进

    Args:
        msg: 原始消息（可能包含换行符）
        current_time: 当前时间字符串
        function_name: 格式化后的函数名
        level: 日志级别
        indent: 缩进字符串
        trace_id: 追踪ID

    Returns:
        str: 格式化后的完整消息
    """
    lines = msg.split("\n")
    trace_id_prefix = f"[{trace_id}] " if trace_id else ""
    
    if len(lines) <= 1:
        return f"{trace_id_prefix}[{current_time}][{function_name}][{level}]:{indent}{msg}"

    formatted_lines = []
    # 第一行正常格式
    formatted_lines.append(f"{trace_id_prefix}[{current_time}][{function_name}][{level}]:{indent}{lines[0]}")

    # 后续行需要对齐
    prefix_length = len(f"[{current_time}][{function_name}][{level}]:")
    padding = " " * prefix_length

    for line in lines[1:]:
        formatted_lines.append(f"{trace_id_prefix}{padding}{indent}{line}")

    return "\n".join(formatted_lines)


def log_setter_dev(
    _input: str = "",
    level: str = "info",
    function: str = "",
    **kwargs,  # 兼容其他参数
) -> None:
    """
    开发模式专用的log_setter实现

    Args:
        _input: 日志消息
        level: 日志级别
        function: 函数名
        **kwargs: 其他参数（为了兼容性）
    """
    current_time = datetime.now().strftime("%H:%M:%S")
    formatted_function = _format_function_name(function or "unknown")
    indent = _get_current_indent()

    # 获取trace-id
    try:
        from utils.req_ctx import get_req_ctx
        trace_id = get_req_ctx("trace_id", "")
    except ImportError:
        trace_id = ""

    # 格式化多行消息
    formatted_msg = _format_multiline_message_with_trace_id(_input, current_time, formatted_function, level, indent, trace_id)
    print(formatted_msg)


def log_decorator(log_start: bool = True, log_end: bool = True, log_input: bool = False, log_output: bool = False):
    """
    通用开发模式日志装饰器

    Args:
        log_start: 是否记录函数开始日志
        log_end: 是否记录函数结束日志
        log_input: 是否记录输入参数
        log_output: 是否记录输出结果
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            function_name = f"{func.__module__}.{func.__qualname__}"

            # 记录开始日志并增加深度
            if log_start:
                start_msg = f"[Starting] {func.__name__}"
                if log_input and (args or kwargs):
                    start_msg += f" with args={args}, kwargs={kwargs}"

                # 直接调用原来的log_setter，让它决定是否使用dev模式
                from utils.logger import log_setter

                log_setter(
                    level="info",
                    _input=start_msg,
                    function=function_name,
                )
                _increment_depth()

            try:
                # 执行函数
                result = await func(*args, **kwargs)

                # 减少深度并记录结束日志
                if log_end:
                    _decrement_depth()
                    end_msg = f"[Completed] {func.__name__}"
                    if log_output:
                        end_msg += f" with result={result}"

                    from utils.logger import log_setter

                    log_setter(
                        level="info",
                        _input=end_msg,
                        function=function_name,
                    )

                return result

            except Exception as e:
                # 出错时也要减少深度
                if log_start:
                    _decrement_depth()

                # 记录异常日志
                error_msg = f"[Error] {func.__name__}: {str(e)}"
                from utils.logger import log_setter

                log_setter(
                    level="error",
                    _input=error_msg,
                    function=function_name,
                    error=traceback.format_exc(),
                )
                # 重新抛出异常
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            function_name = f"{func.__module__}.{func.__qualname__}"

            # 记录开始日志并增加深度
            if log_start:
                start_msg = f"[Starting] {func.__name__}"
                if log_input and (args or kwargs):
                    start_msg += f" with args={args}, kwargs={kwargs}"

                from utils.logger import log_setter

                log_setter(
                    level="info",
                    _input=start_msg,
                    function=function_name,
                )
                _increment_depth()

            try:
                # 执行函数
                result = func(*args, **kwargs)

                # 减少深度并记录结束日志
                if log_end:
                    _decrement_depth()
                    end_msg = f"[Completed] {func.__name__}"
                    if log_output:
                        end_msg += f" with result={result}"

                    from utils.logger import log_setter

                    log_setter(
                        level="info",
                        _input=end_msg,
                        function=function_name,
                    )

                return result

            except Exception as e:
                # 出错时也要减少深度
                if log_start:
                    _decrement_depth()

                # 记录异常日志
                error_msg = f"[Error] {func.__name__}: {str(e)}"
                from utils.logger import log_setter

                log_setter(
                    level="error",
                    _input=error_msg,
                    function=function_name,
                    error=traceback.format_exc(),
                )
                # 重新抛出异常
                raise

        # 根据函数类型返回对应的包装器
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def _get_caller_function() -> str:
    """
    获取调用者的函数名称

    Returns:
        str: 调用者函数的完整名称
    """
    try:
        # 获取调用栈
        frame = inspect.currentframe()
        if frame is None:
            return "unknown_function"
            
        # 跳过当前函数和log_info/log_error函数
        caller_frame = frame.f_back
        if caller_frame is None:
            return "unknown_function"
            
        caller_frame = caller_frame.f_back
        if caller_frame is None:
            return "unknown_function"

        # 获取模块名
        module_name = caller_frame.f_globals.get("__name__", "unknown")
        # 获取函数名或类方法名
        function_name = caller_frame.f_code.co_name

        # 如果在类方法中，尝试获取类名
        if "self" in caller_frame.f_locals:
            class_name = caller_frame.f_locals["self"].__class__.__name__
            return f"{module_name}.{class_name}.{function_name}"
        else:
            return f"{module_name}.{function_name}"
    except Exception:
        # 如果获取失败，返回默认值
        return "unknown_function"
    finally:
        # 清理frame引用，避免内存泄漏
        if 'frame' in locals():
            del frame


def dev_log_info(msg: str, encrypted_info: Optional[Any] = None) -> None:
    """
    记录info级别日志（支持缩进）

    Args:
        msg: 日志消息
        encrypted_info: 需要加密的敏感信息
    """
    function_name = _get_caller_function()

    from utils.logger import log_setter

    log_kwargs = {
        "level": "info",
        "_input": msg,
        "function": function_name,
        "cost_time": 0.0,
        "status": 200,
        "call_depth": 2,
    }

    if encrypted_info is not None:
        log_kwargs["encrypted_info"] = encrypted_info

    log_setter(**log_kwargs)


def dev_log_error(msg: str, error: Optional[str] = None, encrypted_info: Optional[Any] = None) -> None:
    """
    记录error级别日志（支持缩进）

    Args:
        msg: 日志消息
        error: 错误详情（如traceback）
        encrypted_info: 需要加密的敏感信息
    """
    function_name = _get_caller_function()

    from utils.logger import log_setter

    log_kwargs = {
        "level": "error",
        "_input": msg,
        "function": function_name,
        "cost_time": 0.0,
        "status": 200,
        "call_depth": 2,
    }

    if error is not None:
        log_kwargs["error"] = error

    if encrypted_info is not None:
        log_kwargs["encrypted_info"] = encrypted_info

    log_setter(**log_kwargs)


def dev_log_warning(msg: str, encrypted_info: Optional[Any] = None) -> None:
    """
    记录warning级别日志（支持缩进）

    Args:
        msg: 日志消息
        encrypted_info: 需要加密的敏感信息
    """
    function_name = _get_caller_function()

    from utils.logger import log_setter

    log_kwargs = {
        "level": "warning",
        "_input": msg,
        "function": function_name,
        "cost_time": 0.0,
        "status": 200,
        "call_depth": 2,
    }

    if encrypted_info is not None:
        log_kwargs["encrypted_info"] = encrypted_info

    log_setter(**log_kwargs)


def dev_log_debug(msg: str, encrypted_info: Optional[Any] = None) -> None:
    """
    记录debug级别日志（支持缩进）

    Args:
        msg: 日志消息
        encrypted_info: 需要加密的敏感信息
    """
    function_name = _get_caller_function()

    from utils.logger import log_setter

    log_kwargs = {
        "level": "debug",
        "_input": msg,
        "function": function_name,
        "cost_time": 0.0,
        "status": 200,
        "call_depth": 2,
    }

    if encrypted_info is not None:
        log_kwargs["encrypted_info"] = encrypted_info

    log_setter(**log_kwargs)


# 装饰器别名，更简洁的使用方式
dlog = log_decorator()  # 默认配置的装饰器
dlog_full = log_decorator(log_start=True, log_end=True, log_input=True, log_output=True)  # 完整日志装饰器
