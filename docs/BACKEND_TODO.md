# 前后端对接待办

记录前端目前使用模拟数据（mock）的位置，后端接口就绪后按此清单逐项替换。
代码中对应位置均以 `TODO(backend)` 注释标记，可全局搜索。

## 1. 机器人厂家 / 机型列表

- **前端位置**：`frontend/src/data/vendors.js`
- **现状**：静态写死。厂家：宇树科技（H2 / G1 / G1D）、众擎机器人（暂无机型）
- **待对接**：后端返回厂家及其机型列表；机型图片目前为本地透明底 PNG，可继续由前端维护，也可改为后端返回 URL
- **建议接口**：`GET /api/vendors`

  ```json
  [
    {
      "id": "unitree",
      "name": "宇树科技",
      "robots": [
        { "id": "h2", "name": "H2", "subtitle": "人形本体", "image": "" }
      ]
    }
  ]
  ```

## 2. 机型下的机器人编号列表

- **前端位置**：`frontend/src/api/robots.js` → `fetchRobotUnits(robotId)`
- **现状**：模拟数据 `MOCK_ROBOT_UNITS`，带 300ms 延迟模拟网络
  - H2：3 台（`H2-1063`、`H2-1213`、`H2-1336`）
  - G1：20 台（`mockUnits` 按固定种子生成，形如 `G1-xxxx`）
  - G1D：40 台（同上，形如 `G1D-xxxx`）
- **待对接**：替换函数内部实现为真实请求，保持函数签名与返回 `Promise<string[]>` 不变即可，调用方无需修改
- **注意**：前端期望编号已按升序排好；若后端不保证顺序，在此函数内排序
- **搜索**：目前在前端本地过滤（数量 ≤ 几百台足够）。若单机型编号超过数百台，改为把搜索词传给后端：`GET /api/robots/{robotId}/units?q=1336`
- **建议接口**：`GET /api/robots/{robotId}/units` → `["H2-1336", "H2-1213", ...]`
- **使用方**：`frontend/src/components/RobotUnitPicker.vue`（点击机型卡片弹出的编号选择框，位于顶部导航悬停面板 `CalibMenuPanel.vue` 内）

## 3. 机器人详情页（选中编号后跳转）

- **前端位置**：`frontend/src/views/RobotDetailView.vue`，路由 `/robots/:unitCode/:section?`（如 `/robots/H2-1336/extrinsic`）
- **现状**：
  - 顶部 hero 已完成：机型图片 + 厂家/机型 + 编号大标题。机型信息由 `findRobotByUnitCode()` 按编号前缀在前端本地反查
  - 三个分类（定义在 `frontend/src/data/calibSections.js`）在同一页面内连续排列，左侧菜单随滚动高亮当前栏目，点击菜单平滑滚动到对应位置；路由参数 `section` 仅用于打开链接时初始定位：
    - `extrinsic` 外参标定文件
    - `intrinsic` 内参标定文件
    - `camera-transform` 内部相机转换文件
  - 右侧内容区为占位（"待开发"）
- **待对接**：
  - 直接访问该 URL 时（刷新 / 分享链接）需要校验编号是否存在；目前前缀匹配不到时显示"未知机型"。建议接口：`GET /api/robots/units/{unitCode}` 返回编号、机型、厂家、状态等
  - 内容区按分类加载文件列表。建议接口：`GET /api/robots/units/{unitCode}/calibrations?type=extrinsic|intrinsic|camera-transform`，字段待定（文件名、标定时间、下载地址、是否当前生效等）

## 4. 机器人模型文件（STL / URDF）

- **存放位置**：仓库根目录 `models/<vendorId>/<robotId>/{meshes,urdf}/`，目录约定见 `models/README.md`
- **现状**：仅目录骨架，无实体文件；前端不直接读取
- **待对接**：若需在网页中预览 3D 模型或下载，由后端提供静态文件服务或对象存储地址。建议接口：`GET /api/robots/{robotId}/models` 返回文件列表与下载 URL
- **注意**：放入模型文件前先启用 Git LFS（见 `models/README.md`），否则仓库会迅速膨胀

## 5. 尚未开始的页面

- **首页**（`frontend/src/views/HomeView.vue`）：已有标题与三个分类卡片（外参 / 内参 / 内部相机转换），卡片内容为"待开发"占位
- **使用说明**（`frontend/src/views/GuideView.vue`）：空白
