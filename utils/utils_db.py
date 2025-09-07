# -*- coding: utf-8 -*-
# @Created Time: 2023-10-04
# @Author      : xun.jiang

import inspect
import time
from contextlib import asynccontextmanager
from datetime import datetime

import psycopg2.extras
from psycopg2 import pool
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from tabulate import tabulate

from config.config import safe_read_cfg
from utils.logger import log_setter

DB_CONFIG = {
    "pg_host": safe_read_cfg("pg_host"),
    "pg_port": safe_read_cfg("pg_port"),
    "pg_user": safe_read_cfg("pg_user"),
    "pg_password": safe_read_cfg("pg_password"),
    "pg_dbname": safe_read_cfg("pg_dbname"),
    "encryption_key": safe_read_cfg("pg_encryption_key"),
}

DB_CONFIG_CORE = {
    "pg_host": safe_read_cfg("pg_host_core"),
    "pg_port": safe_read_cfg("pg_port_core"),
    "pg_user": safe_read_cfg("pg_user_core"),
    "pg_password": safe_read_cfg("pg_password_core"),
    "pg_dbname": safe_read_cfg("pg_dbname_core"),
    "encryption_key": safe_read_cfg("pg_encryption_key_core"),
}

DB_CONFIG_READ_CORE = {
    "pg_host": safe_read_cfg("pg_read_host_core"),
    "pg_port": safe_read_cfg("pg_port_core"),
    "pg_user": safe_read_cfg("pg_user_core"),
    "pg_password": safe_read_cfg("pg_password_core"),
    "pg_dbname": safe_read_cfg("pg_dbname_core"),
    "encryption_key": safe_read_cfg("pg_encryption_key_core"),
}

DB_CONFIG_TS = {
    "pg_host": safe_read_cfg("ts_host"),
    "pg_port": safe_read_cfg("ts_port"),
    "pg_user": safe_read_cfg("ts_user"),
    "pg_password": safe_read_cfg("ts_password"),
    "pg_dbname": safe_read_cfg("ts_dbname"),
}

# 一般日志名称
logger_name = "main"


def db_result_2_dict(rows, sqlDesc):
    """Convert database query rows to a dictionary result format.

    Args:
        rows: The query result rows
        sqlDesc: The column names/descriptions

    Returns:
        Dictionary with sqlDesc and sqlDataSet
    """
    # Properly convert rows to dictionaries using column names as keys
    result_data = []
    for row in rows:
        if hasattr(row, "_mapping"):  # SQLAlchemy 1.4+ Row objects
            result_data.append(dict(row._mapping))
        elif hasattr(row, "keys"):  # Row-like objects
            result_data.append({k: row[k] for k in row.keys()})
        else:  # Tuple/list-like results with column position
            row_dict = {}
            for i, col_name in enumerate(sqlDesc):
                if i < len(row):
                    row_dict[col_name] = row[i]
            result_data.append(row_dict)

    return {"sqlDesc": [(k,) for k in sqlDesc], "sqlDataSet": result_data}


def db_result_2_df(return_result):
    import pandas as pd

    return pd.DataFrame(
        return_result["sqlDataSet"],
        columns=[desc[0] for desc in return_result["sqlDesc"]],
    )


def db_result_2_markdown(return_result, tablefmt="pipe"):
    """Convert database query result to markdown table format string using tabulate.

    Args:
        return_result (dict): Database query result containing 'sqlDataSet' and 'sqlDesc'
        tablefmt (str): Table format ('pipe' for markdown, other options: 'grid', 'simple', etc.)

    Returns:
        str: Formatted table string
    """

    headers = [desc[0] for desc in return_result["sqlDesc"]]
    data = return_result["sqlDataSet"]
    return tabulate(data, headers=headers, tablefmt=tablefmt)


