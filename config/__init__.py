import os

PROJECT_DIR = os.getenv("PROJECT_PATH") or os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

LOG_NAMESPACE = "feetfit"

LOG_PATH = os.path.join(PROJECT_DIR, "logs/feetfit")

if os.path.exists(LOG_PATH) is False:
    os.makedirs(LOG_PATH)

__all__ = ["PROJECT_DIR", "LOG_NAMESPACE", "LOG_PATH"]


if __name__ == "__main__":
    print(PROJECT_DIR)
