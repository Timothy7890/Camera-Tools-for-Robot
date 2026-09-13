"""SQLite + 本地文件系统的产物存储。

表 calibrations：一行 = 一个产物包（对应机器人侧 calibrations/<type>/<subject_key>/<run_id>/manifest.json）。
唯一键 (unit_code, type, subject_key, run_id)，重复上传视为覆盖（幂等）。
文件放 <data_dir>/files/<unit_code>/<type>/<subject_key>/<run_id>/<name>。

"生效"语义与机器人侧一致：同一 (unit_code, type, camera_role) 下最多一个 active，
其余曾经 active 的变为 superseded。机器人侧是真相源，云端只记录它推送过来的状态。
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

CAMERA_ARTIFACT_TYPES = ("extrinsic", "intrinsic", "camera_transform")
HAND_ARTIFACT_TYPES = ("hand_mount", "tcp_profile")
ARTIFACT_TYPES = (*CAMERA_ARTIFACT_TYPES, *HAND_ARTIFACT_TYPES)
# 前端路由用连字符（camera-transform），manifest 用下划线；两种都接受
TYPE_ALIASES = {"camera-transform": "camera_transform"}
STATUSES = ("draft", "active", "superseded")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS calibrations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_code     TEXT NOT NULL,
    vendor        TEXT,
    robot_model   TEXT,
    type          TEXT NOT NULL,
    artifact_id   TEXT,
    subject_key   TEXT,
    subject       TEXT,
    camera_role   TEXT NOT NULL,
    camera_label  TEXT,
    camera_serial TEXT,
    arm           TEXT,
    run_id        TEXT NOT NULL,
    tool          TEXT,
    tool_version  TEXT,
    created_at    TEXT,
    status        TEXT NOT NULL DEFAULT 'draft',
    activated_at  TEXT,
    quality       TEXT,
    files         TEXT,
    manifest      TEXT NOT NULL,
    preview_status TEXT NOT NULL DEFAULT 'none',
    preview_hash   TEXT,
    preview_error  TEXT,
    preview_updated_at TEXT,
    uploaded_at   TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    UNIQUE (unit_code, type, camera_role, run_id)
);
CREATE INDEX IF NOT EXISTS idx_calib_unit ON calibrations (unit_code, type);
CREATE TABLE IF NOT EXISTS units (
    unit_code   TEXT PRIMARY KEY,
    vendor      TEXT,
    robot_model TEXT,
    first_seen  TEXT NOT NULL,
    last_seen   TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_type(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().lower()
    value = TYPE_ALIASES.get(value, value)
    return value if value in ARTIFACT_TYPES else None


def manifest_subject(manifest: dict[str, Any], artifact_type: str) -> tuple[dict[str, Any], str]:
    """Validate a v1/v2 subject and return (subject, canonical subject_key)."""
    raw = manifest.get("subject")
    subject = dict(raw) if isinstance(raw, dict) else {}
    if artifact_type in CAMERA_ARTIFACT_TYPES:
        camera_role = str(subject.get("camera_role") or manifest.get("camera_role") or "").strip()
        if not camera_role:
            raise ValueError("相机产物 manifest 缺少 subject.camera_role / camera_role")
        subject.setdefault("kind", "camera")
        subject.setdefault("unit_code", manifest.get("unit_code"))
        subject["camera_role"] = camera_role
        subject.setdefault("camera_serial", manifest.get("camera_serial"))
        canonical_key = camera_role
    else:
        arm = str(subject.get("arm") or manifest.get("arm") or "").strip()
        hand_id = str(subject.get("hand_id") or manifest.get("hand_id") or "").strip()
        if not arm or not hand_id:
            raise ValueError("手部产物 manifest 缺少 subject.arm / subject.hand_id")
        subject.setdefault("kind", "hand")
        subject.setdefault("unit_code", manifest.get("unit_code"))
        subject["arm"] = arm
        subject["hand_id"] = hand_id
        subject.setdefault("hand_serial", manifest.get("hand_serial"))
        canonical_key = f"{arm}__{hand_id}"
    supplied_key = str(manifest.get("subject_key") or "").strip()
    if supplied_key and supplied_key != canonical_key:
        raise ValueError(
            f"manifest.subject_key={supplied_key!r} 与 subject 推导值 {canonical_key!r} 不一致")
    return subject, canonical_key


class Store:
    def __init__(self, db_path: Path, files_dir: Path) -> None:
        self.db_path = Path(db_path)
        self.files_dir = Path(files_dir)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._migrate_v2_columns()
        self._conn.commit()

    def _migrate_v2_columns(self) -> None:
        """Add v2 identity columns without rebuilding existing production DBs."""
        columns = {row["name"] for row in self._conn.execute("PRAGMA table_info(calibrations)")}
        additions = {
            "artifact_id": "TEXT",
            "subject_key": "TEXT",
            "subject": "TEXT",
            "preview_status": "TEXT NOT NULL DEFAULT 'none'",
            "preview_hash": "TEXT",
            "preview_error": "TEXT",
            "preview_updated_at": "TEXT",
        }
        for name, sql_type in additions.items():
            if name not in columns:
                self._conn.execute(f"ALTER TABLE calibrations ADD COLUMN {name} {sql_type}")
        self._conn.execute(
            "UPDATE calibrations SET subject_key=camera_role WHERE subject_key IS NULL OR subject_key=''"
        )
        self._conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_calib_subject "
            "ON calibrations (unit_code, type, subject_key, run_id)"
        )
        self._conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_calib_artifact_id "
            "ON calibrations (artifact_id) WHERE artifact_id IS NOT NULL"
        )

    def close(self) -> None:
        self._conn.close()

    # ---------- 路径 ----------

    def artifact_dir(self, unit_code: str, artifact_type: str, subject_key: str, run_id: str) -> Path:
        return self.files_dir / unit_code / artifact_type / subject_key / run_id

    # ---------- 写 ----------

    def upsert(self, manifest: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """写入 / 覆盖一条产物记录，返回 (行, 是否新建)。文件由调用方落盘。"""
        unit_code = str(manifest["unit_code"])
        artifact_type = normalize_type(manifest.get("type"))
        if artifact_type is None:
            raise ValueError(f"未知产物类型 {manifest.get('type')!r}")
        subject, subject_key = manifest_subject(manifest, artifact_type)
        if artifact_type in CAMERA_ARTIFACT_TYPES:
            camera_role = str(subject["camera_role"])
        else:
            camera_role = subject_key  # 兼容旧数据库 NOT NULL/唯一键，API 输出会隐藏
        run_id = str(manifest.get("run_id") or "")
        if not subject_key or not run_id:
            raise ValueError("manifest 缺少 subject_key / run_id")
        status = str(manifest.get("status") or "draft")
        if status not in STATUSES:
            status = "draft"
        ts = now_iso()
        with self._lock:
            existing = self._conn.execute(
                "SELECT id FROM calibrations WHERE unit_code=? AND type=? AND subject_key=? AND run_id=?",
                (unit_code, artifact_type, subject_key, run_id),
            ).fetchone()
            values = dict(
                unit_code=unit_code,
                vendor=manifest.get("vendor"),
                robot_model=manifest.get("robot_model"),
                type=artifact_type,
                artifact_id=manifest.get("artifact_id"),
                subject_key=subject_key,
                subject=json.dumps(subject, ensure_ascii=False),
                camera_role=camera_role,
                camera_label=manifest.get("camera_label"),
                camera_serial=manifest.get("camera_serial"),
                arm=manifest.get("arm"),
                run_id=run_id,
                tool=manifest.get("tool"),
                tool_version=manifest.get("tool_version"),
                created_at=manifest.get("created_at"),
                status=status,
                activated_at=manifest.get("activated_at"),
                quality=json.dumps(manifest.get("quality") or {}, ensure_ascii=False),
                files=json.dumps(manifest.get("files") or [], ensure_ascii=False),
                manifest=json.dumps(manifest, ensure_ascii=False),
                updated_at=ts,
            )
            if existing:
                sets = ", ".join(f"{k}=:{k}" for k in values)
                values["id"] = existing["id"]
                self._conn.execute(f"UPDATE calibrations SET {sets} WHERE id=:id", values)
                row_id = existing["id"]
                created = False
            else:
                values["uploaded_at"] = ts
                cols = ", ".join(values)
                params = ", ".join(f":{k}" for k in values)
                cur = self._conn.execute(f"INSERT INTO calibrations ({cols}) VALUES ({params})", values)
                row_id = cur.lastrowid
                created = True
            if status == "active":
                self._supersede_others(unit_code, artifact_type, subject_key, row_id)
            self._touch_unit(unit_code, manifest.get("vendor"), manifest.get("robot_model"), ts)
            self._conn.commit()
        return self.get(row_id), created

    def set_status(self, row_id: int, status: str) -> dict[str, Any]:
        if status not in STATUSES:
            raise ValueError(f"status 只能是 {STATUSES}")
        with self._lock:
            row = self._conn.execute("SELECT * FROM calibrations WHERE id=?", (row_id,)).fetchone()
            if row is None:
                raise KeyError(row_id)
            ts = now_iso()
            manifest = json.loads(row["manifest"])
            manifest["status"] = status
            if status == "active":
                manifest["activated_at"] = ts
                self._supersede_others(row["unit_code"], row["type"], row["subject_key"], row_id)
            self._conn.execute(
                "UPDATE calibrations SET status=?, activated_at=?, manifest=?, updated_at=? WHERE id=?",
                (status, manifest.get("activated_at") if status == "active" else row["activated_at"],
                 json.dumps(manifest, ensure_ascii=False), ts, row_id),
            )
            self._conn.commit()
        return self.get(row_id)

    def delete(self, row_id: int) -> dict[str, Any]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM calibrations WHERE id=?", (row_id,)).fetchone()
            if row is None:
                raise KeyError(row_id)
            self._conn.execute("DELETE FROM calibrations WHERE id=?", (row_id,))
            self._conn.commit()
        target = self.artifact_dir(row["unit_code"], row["type"], row["subject_key"], row["run_id"])
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        return self._row_to_dict(row)

    def _supersede_others(self, unit_code: str, artifact_type: str, subject_key: str, keep_id: int) -> None:
        ts = now_iso()
        others = self._conn.execute(
            "SELECT id, manifest FROM calibrations WHERE unit_code=? AND type=? AND subject_key=? AND status='active' AND id<>?",
            (unit_code, artifact_type, subject_key, keep_id),
        ).fetchall()
        for other in others:
            manifest = json.loads(other["manifest"])
            manifest["status"] = "superseded"
            self._conn.execute(
                "UPDATE calibrations SET status='superseded', manifest=?, updated_at=? WHERE id=?",
                (json.dumps(manifest, ensure_ascii=False), ts, other["id"]),
            )

    def _touch_unit(self, unit_code: str, vendor: Any, robot_model: Any, ts: str) -> None:
        self._conn.execute(
            """INSERT INTO units (unit_code, vendor, robot_model, first_seen, last_seen)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(unit_code) DO UPDATE SET
                 vendor=COALESCE(excluded.vendor, units.vendor),
                 robot_model=COALESCE(excluded.robot_model, units.robot_model),
                 last_seen=excluded.last_seen""",
            (unit_code, vendor, robot_model, ts, ts),
        )

    # ---------- 读 ----------

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        for key in ("quality", "files", "subject"):
            try:
                d[key] = json.loads(d[key]) if d.get(key) else ({} if key in ("quality", "subject") else [])
            except ValueError:
                d[key] = {} if key in ("quality", "subject") else []
        if d.get("type") in HAND_ARTIFACT_TYPES:
            d["camera_role"] = None
        if d.get("preview_status") == "ready" and d.get("preview_hash"):
            d["preview_url"] = (
                f"/api/robots/units/{d['unit_code']}/calibrations/{d['id']}/preview.webp"
                f"?v={d['preview_hash'][:12]}"
            )
        else:
            d["preview_url"] = None
        d.pop("preview_error", None)
        d.pop("manifest", None)
        return d

    def get(self, row_id: int) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM calibrations WHERE id=?", (row_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def get_manifest(self, row_id: int) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT manifest FROM calibrations WHERE id=?", (row_id,)).fetchone()
        return json.loads(row["manifest"]) if row else None

    def set_preview_state(self, row_id: int, status: str, *, fingerprint: str | None = None,
                          error: str | None = None) -> dict[str, Any] | None:
        if status not in ("none", "pending", "ready", "error"):
            raise ValueError(f"未知预览状态 {status!r}")
        with self._lock:
            current = self._conn.execute(
                "SELECT preview_hash FROM calibrations WHERE id=?", (row_id,)
            ).fetchone()
            if current is None:
                return None
            preview_hash = fingerprint if fingerprint is not None else current["preview_hash"]
            self._conn.execute(
                "UPDATE calibrations SET preview_status=?, preview_hash=?, preview_error=?, "
                "preview_updated_at=? WHERE id=?",
                (status, preview_hash, error, now_iso(), row_id),
            )
            self._conn.commit()
        return self.get(row_id)

    def preview_candidates(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM calibrations WHERE type='extrinsic' "
            "ORDER BY CASE status WHEN 'active' THEN 0 ELSE 1 END, id DESC"
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def preferred_extrinsic(self, unit_code: str, camera_role: str) -> dict[str, Any] | None:
        rows = self.list(unit_code, "extrinsic", camera_role)
        return next((row for row in rows if row["status"] == "active"), rows[0] if rows else None)

    def list(self, unit_code: str, artifact_type: str | None = None, camera_role: str | None = None,
             status: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM calibrations WHERE unit_code=?"
        params: list[Any] = [unit_code]
        if artifact_type:
            sql += " AND type=?"
            params.append(artifact_type)
        if camera_role:
            sql += " AND subject_key=?"
            params.append(camera_role)
        if status:
            sql += " AND status=?"
            params.append(status)
        sql += " ORDER BY COALESCE(created_at, uploaded_at) DESC, id DESC"
        return [self._row_to_dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def active_map(self, unit_code: str) -> dict[str, dict[str, dict[str, Any]]]:
        """{type: {subject_key: row}} 当前生效项。"""
        out: dict[str, dict[str, dict[str, Any]]] = {t: {} for t in ARTIFACT_TYPES}
        for row in self.list(unit_code, status="active"):
            out.setdefault(row["type"], {})[row["subject_key"]] = row
        return out

    def counts(self, unit_code: str) -> dict[str, int]:
        rows = self._conn.execute(
            "SELECT type, COUNT(*) AS n FROM calibrations WHERE unit_code=? GROUP BY type", (unit_code,)
        ).fetchall()
        out = {t: 0 for t in ARTIFACT_TYPES}
        for r in rows:
            out[r["type"]] = r["n"]
        return out

    def unit(self, unit_code: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM units WHERE unit_code=?", (unit_code,)).fetchone()
        return dict(row) if row else None

    def units(self, robot_model: str | None = None) -> list[dict[str, Any]]:
        if robot_model:
            rows = self._conn.execute(
                "SELECT * FROM units WHERE lower(robot_model)=lower(?) ORDER BY unit_code", (robot_model,)
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM units ORDER BY unit_code").fetchall()
        return [dict(r) for r in rows]

    def unit_counts_by_model(self) -> dict[str, int]:
        rows = self._conn.execute(
            "SELECT lower(robot_model) AS m, COUNT(*) AS n FROM units GROUP BY lower(robot_model)"
        ).fetchall()
        return {r["m"]: r["n"] for r in rows if r["m"]}


def iter_manifest_files(manifest: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for entry in manifest.get("files") or []:
        if isinstance(entry, dict) and entry.get("name"):
            yield entry
