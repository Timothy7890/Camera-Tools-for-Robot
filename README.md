# Camera-Tools-for-Robot

机器人相机标定文件管理平台（云端）。展示与管理放云端，标定流程在机器人本地的 `calib_workstation` 完成后推送到这里。

- `frontend/` Vue 3 网页
- `backend/` FastAPI 后端（接口、部署、环境变量见 [backend/README.md](backend/README.md)）
- `docs/BACKEND_TODO.md` 前后端对接状态
- `models/` 机型模型文件目录约定

部署到云服务器（systemd）：

```bash
sudo bash deploy/install.sh          # 生成 .env + 构建前端 + venv + 安装并启动 calib-cloud.service
curl http://127.0.0.1:8080/api/health
sudo bash deploy/nginx/setup.sh      # Nginx 反代 + Let's Encrypt，域名 bwt.xingxingdiandian.xyz
curl https://bwt.xingxingdiandian.xyz/api/health
```

详见 [backend/README.md](backend/README.md)。
