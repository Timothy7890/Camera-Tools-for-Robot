# 云端后端（calib_cloud）

接收机器人侧标定工作站推送的标定产物（`manifest.json` + 结果文件），按
`机器人编号 / 类型 / 相机位置 / 运行` 归档，供网页查看与下载。FastAPI + SQLite，无外部依赖。

- 数据全部在一个目录（默认 `CALIB_DATA_DIR`）：`calib_cloud.sqlite3` + `files/<unit>/<type>/<role>/<run_id>/…`，备份即拷目录。
- 同 `(unit_code, type, camera_role, run_id)` 重复上传 = 覆盖，幂等，机器人侧可放心重试。
- "生效中"以机器人侧为准：推送 `status=active` 的产物时，云端自动把同位置其他 active 改为 `superseded`。

## 部署（systemd）

```bash
git clone <本仓库> /opt/calib-cloud && cd /opt/calib-cloud
sudo bash deploy/install.sh
# 脚本会：生成 .env（随机 token，打印出来请保存）→ npm 构建前端 → 创建 backend/.venv 并装依赖
# → 安装并启动 /etc/systemd/system/calib-cloud.service
curl http://127.0.0.1:8080/api/health     # {"ok":true,...,"write_enabled":true}
```

- 单元模板 `deploy/calib-cloud.service`，占位符 `__APP_DIR__` / `__USER__` 由脚本替换；手工装就自己 sed。
- 配置全部在 `.env`（`EnvironmentFile`），改完 `sudo systemctl restart calib-cloud`。
- 日志 `journalctl -u calib-cloud -f`；更新 `git pull && (cd frontend && npm run build) && sudo systemctl restart calib-cloud`。
- 后端同源托管 `frontend/dist`，网页和 `/api` 同一个端口。
- 服务器上没 npm 时，在别处 `npm run build` 后把 `frontend/dist` 拷到服务器同路径。

## 域名 + HTTPS（Nginx）

`.env` 默认 `CALIB_HOST=127.0.0.1`，对外由 Nginx 反代，与 netbridge 一样走 Let's Encrypt：

```bash
apt install nginx certbot
sudo bash deploy/nginx/setup.sh                      # 默认域名 bwt.xingxingdiandian.xyz
sudo DOMAIN=other.example.com EMAIL=me@x.com bash deploy/nginx/setup.sh
curl https://bwt.xingxingdiandian.xyz/api/health
```

脚本会：无证书时先装临时 80 端口站点 → `certbot certonly --webroot` 签发 → 安装
[`deploy/nginx/calib-cloud.conf`](../deploy/nginx/calib-cloud.conf)（80→443 跳转、全部反代到 127.0.0.1:8080、
`client_max_body_size 256m`）→ 装续期 hook 自动 reload。

```text
/            Vue SPA（后端回 index.html）
/assets/     前端静态资源，长缓存
/api/        接口，关了 proxy_request_buffering 方便大文件上传
```

公网只开 `80/tcp`、`443/tcp`；`8080` 不要对外。机器人侧推送地址填 `https://bwt.xingxingdiandian.xyz`。

## 手动运行（不装服务）

```bash
cd frontend && npm ci && npm run build && cd ..
cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
export CALIB_API_TOKEN=... CALIB_DATA_DIR=/srv/calib-cloud/data
uvicorn calib_cloud.main:app --host 0.0.0.0 --port 8080
```

## 环境变量

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `CALIB_API_TOKEN` | 空 | 写接口 Bearer token。空 = 拒绝所有上传（503） |
| `CALIB_READ_REQUIRES_TOKEN` | `0` | `1` 时读接口也要 token |
| `CALIB_HOST` / `CALIB_PORT` | `0.0.0.0` / `8080` | 监听地址与端口（仅 systemd 单元使用） |
| `CALIB_DATA_DIR` | `<repo>/data` | 数据目录 |
| `CALIB_FRONTEND_DIST` | `<repo>/frontend/dist` | 前端构建目录，存在则托管 |
| `CALIB_CORS_ORIGINS` | `*` | 前后端分开部署时填前端域名 |
| `CALIB_MAX_FILE_MB` | `64` | 单文件上传上限 |

## 接口

读（`CALIB_READ_REQUIRES_TOKEN=1` 时需 `Authorization: Bearer <token>`）：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 |
| GET | `/api/vendors` | 厂家 / 机型，附 `unit_count` |
| GET | `/api/robots/{robotId}/units?q=` | 机型下机器人编号（升序） |
| GET | `/api/robots/units/{unitCode}` | 详情：`counts{type}`、`active{type}{camera_role}` |
| GET | `/api/robots/units/{unitCode}/calibrations?type=&camera_role=&status=` | 产物列表（`type` 接受 `camera-transform` 或 `camera_transform`） |
| GET | `/api/robots/units/{unitCode}/calibrations/{id}` | 完整 manifest |
| GET | `/api/robots/units/{unitCode}/calibrations/{id}/files/{name}` | 下载文件 |

写（必须 `Authorization: Bearer <CALIB_API_TOKEN>`）：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/robots/units/{unitCode}/calibrations` | multipart：`manifest`=JSON 字符串，`files`=多个文件。校验 `manifest.files[].sha256`；返回 `{ok, created, id, item}`，`201` 新建 / `200` 覆盖 |
| PATCH | `/api/robots/units/{unitCode}/calibrations/{id}` | `{"status": "active"|"draft"|"superseded"}` |
| DELETE | `/api/robots/units/{unitCode}/calibrations/{id}` | 删记录 + 文件 |

manifest 格式即机器人侧 `calib_workstation` 的 `calib-manifest/1`（`unit_code`、`vendor`、`robot_model`、
`type`、`camera_role`、`camera_label`、`camera_serial`、`arm`、`run_id`、`tool`、`tool_version`、`created_at`、
`quality`、`files[{name,bytes,sha256}]`、`status`）。上传成功后云端在落盘 manifest 的 `cloud` 里写
`pushed=true / pushed_at / remote_id`，响应里的 `id` 即 `remote_id`，机器人侧回写到本地 manifest。

手动推送示例：

```bash
curl -X POST http://<服务器>:8080/api/robots/units/H2-1336/calibrations \
  -H "Authorization: Bearer $CALIB_API_TOKEN" \
  -F "manifest=<manifest.json" \
  -F "files=@handeye_result_left.json" -F "files=@run.json" -F "files=@session_meta.json"
```

## 开发 / 测试

```bash
cd backend && pip install -r requirements-dev.txt && pytest
CALIB_API_TOKEN=dev uvicorn calib_cloud.main:app --port 8080 --reload
cd ../frontend && npm run dev        # vite 把 /api 代理到 8080
```
