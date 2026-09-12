import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from calib_cloud.app import create_app
from calib_cloud.config import Settings
from calib_cloud.store import Store

TOKEN = "test-token"


def make_client(tmp_path: Path, **overrides) -> TestClient:
    kwargs = dict(
        data_dir=tmp_path / "data",
        api_token=TOKEN,
        frontend_dist=tmp_path / "nodist",
        models_dir=tmp_path / "nomodels",
    )
    kwargs.update(overrides)
    settings = Settings(**kwargs)
    return TestClient(create_app(settings))


def manifest(run_id="run-1", status="draft", artifact_type="extrinsic", files=None, unit="H2-1336"):
    files = files or {"handeye_result_left.json": b'{"T_cam2base": []}'}
    return {
        "schema": "calib-manifest/1",
        "unit_code": unit,
        "vendor": "unitree",
        "robot_model": "h2",
        "type": artifact_type,
        "camera_role": "head",
        "camera_label": "头部相机",
        "camera_serial": "CP0X663000B7",
        "arm": "right",
        "run_id": run_id,
        "tool": "hand_eye_2D",
        "tool_version": "abc123",
        "created_at": "2026-09-10T07:13:10+00:00",
        "quality": {"num_samples": 31, "num_inliers": 11},
        "files": [{"name": n, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in files.items()],
        "status": status,
        "cloud": {"pushed": False, "pushed_at": None, "remote_id": None},
    }, files


def upload(client, m, files, token=TOKEN):
    return client.post(
        f"/api/robots/units/{m['unit_code']}/calibrations",
        data={"manifest": json.dumps(m)},
        files=[("files", (name, body, "application/json")) for name, body in files.items()],
        headers={"Authorization": f"Bearer {token}"} if token else {},
    )


def test_upload_list_download_and_active_semantics(tmp_path):
    c = make_client(tmp_path)
    m1, f1 = manifest("run-1", status="active")
    r = upload(c, m1, f1)
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    # 编号自动登记，机型列表可见
    assert c.get("/api/robots/h2/units").json() == ["H2-1336"]
    assert c.get("/api/vendors").json()[0]["robots"][0]["unit_count"] == 1

    detail = c.get("/api/robots/units/H2-1336").json()
    assert detail["counts"]["extrinsic"] == 1
    assert detail["active"]["extrinsic"]["head"]["run_id"] == "run-1"

    items = c.get("/api/robots/units/H2-1336/calibrations?type=extrinsic").json()["items"]
    assert [i["run_id"] for i in items] == ["run-1"]
    assert c.get("/api/robots/units/H2-1336/calibrations?type=camera-transform").json()["items"] == []

    body = c.get(f"/api/robots/units/H2-1336/calibrations/{cid}/files/handeye_result_left.json").content
    assert body == f1["handeye_result_left.json"]
    full = c.get(f"/api/robots/units/H2-1336/calibrations/{cid}").json()
    assert full["cloud"]["pushed"] is True and full["cloud"]["remote_id"] == cid

    # 第二次生效项把第一次挤成 superseded
    m2, f2 = manifest("run-2", status="active")
    assert upload(c, m2, f2).status_code == 201
    statuses = {i["run_id"]: i["status"] for i in c.get("/api/robots/units/H2-1336/calibrations").json()["items"]}
    assert statuses == {"run-1": "superseded", "run-2": "active"}

    # 重复上传同一 run = 覆盖，不新增
    r = upload(c, m2, f2)
    assert r.status_code == 200 and r.json()["created"] is False
    assert len(c.get("/api/robots/units/H2-1336/calibrations").json()["items"]) == 2

    # PATCH 状态回切
    r = c.patch(f"/api/robots/units/H2-1336/calibrations/{cid}", json={"status": "active"},
                headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    statuses = {i["run_id"]: i["status"] for i in c.get("/api/robots/units/H2-1336/calibrations").json()["items"]}
    assert statuses == {"run-1": "active", "run-2": "superseded"}

    # 删除
    r = c.delete(f"/api/robots/units/H2-1336/calibrations/{cid}", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    assert c.get(f"/api/robots/units/H2-1336/calibrations/{cid}").status_code == 404


def test_hand_artifacts_use_subject_key_and_independent_activation(tmp_path):
    c = make_client(tmp_path)
    payload = b'{"T_wrist2hand":[]}'
    m, files = manifest(
        "mount-1", status="active", artifact_type="hand_mount",
        files={"mount_result.json": payload},
    )
    m.update({
        "schema": "calib-manifest/2",
        "artifact_id": "mount-artifact-1",
        "subject": {
            "kind": "hand",
            "unit_code": "H2-1336",
            "arm": "right_arm",
            "hand_id": "qiangnao-1-right",
            "hand_serial": None,
        },
        "subject_key": "right_arm__qiangnao-1-right",
    })
    m.pop("camera_role")

    response = upload(c, m, files)

    assert response.status_code == 201, response.text
    item = response.json()["item"]
    assert item["subject_key"] == "right_arm__qiangnao-1-right"
    assert item["camera_role"] is None
    detail = c.get("/api/robots/units/H2-1336").json()
    assert detail["active"]["hand_mount"]["right_arm__qiangnao-1-right"]["run_id"] == "mount-1"
    downloaded = c.get(
        f"/api/robots/units/H2-1336/calibrations/{item['id']}/files/mount_result.json"
    )
    assert downloaded.content == payload

    mismatched = dict(m)
    mismatched["run_id"] = "mount-bad"
    mismatched["subject_key"] = "left_arm__wrong-hand"
    response = upload(c, mismatched, files)
    assert response.status_code == 422
    assert "不一致" in response.text


def test_auth_and_validation(tmp_path):
    c = make_client(tmp_path)
    m, f = manifest()
    assert upload(c, m, f, token=None).status_code == 401
    assert upload(c, m, f, token="wrong").status_code == 401

    # sha256 不一致
    bad = {"handeye_result_left.json": b"tampered"}
    assert upload(c, m, bad).status_code == 422

    # 声明了却没传
    assert upload(c, m, {}).status_code == 422

    # unit_code 与路径不一致
    r = c.post("/api/robots/units/H2-9999/calibrations", data={"manifest": json.dumps(m)},
               files=[("files", (n, b)) for n, b in f.items()], headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 422

    # 未知编号
    assert c.get("/api/robots/units/H2-0000").status_code == 404


def test_write_disabled_without_token_config(tmp_path):
    c = make_client(tmp_path, api_token="")
    m, f = manifest()
    assert upload(c, m, f, token="anything").status_code == 503
    assert c.get("/api/health").json()["write_enabled"] is False


def test_read_can_require_token(tmp_path):
    c = make_client(tmp_path, read_requires_token=True)
    assert c.get("/api/vendors").status_code == 401
    assert c.get("/api/vendors", headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 200


def test_models_are_served_when_configured(tmp_path):
    models = tmp_path / "models"
    urdf = models / "unitree" / "h2" / "urdf" / "robot.urdf"
    urdf.parent.mkdir(parents=True)
    urdf.write_text('<robot name="H2"/>', encoding="utf-8")
    c = make_client(tmp_path, models_dir=models)

    response = c.get("/models/unitree/h2/urdf/robot.urdf")

    assert response.status_code == 200
    assert response.text == '<robot name="H2"/>'


def test_existing_v1_database_is_migrated_in_place(tmp_path):
    db_path = tmp_path / "legacy.sqlite3"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE calibrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_code TEXT NOT NULL, vendor TEXT, robot_model TEXT, type TEXT NOT NULL,
            camera_role TEXT NOT NULL, camera_label TEXT, camera_serial TEXT, arm TEXT,
            run_id TEXT NOT NULL, tool TEXT, tool_version TEXT, created_at TEXT,
            status TEXT NOT NULL DEFAULT 'draft', activated_at TEXT, quality TEXT,
            files TEXT, manifest TEXT NOT NULL, uploaded_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            UNIQUE (unit_code, type, camera_role, run_id)
        );
        CREATE TABLE units (
            unit_code TEXT PRIMARY KEY, vendor TEXT, robot_model TEXT,
            first_seen TEXT NOT NULL, last_seen TEXT NOT NULL
        );
    """)
    conn.execute(
        "INSERT INTO calibrations "
        "(unit_code,type,camera_role,run_id,status,manifest,uploaded_at,updated_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        ("H2-1336", "extrinsic", "head", "old-run", "active", "{}", "t", "t"),
    )
    conn.commit()
    conn.close()

    store = Store(db_path, tmp_path / "files")

    row = store.list("H2-1336")[0]
    assert row["subject_key"] == "head"
    assert {"artifact_id", "subject_key", "subject"}.issubset(
        {r["name"] for r in store._conn.execute("PRAGMA table_info(calibrations)")}
    )
