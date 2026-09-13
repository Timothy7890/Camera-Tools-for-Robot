"""相机标定 WebP 预览图后台生成器。"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import queue
import re
import shutil
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any, Callable

from .config import Settings
from .store import Store

LOGGER = logging.getLogger(__name__)
RENDER_VERSION = "h2-preview-v1"
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")


class PreviewGenerator:
    """单工作线程截图队列；上传不等待渲染完成。"""

    def __init__(self, settings: Settings, store: Store,
                 runner: Callable[[dict[str, Any], Path], None] | None = None) -> None:
        self.settings = settings
        self.store = store
        self.renderer_dir = settings.preview_renderer_dir
        self.render_script = self.renderer_dir / "render-preview.mjs"
        self.node = shutil.which("node")
        self.runner = runner or self._run_renderer
        self._queue: queue.Queue[int | None] = queue.Queue()
        self._queued: set[int] = set()
        self._rerun: set[int] = set()
        self._queue_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._available = False

    def start(self) -> None:
        if not self.settings.preview_enabled or self._thread:
            return
        missing = self._missing_prerequisite()
        if missing:
            LOGGER.warning("自动预览未启动：%s", missing)
            return
        self._available = True
        self._thread = threading.Thread(target=self._work, name="calib-preview", daemon=True)
        self._thread.start()
        # 服务重启后检查旧记录；内容哈希未变化时不会重复渲染。
        for row in self.store.preview_candidates():
            target = self.store.artifact_dir(
                row["unit_code"], row["type"], row["subject_key"], row["run_id"]
            ) / "preview.webp"
            self.enqueue(
                row["id"],
                mark_pending=row.get("preview_status") != "ready" or not target.is_file(),
            )

    def stop(self) -> None:
        if not self._thread:
            return
        self._queue.put(None)
        self._thread.join(timeout=5)
        self._thread = None
        self._available = False

    def enqueue_for_upload(self, row: dict[str, Any]) -> None:
        if row.get("type") == "extrinsic":
            target = row
        elif row.get("type") == "intrinsic":
            target = self.store.preferred_extrinsic(row["unit_code"], row.get("camera_role") or "")
        else:
            return
        if not target:
            return
        if not self._available:
            if self.settings.preview_enabled:
                self.store.set_preview_state(target["id"], "error", error="预览服务不可用")
            return
        self.enqueue(target["id"], mark_pending=True)

    def enqueue(self, row_id: int, *, mark_pending: bool) -> None:
        if mark_pending:
            self.store.set_preview_state(row_id, "pending", error=None)
        with self._queue_lock:
            if row_id in self._queued:
                self._rerun.add(row_id)
                return
            self._queued.add(row_id)
            self._queue.put(row_id)

    def _missing_prerequisite(self) -> str | None:
        if not self.node:
            return "找不到 node"
        if not self.render_script.is_file():
            return f"缺少 {self.render_script}"
        if not (self.renderer_dir / "node_modules" / "@sparticuz" / "chromium").is_dir():
            return "renderer 依赖尚未安装"
        if not (self.settings.frontend_dist / "preview-render.html").is_file():
            return "前端尚未构建 preview-render.html"
        if not self.settings.models_dir.is_dir():
            return "模型目录不存在"
        return None

    def _work(self) -> None:
        while True:
            row_id = self._queue.get()
            if row_id is None:
                self._queue.task_done()
                return
            try:
                self._generate(row_id)
            except Exception as error:  # 后台失败不能影响上传接口
                LOGGER.exception("标定记录 %s 的预览图生成失败", row_id)
                self.store.set_preview_state(row_id, "error", error=str(error)[:500])
            finally:
                with self._queue_lock:
                    if row_id in self._rerun:
                        self._rerun.remove(row_id)
                        self._queue.put(row_id)
                    else:
                        self._queued.discard(row_id)
                self._queue.task_done()

    def _generate(self, row_id: int) -> None:
        row = self.store.get(row_id)
        if not row or row.get("type") != "extrinsic":
            return
        payload, fingerprint = build_preview_payload(self.settings, self.store, row)
        target_dir = self.store.artifact_dir(
            row["unit_code"], row["type"], row["subject_key"], row["run_id"]
        )
        target = target_dir / "preview.webp"
        if row.get("preview_hash") == fingerprint and target.is_file():
            self.store.set_preview_state(row_id, "ready", fingerprint=fingerprint)
            return

        self.store.set_preview_state(row_id, "pending", error=None)
        temporary = target_dir / f".preview-{uuid.uuid4().hex}.webp"
        try:
            self.runner(payload, temporary)
            if not temporary.is_file() or temporary.stat().st_size == 0:
                raise RuntimeError("渲染器没有生成预览图")
            os.replace(temporary, target)
            self.store.set_preview_state(row_id, "ready", fingerprint=fingerprint, error=None)
        finally:
            temporary.unlink(missing_ok=True)

    def _run_renderer(self, payload: dict[str, Any], output: Path) -> None:
        result = subprocess.run(
            [
                self.node or "node",
                str(self.render_script),
                "--dist", str(self.settings.frontend_dist),
                "--models", str(self.settings.models_dir),
                "--output", str(output),
            ],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
        if result.returncode != 0:
            message = (result.stderr or result.stdout or "渲染器执行失败").strip()
            raise RuntimeError(message[-1000:])


def build_preview_payload(settings: Settings, store: Store,
                          row: dict[str, Any]) -> tuple[dict[str, Any], str]:
    manifest = store.get_manifest(row["id"]) or {}
    transform = manifest.get("T_cam2base")
    if not _valid_transform(transform):
        raise ValueError("外参缺少有效的 T_cam2base")

    vendor = str(row.get("vendor") or manifest.get("vendor") or "").lower()
    robot_model = str(row.get("robot_model") or manifest.get("robot_model") or "").lower()
    if not _SAFE_ID.match(vendor) or not _SAFE_ID.match(robot_model):
        raise ValueError("厂家或机型标识非法")
    model_root = settings.models_dir / vendor / robot_model
    urdf = model_root / "urdf" / "robot.urdf"
    meshes = model_root / "meshes"
    if not urdf.is_file() or not meshes.is_dir():
        raise FileNotFoundError(f"机型 {vendor}/{robot_model} 尚未配置模型")

    intrinsics = _load_intrinsics(store, row["unit_code"], row.get("camera_role") or "")
    anchor_link = (manifest.get("frames") or {}).get("parent") or "torso_link"
    payload = {
        "model": {
            "urdfUrl": f"/models/{vendor}/{robot_model}/urdf/robot.urdf",
            "meshBaseUrl": f"/models/{vendor}/{robot_model}/meshes/",
            "anchorLink": anchor_link,
        },
        "transform": transform,
        "intrinsics": intrinsics,
        "cameraRole": row.get("camera_role") or "head",
    }
    fingerprint_input = {
        "renderer": RENDER_VERSION,
        "payload": payload,
        "model": [
            (str(path.relative_to(model_root)), path.stat().st_size, path.stat().st_mtime_ns)
            for path in sorted(model_root.rglob("*")) if path.is_file()
        ],
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_input, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload, fingerprint


def _load_intrinsics(store: Store, unit_code: str, camera_role: str) -> dict[str, Any]:
    rows = store.list(unit_code, "intrinsic", camera_role)
    if not rows:
        return {}
    row = next((item for item in rows if item["status"] == "active"), rows[0])
    manifest = store.get_manifest(row["id"]) or {}
    declared = [entry.get("name") for entry in row.get("files") or [] if isinstance(entry, dict)]
    candidates = [manifest.get("primary_file"), "camera_intrinsics.json", *declared]
    directory = store.artifact_dir(
        row["unit_code"], row["type"], row["subject_key"], row["run_id"]
    )
    for name in candidates:
        if not name or Path(str(name)).name != name or not str(name).endswith(".json"):
            continue
        path = directory / name
        if not path.is_file():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                return value
        except (OSError, ValueError):
            continue
    return {}


def _valid_transform(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 4
        and all(isinstance(row, list) and len(row) == 4 for row in value)
        and all(isinstance(number, (int, float)) for row in value for number in row)
    )
