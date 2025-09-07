import json
import os
import random
import string
import time
from datetime import datetime
from typing import Dict, Union

from loguru import logger

t = time.strftime("%Y-%m-%d")
random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))


def console_filter(record):
    """控制台过滤器，将 encrypted_info 替换为 display_encrypted_info，并格式化显示"""
    try:
        # 解析消息中的 JSON
        message_data = json.loads(record["message"])

        # 如果存在 display_encrypted_info，用它替换 encrypted_info
        if "display_encrypted_info" in message_data:
            message_data["encrypted_info"] = message_data["display_encrypted_info"]
            # 移除临时字段
            del message_data["display_encrypted_info"]

        # 保存原始的 input_params 用于特殊处理
        original_input_params = None
        has_sql = False

        if "input_params" in message_data and message_data["input_params"]:
            input_str = message_data["input_params"]
            # 检查是否是 SQL 语句
            if message_data["function"] == "SQL" or "\n" in input_str:
                has_sql = True
                original_input_params = input_str
                # 临时替换为简短标记
                message_data["input_params"] = "[INFO - see below]"

        # 将主要信息转换为单行 JSON
        main_message = json.dumps(message_data, ensure_ascii=False)

        # 如果有 SQL，将其附加在后面并换行显示
        if has_sql and original_input_params:
            sql_lines = original_input_params.strip().split("\n")
            indented_sql = "\n".join(["" + line for line in sql_lines])
            record["message"] = f"{main_message}:{indented_sql}"
        else:
            record["message"] = main_message

    except Exception:
        pass

    return True


class Logger:
    def __init__(self, project_dir, project_name, log_namespace, log_path):
        self.project_name = project_name
        self.log_namespace = log_namespace
        log_dir = os.path.join(project_dir, log_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # 移除默认的控制台处理器
        logger.remove()

        # 添加文件处理器（使用原始消息格式，包含完整加密信息）
        logger.add(
            f"{log_dir}/{t}_all_{random_suffix}.log",
            level="INFO",
            rotation="00:00",
            retention="90 days",
            format="{message}",
        )

        logger.add(
            f"{log_dir}/{t}_err_{random_suffix}.log",
            level="ERROR",
            filter=lambda x: "ERROR" in str(x["level"]).upper(),
            rotation="00:00",
            retention="90 days",
            format="{message}",
        )

        # 添加控制台处理器（使用过滤器，显示遮蔽信息）
        import sys

        logger.add(
            sys.stderr,
            level="INFO",
            filter=console_filter,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
        )

    def log_setter(
        self,
        data_sensitive_level: str = "public",
        log_sensitive_info: str = "true",
        level: str = "info",
        function: str = "",
        _input: Union[Dict, str] = "",
        author: str = "",
        error: str = "",
        cost_time: float = 0.0,
        trace_id: str = "",
        call_depth: int = 2,  # 新增：调用栈深度参数
        **kwargs,
    ):
        """
        Args:
            data_sensitive_level: str, 'public' or 'private', only 'public' level will be logged.
            log_sensitive_info: str, 'true' or 'false'. 'false' is for staff and prod environment.
            level: str, log level, only 'info', 'error', 'warning', 'debug'
            function: str, function name in log
            _input: str, input if log
            author: str, author of the function
            error: str, error in str format
            cost_time: float, time cost
            trace_id: str, log trace id

        Returns:
            dict, log dict
        """
        assert level in ["info", "error", "warning", "debug"]
        # 使用 opt(depth=call_depth) 来跳过指定层数的调用栈，显示真实的调用位置
        # 默认 depth=2 跳过: 1. unified_logger.log_setter, 2. logger.log_setter
        # 对于SQL可以使用更大的深度来跳过数据库工具函数
        # 添加安全检查，确保调用栈深度足够
        import inspect

        actual_stack_depth = len(inspect.stack())
        safe_depth = min(call_depth, actual_stack_depth - 1)  # 确保不超过实际栈深度

        logger_dict = {
            "info": logger.opt(depth=safe_depth).info,
            "error": logger.opt(depth=safe_depth).error,
            "warning": logger.opt(depth=safe_depth).warning,
            "debug": logger.opt(depth=safe_depth).debug,
        }
        if isinstance(_input, dict):
            _input = json.dumps(_input, ensure_ascii=False, indent=2)
        if log_sensitive_info.lower().strip() == "false" and data_sensitive_level.lower().strip() != "public":
            # log_sensitive_info == "false" is for the staff and prod environment.
            # data_sensitive_level.lower().strip() != "public" is for the un-public session data.
            _input = _input[:5] + "*" * 11 + _input[-5:]
        message = "fail" if level == "error" else "success"

        log_res = {
            "level": level,
            "function": function,
            "input_params": _input,
            "message": message,
            "error": error,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            "timestamp": time.time(),
            "cost_time": cost_time,
            "nlp_name": self.project_name,
            "namespace": self.log_namespace,
            "author": author,
            "trace_id": trace_id,
            **kwargs,
        }
        logger_result = json.dumps(log_res, ensure_ascii=False)
        logger_dict[level](logger_result)

        return logger_result
