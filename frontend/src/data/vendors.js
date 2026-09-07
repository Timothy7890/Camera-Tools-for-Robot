// 机器人厂家与机型配置。后续可改为后端接口返回。
// image 字段留空时前端使用占位图。
import h2Image from '../assets/robots/h2.png'
import g1Image from '../assets/robots/g1.png'
import g1dImage from '../assets/robots/g1d.png'

export const vendors = [
  {
    id: 'unitree',
    name: '宇树科技',
    robots: [
      { id: 'h2', name: 'H2', subtitle: '人形本体', image: h2Image },
      { id: 'g1', name: 'G1', subtitle: '人形本体', image: g1Image },
      { id: 'g1d', name: 'G1D', subtitle: '轮式双臂', image: g1dImage },
    ],
  },
  {
    id: 'engineai',
    name: '众擎机器人',
    robots: [],
  },
]

/**
 * 根据机器人编号（如 'G1D-3001'）反查厂家与机型。
 * 按机型名长度降序匹配前缀，避免 'G1-' 误匹配 'G1D-xxxx'。
 * @returns {{ vendor: object, robot: object } | null}
 */
export function findRobotByUnitCode(unitCode) {
  const candidates = []
  for (const vendor of vendors) {
    for (const robot of vendor.robots) {
      candidates.push({ vendor, robot })
    }
  }
  candidates.sort((a, b) => b.robot.name.length - a.robot.name.length)
  const upper = String(unitCode ?? '').toUpperCase()
  return candidates.find(({ robot }) => upper.startsWith(`${robot.name.toUpperCase()}-`)) ?? null
}
