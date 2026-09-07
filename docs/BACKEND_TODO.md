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
- **使用方**：`frontend/src/components/RobotUnitPicker.vue`（点击机型卡片弹出的编号选择框）

## 3. 选中机器人编号后的动作

- **前端位置**：`frontend/src/views/CameraCalibView.vue` → `onUnitSelected(unit)`
- **现状**：仅 `console.log` 并关闭弹窗
- **待对接**：加载并展示该机器人编号对应的相机标定文件列表（字段待定：文件名、标定时间、下载地址等）
- **建议接口**：`GET /api/robots/units/{unitCode}/camera-calibrations`

## 4. 尚未开始的页面

- **使用说明**（`frontend/src/views/GuideView.vue`）：空白
- **工具标定文件**（`frontend/src/views/ToolCalibView.vue`）：空白，结构预计与相机标定文件一致
