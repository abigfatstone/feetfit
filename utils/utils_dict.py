MAX_VALUE_LENGTH = 300


class DictPrinter:
    def __init__(self):
        pass

    def _print_complete_summary(self, title: str, summary_dict: dict, indent_level: int = 0):
        """
        动态打印字典的全部信息，只对叶子节点进行截断

        Args:
            title: 打印的标题
            summary_dict: 要打印的字典
            indent_level: 缩进级别
        """

        INDENT = "  " * indent_level

        print(f"{INDENT}【{title}】")

        if not summary_dict:
            print(f"{INDENT}  无数据")
            return

        for key, value in summary_dict.items():
            self._print_value(key, value, indent_level + 1)

        print()  # 添加空行分隔

    def _print_value(self, key: str, value, indent_level: int):
        """
        打印单个值，根据类型决定是否进一步分解

        Args:
            key: 键名
            value: 值
            indent_level: 缩进级别
        """
        INDENT = "  " * indent_level

        if isinstance(value, dict):
            # 如果值是字典，递归打印
            if value:
                print(f"{INDENT}{key}:")
                for sub_key, sub_value in value.items():
                    self._print_value(sub_key, sub_value, indent_level + 1)
            else:
                print(f"{INDENT}{key}: {{}}")

        elif isinstance(value, (list, tuple)):
            # 如果值是列表或元组，需要检查元素类型
            if len(value) == 0:
                print(f"{INDENT}{key}: []")
            else:
                # 检查列表中的元素是否都是简单类型
                if self._is_simple_list(value):
                    # 简单类型的列表，可以直接打印
                    value_str = str(value)
                    if len(value_str) > MAX_VALUE_LENGTH:
                        print(f"{INDENT}{key}: {value_str[:MAX_VALUE_LENGTH]}... (truncated)")
                    else:
                        print(f"{INDENT}{key}: {value_str}")
                else:
                    # 复杂结构的列表，需要逐个处理
                    print(f"{INDENT}{key}: [")
                    for i, item in enumerate(value):
                        self._print_value(f"[{i}]", item, indent_level + 1)
                    print(f"{INDENT}]")
        else:
            # 叶子节点：其他简单类型的值
            value_str = str(value)
            if len(value_str) > MAX_VALUE_LENGTH:
                print(f"{INDENT}{key}: {value_str[:MAX_VALUE_LENGTH]}... (truncated)")
            else:
                print(f"{INDENT}{key}: {value_str}")

    def _is_simple_list(self, lst) -> bool:
        """
        检查列表是否只包含简单类型（非字典、非列表）

        Args:
            lst: 要检查的列表

        Returns:
            bool: 如果列表只包含简单类型返回True，否则返回False
        """
        for item in lst:
            if isinstance(item, (dict, list, tuple)):
                return False
        return True
