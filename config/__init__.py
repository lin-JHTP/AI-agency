"""配置包初始化模块。"""

# 暴露 settings 模块，支持 `from config import settings` 用法。
from . import settings

__all__ = ["settings"]
