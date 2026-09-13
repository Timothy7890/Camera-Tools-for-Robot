"""HTTP 接口。

读（默认公开，可用 CALIB_READ_REQUIRES_TOKEN=1 关闭）：
  GET  /api/health
  GET  /api/vendors                                   厂家 / 机型（附每个机型已登记的机器人数）
  GET  /api/robots/{robotId}/units                    某机型下的机器人编号列表
  GET  /api/robots/units/{unitCode}                   机器人详情：各类型数量 + 当前生效项
  GET  /api/robots/units/{unitCode}/calibrations?type=&camera_role=&status=
  GET  /api/robots/units/{unitCode}/calibrations/{id}             完整 manifest
  GET  /api/robots/units/{unitCode}/calibrations/{id}/files/{name} 下载文件

写（Bearer CALIB_API_TOKEN）：
  POST   /api/robots/units/{unitCode}/calibrations    multipart: manifest=<json 字符串> + files=<多个文件>
  PATCH  /api/robots/units/{unitCode}/calibrations/{id}   {"status": "active|draft|superseded"}
  DELETE /api/robots/units/{unitCode}/calibrations/{id}
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import Settings, load_settings
from .preview import PreviewGenerator
from .store import (
    ARTIFACT_TYPES,
    STATUSES,
    Store,
    iter_manifest_files,
    manifest_subject,
    normalize_type,
)

_UNIT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SAFE_NAME_RE = re.compile(r"^[^/\\\x00]{1,255}$")
_VENDORS = json.loads((Path(__file__).with_name("vendors.json")).read_text(encoding="utf-8"))

# 部分精简 Linux 环境没有预置 WebP MIME，显式注册以便静态预览图正确返回。
mimetypes.add_type("image/webp", ".webp")


def fail(status: int, message: str) -> HTTPException:
    return HTTPException(status, {"ok": False, "error": message})


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    store = Store(settings.db_path, settings.files_dir)
    previews = PreviewGenerator(settings, store)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        previews.start()
        try:
            yield
        finally:
            previews.stop()

    app = FastAPI(title="相机标定管理平台", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings = settings
    app.state.store = store
    app.state.preview_generator = previews

    # ---------- 鉴权 ----------

    def _check_token(authorization: str | None) -> None:
        if not settings.api_token:
            raise fail(503, "服务端未配置 CALIB_API_TOKEN，暂不接受写操作")
        token = ""
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        if token != settings.api_token:
            raise fail(401, "token 无效")

    def require_write(authorization: str | None = Header(default=None)) -> None:
        _check_token(authorization)

    def require_read(authorization: str | None = Header(default=None)) -> None:
        if settings.read_requires_token:
            _check_token(authorization)

    def unit_param(unit_code: str) -> str:
        if not _UNIT_RE.match(unit_code or ""):
            raise fail(422, "非法机器人编号")
        return unit_code

    def row_or_404(unit_code: str, calib_id: int) -> dict[str, Any]:
        row = store.get(calib_id)
        if row is None or row["unit_code"] != unit_code:
            raise fail(404, "记录不存在")
        return row

    # ---------- 读 ----------

    @app.get("/api/health")
    def health():
        return {"ok": True, "version": __version__, "write_enabled": bool(settings.api_token)}

    @app.get("/api/vendors", dependencies=[Depends(require_read)])
    def vendors():
        counts = store.unit_counts_by_model()
        out = []
        for vendor in _VENDORS:
            robots = [{**r, "unit_count": counts.get(r["id"].lower(), 0)} for r in vendor["robots"]]
            out.append({**vendor, "robots": robots})
        return out

    @app.get("/api/robots/{robot_id}/units", dependencies=[Depends(require_read)])
    def robot_units(robot_id: str, q: str | None = None):
        units = [u["unit_code"] for u in store.units(robot_id)]
        if q:
            needle = re.sub(r"[-\s]", "", q).lower()
            units = [u for u in units if needle in re.sub(r"[-\s]", "", u).lower()]
        return units

    @app.get("/api/robots/units/{unit_code}", dependencies=[Depends(require_read)])
    def unit_detail(unit_code: str):
        unit_param(unit_code)
        unit = store.unit(unit_code)
        if unit is None:
            raise fail(404, "机器人编号不存在（还没有任何标定产物上传）")
        return {**unit, "counts": store.counts(unit_code), "active": store.active_map(unit_code)}

    @app.get("/api/robots/units/{unit_code}/calibrations", dependencies=[Depends(require_read)])
    def list_calibrations(unit_code: str, type: str | None = Query(default=None),
                          camera_role: str | None = None, status: str | None = None):
        unit_param(unit_code)
        artifact_type = None
        if type:
            artifact_type = normalize_type(type)
            if artifact_type is None:
                raise fail(422, f"type 只能是 {ARTIFACT_TYPES}（或 camera-transform）")
        if status and status not in STATUSES:
            raise fail(422, f"status 只能是 {STATUSES}")
        return {"items": store.list(unit_code, artifact_type, camera_role, status)}

    @app.get("/api/robots/units/{unit_code}/calibrations/{calib_id}", dependencies=[Depends(require_read)])
    def get_calibration(unit_code: str, calib_id: int):
        row_or_404(unit_code, calib_id)
        return store.get_manifest(calib_id)

    @app.get("/api/robots/units/{unit_code}/calibrations/{calib_id}/preview-status",
             dependencies=[Depends(require_read)])
    def preview_status(unit_code: str, calib_id: int):
        row = row_or_404(unit_code, calib_id)
        return {"status": row.get("preview_status") or "none", "preview_url": row.get("preview_url")}

    @app.get("/api/robots/units/{unit_code}/calibrations/{calib_id}/preview.webp",
             dependencies=[Depends(require_read)])
    def preview_image(unit_code: str, calib_id: int):
        row = row_or_404(unit_code, calib_id)
        path = store.artifact_dir(
            row["unit_code"], row["type"], row["subject_key"], row["run_id"]
        ) / "preview.webp"
        if row.get("preview_status") != "ready" or not path.is_file():
            raise fail(404, "预览图尚未生成")
        return FileResponse(
            path,
            media_type="image/webp",
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )

    @app.get("/api/robots/units/{unit_code}/calibrations/{calib_id}/files/{name}",
             dependencies=[Depends(require_read)])
    def download(unit_code: str, calib_id: int, name: str):
        row = row_or_404(unit_code, calib_id)
        if not _SAFE_NAME_RE.match(name) or name in (".", ".."):
            raise fail(422, "非法文件名")
        path = store.artifact_dir(row["unit_code"], row["type"], row["subject_key"], row["run_id"]) / name
        if not path.is_file():
            raise fail(404, "文件不存在")
        return FileResponse(path, filename=name)

    # ---------- 写 ----------

    @app.post("/api/robots/units/{unit_code}/calibrations", dependencies=[Depends(require_write)])
    async def upload(unit_code: str, manifest: str = Form(...), files: list[UploadFile] = File(default=[])):
        """机器人侧推送一个产物包。manifest 里 files[].sha256 用于校验上传内容；
        同 (unit_code, type, subject_key, run_id) 重复上传 = 覆盖（幂等）。"""
        unit_param(unit_code)
        try:
            data = json.loads(manifest)
        except ValueError as exc:
            raise fail(422, f"manifest 不是合法 JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise fail(422, "manifest 必须是对象")
        if str(data.get("unit_code") or "") != unit_code:
            raise fail(422, f"manifest.unit_code={data.get('unit_code')!r} 与路径 {unit_code!r} 不一致")
        artifact_type = normalize_type(data.get("type"))
        if artifact_type is None:
            raise fail(422, f"manifest.type 只能是 {ARTIFACT_TYPES}")
        data["type"] = artifact_type
        try:
            subject, subject_key = manifest_subject(data, artifact_type)
        except ValueError as exc:
            raise fail(422, str(exc)) from exc
        run_id = str(data.get("run_id") or "")
        if not _SAFE_NAME_RE.match(subject_key) or not _SAFE_NAME_RE.match(run_id) or "/" in subject_key + run_id:
            raise fail(422, "subject_key / run_id 非法")
        if subject_key in (".", "..") or run_id in (".", ".."):
            raise fail(422, "subject_key / run_id 非法")
        data["subject"] = subject
        data["subject_key"] = subject_key

        expected = {e["name"]: e for e in iter_manifest_files(data)}
        uploaded: dict[str, bytes] = {}
        limit = settings.max_file_mb * 1024 * 1024
        for f in files:
            name = Path(f.filename or "").name
            if not name or not _SAFE_NAME_RE.match(name):
                raise fail(422, f"非法文件名 {f.filename!r}")
            body = await f.read()
            if len(body) > limit:
                raise fail(413, f"{name} 超过 {settings.max_file_mb} MB")
            uploaded[name] = body
        missing = sorted(set(expected) - set(uploaded))
        if missing:
            raise fail(422, f"manifest.files 里声明了但没上传: {missing}")
        for name, body in uploaded.items():
            entry = expected.get(name)
            if entry and entry.get("sha256"):
                digest = hashlib.sha256(body).hexdigest()
                if digest != entry["sha256"]:
                    raise fail(422, f"{name} 的 sha256 与 manifest 不一致")
            else:
                # 未在 manifest 声明的文件也收下，补进 files 列表
                data.setdefault("files", []).append(
                    {"name": name, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})

        target = store.artifact_dir(unit_code, artifact_type, subject_key, run_id)
        tmp = target.with_name(target.name + ".uploading")
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True, exist_ok=True)
        try:
            for name, body in uploaded.items():
                (tmp / name).write_bytes(body)
            data.setdefault("cloud", {})
            data["cloud"].update({"pushed": True, "pushed_at": _now(), "remote_id": None})
            (tmp / "manifest.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            if target.exists():
                shutil.rmtree(target)
            tmp.rename(target)
        except Exception:
            shutil.rmtree(tmp, ignore_errors=True)
            raise
        try:
            row, created = store.upsert(data)
        except ValueError as exc:
            raise fail(422, str(exc)) from exc
        # remote_id 回写到落盘与库里的 manifest，方便机器人侧记录
        data["cloud"]["remote_id"] = row["id"]
        (target / "manifest.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        row, _ = store.upsert(data)
        previews.enqueue_for_upload(row)
        row = store.get(row["id"])
        return JSONResponse({"ok": True, "created": created, "id": row["id"], "item": row}, status_code=201 if created else 200)

    @app.patch("/api/robots/units/{unit_code}/calibrations/{calib_id}", dependencies=[Depends(require_write)])
    def patch_status(unit_code: str, calib_id: int, body: dict):
        row_or_404(unit_code, calib_id)
        status = str((body or {}).get("status") or "")
        if status not in STATUSES:
            raise fail(422, f"status 只能是 {STATUSES}")
        return {"ok": True, "item": store.set_status(calib_id, status)}

    @app.delete("/api/robots/units/{unit_code}/calibrations/{calib_id}", dependencies=[Depends(require_write)])
    def delete_calibration(unit_code: str, calib_id: int):
        row_or_404(unit_code, calib_id)
        return {"ok": True, "deleted": store.delete(calib_id)}

    # ---------- 前端静态托管（前后端同源部署） ----------

    # 模型与前端构建产物分开存放，避免 Vite 每次构建复制十几 MB 的 STL。
    # URL 稳定，生产 Nginx 可对 /models/ 使用长期缓存。
    if settings.models_dir.is_dir():
        app.mount("/models", StaticFiles(directory=str(settings.models_dir)), name="models")

    dist = settings.frontend_dist
    if (dist / "index.html").is_file():
        if (dist / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=str(dist / "assets")), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):
            candidate = dist / full_path
            if full_path and candidate.is_file() and dist in candidate.resolve().parents:
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    return app


def _now() -> str:
    from .store import now_iso
    return now_iso()