def format_params_for_log(params):
    try:
        """格式化参数用于日志显示，更好地处理数组和复杂类型"""
        if params is None:
            return "None"

        if isinstance(params, dict):
            # 处理字典参数
            parts = []
            for k, v in params.items():
                if isinstance(v, str) and len(v) > 100:
                    # 检查是否是embedding vector格式 (PostgreSQL vector format)
                    if v.startswith("[") and v.endswith("]") and "," in v:
                        # 对于embedding vectors，只显示前几个和后几个值
                        vector_parts = v[1:-1].split(",")
                        if len(vector_parts) > 10:
                            truncated = f"[{','.join(vector_parts[:3])},...,{','.join(vector_parts[-3:])}]"
                            parts.append(f"{k}: '{truncated}' (vector dim:{len(vector_parts)})")
                        else:
                            parts.append(f"{k}: '{v[:97]}...'")
                    else:
                        parts.append(f"{k}: '{v[:97]}...'")
                elif v is None:
                    parts.append(f"{k}: NULL")
                else:
                    parts.append(f"{k}: {v}")
            return "{" + ", ".join(parts) + "}"
        elif isinstance(params, (tuple, list)):
            # 处理元组或列表参数
            formatted_params = []
            for param in params:
                if isinstance(param, dict):
                    # 如果是字典，递归处理
                    formatted_params.append(format_params_for_log(param))
                elif isinstance(param, str):
                    # 检查是否是 PostgreSQL 数组格式 (以 { 开头，以 } 结尾)
                    if param.startswith("{") and param.endswith("}"):
                        formatted_params.append(f"Array[{param}]")
                    else:
                        # 截断过长的字符串参数
                        if len(param) > 100:
                            # 检查是否是embedding vector格式
                            if param.startswith("[") and param.endswith("]") and "," in param:
                                vector_parts = param[1:-1].split(",")
                                if len(vector_parts) > 10:
                                    truncated = f"[{','.join(vector_parts[:3])},...,{','.join(vector_parts[-3:])}]"
                                    formatted_params.append(f"'{truncated}' (vector dim:{len(vector_parts)})")
                                else:
                                    formatted_params.append(f"'{param[:97]}...'")
                            else:
                                formatted_params.append(f"'{param[:97]}...'")
                        else:
                            formatted_params.append(f"'{param}'")
                elif param is None:
                    formatted_params.append("NULL")
                elif isinstance(param, (int, float, bool)):
                    formatted_params.append(str(param))
                elif isinstance(param, datetime):
                    formatted_params.append(f"'{param.isoformat()}'")
                else:
                    formatted_params.append(f"{type(param).__name__}({str(param)})")

            # 如果列表太长，也要截断
            if len(formatted_params) > 10:
                return f"[{len(formatted_params)} items: {', '.join(formatted_params[:3])}, ..., {', '.join(formatted_params[-2:])}]"
            else:
                return "(" + ", ".join(formatted_params) + ")"

        # 对于插入多行的情况，只显示行数
        if isinstance(params, str) and params.startswith("[") and " rows]" in params:
            return params

        return str(params)

    except Exception:
        return str(params)


def get_caller_info():
    """获取调用者信息"""
    stack = inspect.stack()
    # 跳过当前函数和 exec_sql
    for frame_info in stack[2:]:
        module = inspect.getmodule(frame_info.frame)
        if module:
            return (module.__name__, frame_info.lineno, frame_info.function)
    return ("unknown", 0, "unknown")


def detect_query_type(query):
    query = query.strip().lower()
    first_word = query.split(" ", 1)[0] if " " in query else query

    if first_word in ("update", "delete", "insert"):
        return "dml"
    elif first_word in ("create", "drop", "alter", "truncate"):
        return "ddl"
    else:
        # 默认为 select，如果无法确定
        return "select"


