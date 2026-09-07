# 机器人模型文件（STL / URDF 等）

存放各机器人型号的三维模型与描述文件，供标定工具、可视化及后端使用。

## 目录约定

```
models/
└── <厂家 id>/              # 与 frontend/src/data/vendors.js 中的 vendor.id 一致
    └── <机型 id>/          # 与 robot.id 一致（小写）
        ├── meshes/         # STL / OBJ / DAE 等网格文件
        ├── urdf/           # URDF / xacro 机器人描述文件（可选）
        └── README.md       # 该机型模型的来源、版本、坐标系说明（可选）
```

当前已建目录：

| 厂家 | 机型 | 路径 |
|---|---|---|
| 宇树科技 `unitree` | H2 | `models/unitree/h2/` |
| 宇树科技 `unitree` | G1 | `models/unitree/g1/` |
| 宇树科技 `unitree` | G1D | `models/unitree/g1d/` |
| 众擎机器人 `engineai` | 待补充 | `models/engineai/` |

## 文件命名

- 全小写、下划线分隔，含部件名与版本：`g1_torso_v1.stl`、`g1d_gripper_left.stl`
- 同一部件多版本并存时以 `_v2`、`_v3` 递增，不要覆盖旧文件
- 单位统一为 **米**，坐标系与 URDF 保持一致；如有不同请在该机型的 README 中注明

## 大文件管理（重要）

STL / OBJ 等二进制文件通常在几 MB 到几百 MB，直接提交会让仓库迅速膨胀。建议在放入第一个模型文件之前先启用 **Git LFS**：

```bash
brew install git-lfs          # macOS
git lfs install
git lfs track "models/**/*.stl" "models/**/*.STL" "models/**/*.obj" "models/**/*.dae" "models/**/*.glb" "models/**/*.step" "models/**/*.stp"
git add .gitattributes
```

之后正常 `git add` / `git commit` 即可，LFS 会自动接管这些文件。

如果模型文件由外部系统（PLM / 网盘 / 对象存储）统一管理，也可以只在此目录保留 README 与下载脚本，不入库实体文件。

## 与前端 / 后端的关系

- 前端目前**不直接读取**此目录（网页展示用的是 `frontend/src/assets/robots/` 下的透明底图片）
- 后续若需要在网页中预览 3D 模型或提供下载，由后端提供静态文件服务或对象存储地址，见 `docs/BACKEND_TODO.md`
