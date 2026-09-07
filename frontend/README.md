# Camera Tools for Robot — 前端

机器人相机标定 / 工具标定文件管理平台的前端，基于 Vue 3 + Vite + Vue Router。

## 开发

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # 产物输出到 dist/
```

## 目录

- `src/views/` 页面：首页、使用说明、机器人详情（`/robots/:unitCode`）
- `src/components/CalibMenuPanel.vue` 顶部导航「相机与工具标定文件」悬停展开的面板（厂家 / 机型 / 编号选择）
- `src/data/vendors.js` 机器人厂家与机型配置（后续替换为后端接口）
- `src/api/` 接口层（当前为模拟数据，对接清单见 `../docs/BACKEND_TODO.md`）
- `src/assets/robots/` 机型透明底图片
