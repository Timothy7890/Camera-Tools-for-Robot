# 前后端对接状态

后端已实现于 `backend/`（FastAPI + SQLite），接口与部署说明见 `backend/README.md`。
本文记录各处前端的对接状态与剩余事项。

## 已对接

### 机型下的机器人编号列表

- `frontend/src/api/robots.js` → `fetchRobotUnits(robotId)` 调 `GET /api/robots/{robotId}/units`
- 编号来源：机器人侧推送产物时按 manifest 的 `robot_model` 自动登记，无需手工维护
- 搜索仍在前端本地过滤；超过几百台时可改传 `?q=`（后端已支持）

### 机器人详情页

- `frontend/src/views/RobotDetailView.vue` 进入时 `GET /api/robots/units/{unitCode}/calibrations` 一次拉全量，
  按 `type` 分到三个栏目（`camera-transform` 栏目对应 manifest 的 `camera_transform`）
- 列表组件 `frontend/src/components/CalibrationList.vue`：运行名、相机（`camera_label` 或位置名 + 序列号）、手臂、时间、
  质量摘要（内点数 / 残差 / 分辨率）、状态（生效中 / 已替换 / 草稿）、文件下载链接、manifest 链接
- 开发时 `vite.config.js` 把 `/api` 代理到 `http://127.0.0.1:8080`；生产由后端同源托管，无跨域

## 仍为前端静态

### 厂家 / 机型

- `frontend/src/data/vendors.js` 静态（图片是本地 PNG）。后端也有一份 `backend/calib_cloud/vendors.json`
  供 `GET /api/vendors` 返回并附 `unit_count`，两处需同步维护。新增机型时两边一起加。

### 机器人模型文件（STL / URDF）

- 当前由 `/models` 静态托管；相机卡片使用预生成 WebP，点击后才加载 URDF / STL。
- 待提供 green-nas SSH 后：增加“DDNS 主地址 + 阿里云同源回退地址”，并准备 DDNS Docker / Nginx 配置。

### 尚未开始的页面

- 首页（`HomeView.vue`）三个分类卡片仍为占位；可改为展示 `GET /api/vendors` 的 `unit_count` 汇总
- 使用说明（`GuideView.vue`）空白

## 机器人侧对接（calib_workstation 18005）

云端就绪后，机器人侧需要：

1. 配置云端地址与 `CALIB_API_TOKEN`（运行时在页面填写并持久化，不写进配置文件）
2. 扫描 `<data_root>/<unit_code>/calibrations/**/manifest.json` 中 `cloud.pushed=false` 的项，
   `POST /api/robots/units/{unitCode}/calibrations` 上传 manifest + files
3. 用响应里的 `id` 回写本地 manifest 的 `cloud.pushed / pushed_at / remote_id`
4. 本地切换生效 / 删除时同步调 `PATCH` / `DELETE`
