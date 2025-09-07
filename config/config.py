# -*- coding: utf-8 -*-

"""
Author: wujunjie@shanda.com
"""

import base64
import os
from pathlib import Path
from typing import Any, Dict

import yaml
from cryptography.fernet import Fernet, InvalidToken
from dotenv import dotenv_values, load_dotenv
from ruamel.yaml import YAML

# 常量定义
CONFIG_KEY_FILE = Path(__file__).parent / "config.key.yaml"
ENV_FILE = Path(__file__).parent.parent / ".env"


class EnvProxy:
    """Environment configuration proxy"""

    def __init__(self, local_config_path: str, name: str, dotenv: str):
        """
        Initialize the environment proxy

        Args:
            local_config_path: Path to the local config file
            name: Name of the configuration
            dotenv: Path to the .env file
        """
        self.local_config_path = local_config_path
        self.name = name
        self.dotenv = dotenv

        # Load environment variables
        load_dotenv(dotenv)

        # Get current environment
        self.env = os.environ.get("ENV", "development")

        # Load configuration
        self.cfg = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        base_config = {}
        env_config = {}

        # Load base config file
        if os.path.exists(self.local_config_path):
            with open(self.local_config_path, "r", encoding="utf-8") as f:
                base_config = yaml.safe_load(f) or {}

        # Load environment-specific config file if it exists
        env_config_path = self.local_config_path.replace(".yaml", f".{self.env}.yaml")
        if os.path.exists(env_config_path):
            with open(env_config_path, "r", encoding="utf-8") as f:
                env_config = yaml.safe_load(f) or {}

        # Merge configs with environment-specific taking precedence
        return merge_dicts(base_config, env_config)


def get_encryption_key():
    """获取加密密钥"""
    env = dotenv_values(str(ENV_FILE))
    key = env.get("CONFIG_ENCRYPTION_KEY")
    if not key:
        raise ValueError("CONFIG_ENCRYPTION_KEY not found in .env")
    # Fernet 要求 32 字节 base64
    if len(key) != 44:
        # 自动填充/转换
        key = base64.urlsafe_b64encode(key.encode().ljust(32, b"0"))
        key = key.decode()
    return key


def is_encrypted(val):
    """检查值是否已加密"""
    # Fernet 加密串以 gAAAA 开头
    return isinstance(val, str) and val.startswith("gAAAA")


def encrypt_value(val, fernet):
    """加密值"""
    if is_encrypted(val):
        return val
    return fernet.encrypt(str(val).encode()).decode()


def decrypt_value(val, fernet):
    """解密值"""
    if not is_encrypted(val):
        return val
    try:
        return fernet.decrypt(val.encode()).decode()
    except InvalidToken:
        return val


def encrypt_config_file():
    """加密配置文件"""
    yaml = YAML()
    yaml.preserve_quotes = True

    # Get current environment
    env = os.environ.get("ENV", "development")

    # Encrypt base config file
    encrypt_specific_config_file(CONFIG_KEY_FILE)

    # Encrypt environment-specific config file if it exists
    env_config_key_file = Path(__file__).parent / f"config.{env}.key.yaml"
    if env_config_key_file.exists():
        encrypt_specific_config_file(env_config_key_file)


def encrypt_specific_config_file(config_file_path):
    """加密特定的配置文件"""
    yaml = YAML()
    yaml.preserve_quotes = True

    if not os.path.exists(config_file_path):
        return

    with open(config_file_path, "r", encoding="utf-8") as f:
        data = yaml.load(f)

    if not data:
        return

    key = get_encryption_key()
    fernet = Fernet(key)
    changed = False

    for k, v in data.items():
        if not is_encrypted(v):
            data[k] = encrypt_value(v, fernet)
            changed = True

    if changed:
        with open(config_file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f)


def get_decrypted_config():
    """获取解密后的配置"""
    # Get current environment
    env = os.environ.get("ENV", "development")

    # Load base encrypted config
    base_encrypted = load_encrypted_config(CONFIG_KEY_FILE)

    # Load environment-specific encrypted config
    env_config_key_file = Path(__file__).parent / f"config.{env}.key.yaml"
    env_encrypted = load_encrypted_config(env_config_key_file)

    # Merge with environment-specific taking precedence
    return merge_dicts(base_encrypted, env_encrypted)


