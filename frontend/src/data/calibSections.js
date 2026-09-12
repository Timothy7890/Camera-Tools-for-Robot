// 标定文件分类。详情页左侧菜单与首页概览共用。
export const calibSections = [
  {
    id: 'extrinsic',
    name: '外参标定文件',
    desc: '相机相对机器人基座 / 末端的位姿变换',
  },
  {
    id: 'intrinsic',
    name: '内参标定文件',
    desc: '相机焦距、主点、畸变系数等内部参数',
  },
  {
    id: 'camera-transform',
    name: '内部相机转换文件',
    desc: '多相机之间的坐标系转换关系',
  },
  {
    id: 'hand-mount',
    name: '灵巧手安装标定',
    desc: '手腕坐标系到灵巧手模型基座的固定安装变换',
  },
  {
    id: 'tcp-profile',
    name: 'TCP 配置文件',
    desc: '按手型、手势或任务区分的工具中心点与指尖特征点',
  },
]

export const DEFAULT_SECTION_ID = calibSections[0].id

export function findSection(id) {
  return calibSections.find((s) => s.id === id) ?? null
}
