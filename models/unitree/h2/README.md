# Unitree H2 viewer model

用于云端标定资产页的只读 URDF 可视化模型。

- `urdf/robot.urdf` 与 `meshes/*.stl` 来自同项目工作区 `IK_replay/assets/robots/h2/`。
- 模型单位为米，页面把标定产物中的 `T_cam2base` 挂到 `torso_link`。
- 模型只用于展示，不参与云端 IK、碰撞检测或机器人控制。
