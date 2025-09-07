import yaml


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(data, path):
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)


def clean_config(base_path, target_path):
    base = load_yaml(base_path)
    target = load_yaml(target_path)
    keys_to_delete = []
    for k, v in target.items():
        if k in base and base[k] == v:
            keys_to_delete.append(k)
    for k in keys_to_delete:
        del target[k]
    save_yaml(target, target_path)
    print(f"{target_path} 已删除 {len(keys_to_delete)} 个相同项")


if __name__ == "__main__":
    base_path = "config.yaml"
    targets = ["config.prod.yaml", "config.dev.yaml"]
    for target_path in targets:
        clean_config(base_path, target_path)

    base_path = "config.key.yaml"
    targets = ["config.prod.key.yaml", "config.dev.key.yaml"]
    for target_path in targets:
        clean_config(base_path, target_path)
