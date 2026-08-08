"""环境探测——处理 Windows/Linux 差异。"""
import platform
import tempfile


class Environment:
    @staticmethod
    def is_windows() -> bool:
        return platform.system() == "Windows"

    @staticmethod
    def is_linux() -> bool:
        return platform.system() == "Linux"

    @staticmethod
    def get_temp_dir() -> str:
        return tempfile.gettempdir()
