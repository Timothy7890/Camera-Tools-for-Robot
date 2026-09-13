"""全部通过环境变量配置。见仓库根目录 .env.example（systemd 通过 EnvironmentFile 读取）。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[1]


def _split(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass
class Settings:
    # 数据目录：SQLite 库 + 产物文件都放这里
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("CALIB_DATA_DIR", str(_REPO / "data"))))
    # 写接口（上传 / 改状态 / 删除）的 Bearer token。为空时拒绝所有写操作。
    api_token: str = field(default_factory=lambda: os.environ.get("CALIB_API_TOKEN", "").strip())
    # 读接口是否也要 token（默认公开只读；公网部署建议打开）
    read_requires_token: bool = field(
        default_factory=lambda: os.environ.get("CALIB_READ_REQUIRES_TOKEN", "0").strip() in ("1", "true", "yes"))
    # 前端构建产物目录；存在时由后端同源托管
    frontend_dist: Path = field(
        default_factory=lambda: Path(os.environ.get("CALIB_FRONTEND_DIST", str(_REPO / "frontend" / "dist"))))
    # URDF / STL 模型目录；通过 /models 只读提供给网页三维查看器
    models_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("CALIB_MODELS_DIR", str(_REPO / "models"))))
    # 允许跨域的来源（前端单独部署时用），逗号分隔；"*" 表示全部
    cors_origins: list[str] = field(default_factory=lambda: _split(os.environ.get("CALIB_CORS_ORIGINS", "*")))
    # 单个上传文件上限（MB）
    max_file_mb: int = field(default_factory=lambda: int(os.environ.get("CALIB_MAX_FILE_MB", "64")))
    # 上传相机标定后，使用无头浏览器异步生成与交互视图一致的 WebP 预览图
    preview_enabled: bool = field(
        default_factory=lambda: os.environ.get("CALIB_PREVIEW_ENABLED", "1").strip() in ("1", "true", "yes"))
    preview_renderer_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("CALIB_PREVIEW_RENDERER_DIR", str(_REPO / "renderer"))))

    @property
    def db_path(self) -> Path:
        return self.data_dir / "calib_cloud.sqlite3"

    @property
    def files_dir(self) -> Path:
        return self.data_dir / "files"


def load_settings() -> Settings:
    return Settings()
