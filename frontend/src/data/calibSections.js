// 标定文件分类。详情页左侧菜单与首页概览共用。
export const calibSections = [
  {
    id: 'camera',
    name: '相机标定',
    desc: '以机器人三维模型查看相机位置、朝向与标定结果',
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
  const normalized = id === 'extrinsic' || id === 'intrinsic' ? 'camera' : id
  return calibSections.find((s) => s.id === normalized) ?? null
}
