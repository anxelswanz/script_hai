
import os


def get_project_root():
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(current_dir)
    return project_root


def get_abs_path(path: str) -> str:
    root = get_project_root()
    print(root)
    return os.path.join(root, path)

if __name__ == "__main__":
    print(get_abs_path("text/ad"))