def load_encrypted_config(config_file_path):
    """加载并解密特定的配置文件"""
    if not os.path.exists(config_file_path):
        return {}

    yaml = YAML()
    yaml.preserve_quotes = True

    with open(config_file_path, "r", encoding="utf-8") as f:
        data = yaml.load(f)

    if not data:
        return {}

    key = get_encryption_key()
    fernet = Fernet(key)
    result = {}

    for k, v in data.items():
        result[k] = decrypt_value(v, fernet)

    return result


def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并两个字典

    Args:
        a: 第一个字典
        b: 第二个字典

    Returns:
        合并后的新字典
    """
    result = a.copy()
    result.update(b)
    return result


def safe_read_cfg(key: str, default: Any = None) -> Any:
    """
    安全读取配置值

    Args:
        key: 要读取的配置键
        default: 默认值，如果配置不存在则返回此值

    Returns:
        配置值或默认值
    """
    # 始终先检查环境变量
    value = os.environ.get(key)
    if value is not None:
        return value
    return cfg.get(key, default)


# 启动时自动加密配置文件
encrypt_config_file()

# 新的配置合并逻辑，按优先级从低到高合并
# 1. 基础配置 (config.yaml)
base_cfg = {}
config_yaml_path = str(Path(__file__).parent.joinpath("config.yaml"))
if os.path.exists(config_yaml_path):
    with open(config_yaml_path, "r", encoding="utf-8") as f:
        base_cfg = yaml.safe_load(f) or {}

# 2. 基础加密配置 (config.key.yaml)
base_encrypted = load_encrypted_config(CONFIG_KEY_FILE)
cfg_step1 = merge_dicts(base_cfg, base_encrypted)

# 3. 环境特定普通配置 (config.localdb.yaml)
env = os.environ.get("ENV", "localdb")
env_config_path = str(Path(__file__).parent.joinpath(f"config.{env}.yaml"))
env_cfg = {}
if os.path.exists(env_config_path):
    with open(env_config_path, "r", encoding="utf-8") as f:
        env_cfg = yaml.safe_load(f) or {}
cfg_step2 = merge_dicts(cfg_step1, env_cfg)

# 4. 环境特定加密配置 (config.key.localdb.yaml)
env_config_key_file = Path(__file__).parent / f"config.{env}.key.yaml"
env_encrypted = load_encrypted_config(env_config_key_file)
cfg_step3 = merge_dicts(cfg_step2, env_encrypted)

# 5. 环境变量 (最高优先级)
env_config = {}
# 从所有配置文件中提取键，检查是否有对应的环境变量
all_keys = set()
all_keys.update(base_cfg.keys())
all_keys.update(base_encrypted.keys())
all_keys.update(env_cfg.keys())
all_keys.update(env_encrypted.keys())

for key in all_keys:
    if key in os.environ:
        env_config[key] = os.environ[key]
# 强制读取env里的CLUSTER
if "CLUSTER" in os.environ:
    env_config["CLUSTER"] = os.environ["CLUSTER"]

# 最终配置：优先顺序: 环境变量 > config.key.localdb.yaml > config.localdb.yaml > config.key.yaml > config.yaml
cfg = merge_dicts(cfg_step3, env_config)


class Secret:
    """this prevents leakage from accident logging"""

    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

    def _is_sensitive(self) -> bool:
        return any(
            [
                k in self.key.lower()
                for k in ["password", "secret", "key", "token", "access", "credential"]
            ]
        )

    def __str__(self):
        return "**CENSORED**" if self._is_sensitive() else str(self.value)

    def __repr__(self):
        return "**CENSORED**" if self._is_sensitive() else str(self.value)

    def __format__(self, __format_spec: str) -> str:
        return "**CENSORED**" if self._is_sensitive() else str(self.value)

    def unwrap(self):
        return self.value


def dpf_print_value(config: dict, level=0):
    for k, v in config.items():
        if isinstance(v, dict):
            # print("    " * level, f"{k}:")
            key = "    " * level + k + ":"
            source = ""
            print(f"{source}{key:<50}")
            dpf_print_value(v, level + 1)
        else:
            # print("    " * level, f"（{config_source[k]}）{k}: {v}")
            key = "    " * level + k + ":"
            print(f"{key:<50}{Secret(key, v):<30}")
    return config


dpf_print_value(cfg)


__all__ = ["cfg", "safe_read_cfg"]

if __name__ == "__main__":
    key = safe_read_cfg("pg_password")
    print("passwd:", key)
