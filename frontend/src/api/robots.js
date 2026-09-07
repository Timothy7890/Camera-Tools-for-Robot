// 机器人相关接口。
// 当前全部为前端模拟数据，待后端提供接口后替换实现（见 docs/BACKEND_TODO.md）。

/**
 * 生成确定性的模拟编号列表（每次刷新结果一致，便于调试）
 * @param {string} prefix 编号前缀，如 'G1'
 * @param {number} count 数量
 * @param {number} seed 随机种子
 */
function mockUnits(prefix, count, seed) {
  const set = new Set()
  let s = seed
  while (set.size < count) {
    s = (s * 1103515245 + 12345) & 0x7fffffff
    set.add(1000 + (s % 9000))
  }
  return [...set].sort((a, b) => a - b).map((n) => `${prefix}-${n}`)
}

// TODO(backend): 替换为真实接口，如 GET /api/robots/{robotId}/units
const MOCK_ROBOT_UNITS = {
  h2: ['H2-1063', 'H2-1213', 'H2-1336'],
  g1: mockUnits('G1', 20, 7),
  g1d: mockUnits('G1D', 40, 42),
}

const MOCK_DELAY_MS = 300

/**
 * 获取某机型下所有机器人编号
 * @param {string} robotId 机型 id（如 'h2'）
 * @returns {Promise<string[]>} 机器人编号列表（按编号升序）
 */
export function fetchRobotUnits(robotId) {
  return new Promise((resolve) => {
    setTimeout(() => resolve(MOCK_ROBOT_UNITS[robotId] ?? []), MOCK_DELAY_MS)
  })
}