class UnifiedDBManager(object):
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UnifiedDBManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not UnifiedDBManager._initialized:
            self.db_pools = {}
            self.async_engines = {}
            self.async_sessionmakers = {}
            UnifiedDBManager._initialized = True

    def _get_db_key(self, db_config):
        """根据 db_config 生成唯一 key"""
        if db_config is None:
            db_config = DB_CONFIG
        # 只用关键参数生成 key
        key = f"{db_config['pg_host']}:{db_config['pg_port']}:{db_config['pg_dbname']}:{db_config['pg_user']}"
        return key

    def init_utils_db(self, db_config=None):
        """同步初始化，确保连接池已存在"""
        if db_config is None:
            db_config = DB_CONFIG
        db_key = self._get_db_key(db_config)
        if db_key not in self.db_pools:
            # Sync pool
            try:
                self.db_pools[db_key] = pool.SimpleConnectionPool(
                    1,
                    20,
                    host=db_config["pg_host"],
                    port=db_config["pg_port"],
                    user=db_config["pg_user"],
                    password=db_config["pg_password"],
                    database=db_config["pg_dbname"],
                    connect_timeout=10,  # 添加连接超时，单位：秒
                )
            except Exception as e:
                error_msg = f"无法连接到数据库 {db_config['pg_host']}:{db_config['pg_port']}/{db_config['pg_dbname']}, 错误: {str(e)}"
                log_setter(
                    function="init_utils_db",
                    _input=error_msg,
                    level="error",
                    call_depth=4,
                )
                raise ConnectionError(error_msg) from e

        if db_key not in self.async_engines:
            # Async engine
            try:
                async_url = (
                    f"postgresql+asyncpg://{db_config['pg_user']}:{db_config['pg_password']}@"
                    f"{db_config['pg_host']}:{db_config['pg_port']}/{db_config['pg_dbname']}"
                )
                engine = create_async_engine(
                    async_url,
                    future=True,
                    pool_size=20,
                    max_overflow=10,
                    pool_timeout=30,
                    pool_recycle=3600,
                    pool_pre_ping=True,
                    connect_args={
                        "timeout": 10,  # 连接超时，单位：秒
                        "server_settings": {
                            "application_name": "unified_db_manager",
                            "app.encryption_key": str(
                                db_config.get("encryption_key", "default_key_2024_holywell_secure")
                            ),
                        },
                    },
                )
                self.async_engines[db_key] = engine
                self.async_sessionmakers[db_key] = sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=engine,
                    class_=AsyncSession,
                )
            except Exception as e:
                error_msg = f"无法创建异步数据库引擎 {db_config['pg_host']}:{db_config['pg_port']}/{db_config['pg_dbname']}, 错误: {str(e)}"
                log_setter(
                    function="init_utils_db",
                    _input=error_msg,
                    level="error",
                    call_depth=4,
                )
                raise ConnectionError(error_msg) from e
        return db_key

    def get_sync_pool(self, db_config=None):
        db_key = self._get_db_key(db_config)
        if db_key not in self.db_pools:
            self.init_utils_db(db_config)
        return self.db_pools[db_key]

    def get_async_sessionmaker(self, db_config=None):
        db_key = self._get_db_key(db_config)
        if db_key not in self.async_sessionmakers:
            self.init_utils_db(db_config)
        return self.async_sessionmakers[db_key]

    def _execute_query_sync(
        self,
        query,
        params=None,
        query_type=None,
        db_config=None,
        fieldList=None,
        trace_id="",
    ):
        module_name, line_no, function_name = get_caller_info()
        caller = f"{module_name}.{function_name}:{line_no}"
        conn = None
        cursor = None
        start_time = time.time()
        record_count = 0
        error = None
        try:
            if not query:
                raise ValueError("SQL script cannot be empty")
            if query_type is None:
                query_type = detect_query_type(query)

            pool_ = self.get_sync_pool(db_config)
            conn = pool_.getconn()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            # 设置加密key
            encryption_key = db_config.get("encryption_key", "default_key_2024_holywell_secure")
            cursor.execute(f"SET app.encryption_key = '{encryption_key}'")
            if query_type == "select":
                cursor.execute(query, params)
                result = cursor.fetchall()
                record_count = len(result)
            elif query_type == "insert_many":
                if not fieldList:
                    raise ValueError("fieldList cannot be empty for insert_many operation")
                result = cursor.executemany(query, fieldList)
                record_count = cursor.rowcount
            elif query_type == "insert":
                cursor.execute(query, params)
                result = cursor.fetchone()
                if result is not None:
                    if isinstance(result, dict):
                        row_dict = result
                    elif hasattr(result, "_mapping"):
                        row_dict = dict(result._mapping)
                    elif hasattr(result, "keys"):
                        row_dict = {k: result[k] for k in result.keys()}
                    else:
                        row_dict = {}
                        if cursor.description:
                            for i, col in enumerate(cursor.description):
                                row_dict[col.name] = result[i]
                else:
                    row_dict = {}
                record_count = cursor.rowcount
            else:
                cursor.execute(query, params)
                record_count = cursor.rowcount
                result = record_count
            conn.commit()
            duration_ms = (time.time() - start_time) * 1000
            formatted_params = format_params_for_log(
                params if query_type != "insert_many" else f"[{len(fieldList)} rows]"
            )

            log_setter(
                function="SQL",
                _input="[Records:" + str(record_count) + "]" + query,
                encrypted_info=formatted_params,
                cost_time=duration_ms,
                call_depth=4,
            )

            if query_type == "select":
                sqlDesc = cursor.description
                return {"sqlDesc": sqlDesc, "sqlDataSet": result}
            if query_type == "insert":
                return {
                    "sqlDesc": list(row_dict.keys()),
                    "sqlDataSet": row_dict,
                }
            return {"sqlDesc": "", "sqlDataSet": result}
        except Exception as e:
            if conn:
                conn.rollback()

            # 截断错误信息，避免日志过长
            error_str = str(e)
            if len(error_str) > 500:
                error_str = error_str[:497] + "..."

            # 截断SQL语句，避免日志过长
            query_str = query
            if len(query_str) > 1000:
                query_str = query_str[:997] + "..."

            error_msg = f"SQL执行错误: {error_str}, SQL: {query_str}, 参数: {format_params_for_log(params)}"

            log_setter(
                function="SQL",
                _input=error_msg,
                encrypted_info=error_msg,
                cost_time=round((time.time() - start_time) * 1000, 2),
                call_depth=4,
                level="error",
            )
            raise
        finally:
            if cursor and conn:
                cursor.close()
                pool_.putconn(conn)
            total_duration_ms = round((time.time() - start_time) * 1000, 2)
            if error:
                log_setter(
                    function="SQL",
                    _input=f"SQL查询失败: {query_type}, 耗时: {total_duration_ms:.2f}ms, 错误: {error}",
                    encrypted_info=f"caller={caller}, trace_id={trace_id}",
                    cost_time=total_duration_ms,
                    call_depth=4,
                    level="error",
                )

    async def _execute_query_async(
        self,
        query,
        params=None,
        query_type=None,
        db_config=None,
        fieldList=None,
        trace_id="",
    ):
        module_name, line_no, function_name = get_caller_info()
        caller = f"{module_name}.{function_name}:{line_no}"
        start_time = time.time()
        record_count = 0
        error = None
        sessionmaker_ = self.get_async_sessionmaker(db_config)
        async with sessionmaker_() as session:
            try:
                if not query:
                    raise ValueError("SQL script cannot be empty")

                # 设置加密key
                encryption_key = db_config.get("encryption_key", "default_key_2024_holywell_secure")
                await session.execute(text(f"SET app.encryption_key = '{encryption_key}'"))

                if query_type is None:
                    query_type = detect_query_type(query)

                if query_type == "select":
                    result = await session.execute(text(query), params)
                    rows = result.fetchall()
                    record_count = len(rows)
                    sqlDesc = result.keys()
                    ret = db_result_2_dict(rows, sqlDesc)
                elif query_type == "insert_many":
                    if not fieldList:
                        raise ValueError("fieldList cannot be empty for insert_many operation")
                    await session.execute(text(query), fieldList)
                    record_count = len(fieldList)
                    ret = {
                        "sqlDesc": "record_count",
                        "sqlDataSet": {"record_count": record_count},
                    }
                elif query_type == "insert":
                    result = await session.execute(text(query), params)

                    # 检查SQL语句是否包含RETURNING子句
                    has_returning = "returning" in query.lower()

                    if has_returning:
                        # 如果有RETURNING子句，获取返回的行
                        try:
                            row = result.fetchone()
                            if row is not None:
                                row_dict = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
                            else:
                                row_dict = {}
                            record_count = 1
                            ret = {
                                "sqlDesc": list(row_dict.keys()),
                                "sqlDataSet": row_dict,
                            }
                        except Exception as e:
                            # 如果fetchone()失败，回退到rowcount处理
                            record_count = result.rowcount
                            ret = {
                                "sqlDesc": "record_count",
                                "sqlDataSet": {"record_count": record_count},
                            }
                    else:
                        # 如果没有RETURNING子句，使用rowcount
                        record_count = result.rowcount
                        ret = {
                            "sqlDesc": "record_count",
                            "sqlDataSet": {"record_count": record_count},
                        }
                else:
                    result = await session.execute(text(query), params)
                    record_count = result.rowcount
                    ret = {
                        "sqlDesc": "record_count",
                        "sqlDataSet": {"record_count": result.rowcount},
                    }
                await session.commit()
                duration_ms = round((time.time() - start_time) * 1000, 2)
                formatted_params = format_params_for_log(
                    params if query_type != "insert_many" else f"[{len(fieldList)} rows]"
                )
                log_setter(
                    function="SQL",
                    _input="[Records:" + str(record_count) + "]" + query,
                    encrypted_info=formatted_params,
                    cost_time=duration_ms,
                    call_depth=4,
                )

                return ret
            except Exception as e:
                await session.rollback()

                # 截断错误信息，避免日志过长
                error_str = str(e)
                if len(error_str) > 500:
                    error_str = error_str[:497] + "..."

                # 截断SQL语句，避免日志过长
                query_str = query
                if len(query_str) > 1000:
                    query_str = query_str[:997] + "..."

                error_msg = f"SQL执行错误: {error_str}, SQL: {query_str}, 参数: {format_params_for_log(params)}"
                log_setter(
                    function="async_error",
                    _input=error_msg,
                    encrypted_info=f"caller={caller}, trace_id={trace_id}",
                    cost_time=round((time.time() - start_time) * 1000, 2),
                    call_depth=4,
                    level="error",
                )
                raise
            finally:
                total_duration_ms = round((time.time() - start_time) * 1000, 2)
                if error:
                    log_setter(
                        function="async_error",
                        _input=f"SQL查询失败: {query_type}, 耗时: {total_duration_ms:.2f}ms, 错误: {error}",
                        encrypted_info=f"caller={caller}, trace_id={trace_id}",
                        cost_time=total_duration_ms,
                        call_depth=4,
                        level="error",
                    )

    async def _execute_query_async_with_session(
        self,
        query,
        session,
        params=None,
        query_type=None,
        fieldList=None,
        trace_id="",
    ):
        module_name, line_no, function_name = get_caller_info()
        caller = f"{module_name}.{function_name}:{line_no}"
        start_time = time.time()
        record_count = 0
        error = None
        try:
            if not query:
                raise ValueError("SQL script cannot be empty")

            # 设置加密key（从session中获取db_config）
            encryption_key = "default_key_2024_holywell_secure"
            # 如果能从session中获取配置，则使用配置的key
            try:
                await session.execute(text(f"SET app.encryption_key = '{encryption_key}'"))
            except:
                pass  # 如果设置失败，继续使用默认key

            if query_type is None:
                query_type = detect_query_type(query)

            if query_type == "select":
                result = await session.execute(text(query), params)
                rows = result.fetchall()
                record_count = len(rows)
                sqlDesc = result.keys()
                ret = db_result_2_dict(rows, sqlDesc)
            elif query_type == "insert_many":
                if not fieldList:
                    raise ValueError("fieldList cannot be empty for insert_many operation")
                await session.execute(text(query), fieldList)
                record_count = len(fieldList)
                ret = {
                    "sqlDesc": "record_count",
                    "sqlDataSet": {"record_count": record_count},
                }
            elif query_type == "insert":
                result = await session.execute(text(query), params)

                # 检查SQL语句是否包含RETURNING子句
                has_returning = "returning" in query.lower()

                if has_returning:
                    # 如果有RETURNING子句，获取返回的行
                    try:
                        row = result.fetchone()
                        if row is not None:
                            row_dict = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
                        else:
                            row_dict = {}
                        record_count = 1
                        ret = {
                            "sqlDesc": list(row_dict.keys()),
                            "sqlDataSet": row_dict,
                        }
                    except Exception as e:
                        # 如果fetchone()失败，回退到rowcount处理
                        record_count = result.rowcount
                        ret = {
                            "sqlDesc": "record_count",
                            "sqlDataSet": {"record_count": record_count},
                        }
                else:
                    # 如果没有RETURNING子句，使用rowcount
                    record_count = result.rowcount
                    ret = {
                        "sqlDesc": "record_count",
                        "sqlDataSet": {"record_count": record_count},
                    }
            else:
                result = await session.execute(text(query), params)
                record_count = result.rowcount
                ret = {
                    "sqlDesc": "record_count",
                    "sqlDataSet": {"record_count": result.rowcount},
                }
            duration_ms = round((time.time() - start_time) * 1000, 2)
            formatted_params = format_params_for_log(
                params if query_type != "insert_many" else f"[{len(fieldList)} rows]"
            )
            log_setter(
                function="SQL",
                _input="[Records:" + str(record_count) + "]" + query,
                encrypted_info=formatted_params,
                cost_time=duration_ms,
                call_depth=4,
            )

            return ret
        except Exception as e:
            await session.rollback()

            # 截断错误信息，避免日志过长
            error_str = str(e)
            if len(error_str) > 500:
                error_str = error_str[:497] + "..."

            # 截断SQL语句，避免日志过长
            query_str = query
            if len(query_str) > 1000:
                query_str = query_str[:997] + "..."

            error_msg = f"SQL执行错误: {error_str}, SQL: {query_str}, 参数: {format_params_for_log(params)}"
            log_setter(
                function="async_error",
                _input=error_msg,
                encrypted_info=f"caller={caller}, trace_id={trace_id}",
                cost_time=round((time.time() - start_time) * 1000, 2),
                call_depth=4,
                level="error",
            )
            raise
        finally:
            total_duration_ms = round((time.time() - start_time) * 1000, 2)
            if error:
                log_setter(
                    function="async_error",
                    _input=f"SQL查询失败: {query_type}, 耗时: {total_duration_ms:.2f}ms, 错误: {error}",
                    encrypted_info=f"caller={caller}, trace_id={trace_id}",
                    cost_time=total_duration_ms,
                    call_depth=4,
                    level="error",
                )

    async def execute_query(
        self,
        query,
        params=None,
        query_type=None,
        db_config=DB_CONFIG_CORE,
        mode="async",
        fieldList=None,
        trace_id="",
        session=None,
    ):
        if session is None:
            sql_result = await self._execute_query_async(
                query=query,
                params=params,
                query_type=query_type,
                db_config=db_config,
                fieldList=fieldList,
                trace_id=trace_id,
            )
        else:
            sql_result = await self._execute_query_async_with_session(
                query=query,
                session=session,
                params=params,
                query_type=query_type,
                fieldList=fieldList,
                trace_id=trace_id,
            )
        return sql_result["sqlDataSet"]

    @asynccontextmanager
    async def get_session(self, db_config=None):
        sessionmaker_ = self.get_async_sessionmaker(db_config)
        async with sessionmaker_() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                log_setter(level="error", _input=f"SQL Err: {e}")
                await session.rollback()
            finally:
                await session.close()

    async def health_check(self, db_config=None):
        """检查数据库连接健康状态

        Returns:
            dict: 包含连接状态和错误信息的字典
        """
        if db_config is None:
            db_config = DB_CONFIG

        result = {
            "sync_pool": {"status": "unknown", "error": None},
            "async_engine": {"status": "unknown", "error": None},
            "db_info": f"{db_config['pg_host']}:{db_config['pg_port']}/{db_config['pg_dbname']}",
        }

        # 检查同步连接池
        try:
            pool_ = self.get_sync_pool(db_config)
            conn = pool_.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            pool_.putconn(conn)
            result["sync_pool"]["status"] = "healthy"
        except Exception as e:
            result["sync_pool"]["status"] = "unhealthy"
            result["sync_pool"]["error"] = str(e)

        # 检查异步引擎
        try:
            sessionmaker_ = self.get_async_sessionmaker(db_config)
            async with sessionmaker_() as session:
                await session.execute(text("SELECT 1"))
            result["async_engine"]["status"] = "healthy"
        except Exception as e:
            result["async_engine"]["status"] = "unhealthy"
            result["async_engine"]["error"] = str(e)

        return result


def execute_query_sync(
    query,
    params=None,
    query_type=None,
    db_config=None,
    fieldList=None,
    mode="sync",
    trace_id="",
):
    sql_result = UnifiedDBManager()._execute_query_sync(
        query=query,
        params=params,
        query_type=query_type,
        db_config=db_config,
        fieldList=fieldList,
        trace_id=trace_id,
    )
    return sql_result["sqlDataSet"]


# 单例和快捷方法
utils_db_manager = UnifiedDBManager()
execute_query = utils_db_manager.execute_query
health_check = utils_db_manager.health_check
get_session = utils_db_manager.get_session
