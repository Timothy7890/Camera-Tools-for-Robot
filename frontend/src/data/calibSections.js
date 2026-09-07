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
]

export const DEFAULT_SECTION_ID = calibSections[0].id

export function findSection(id) {
  return calibSections.find((s) => s.id === id) ?? null
}
