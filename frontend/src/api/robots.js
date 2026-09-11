// 机器人 / 标定产物接口。后端见 backend/calib_cloud/app.py。
// 开发时由 vite 代理 /api → 后端（vite.config.js）；生产由后端同源托管。

const BASE = import.meta.env.VITE_API_BASE || ''

async function request(path, options = {}) {
  const res = await fetch(BASE + path, { headers: { Accept: 'application/json' }, ...options })
  let body = null
  try {
    body = await res.json()
  } catch {
    body = null
  }
  if (!res.ok) {
    const msg = body?.detail?.error || body?.detail?.message || body?.error || res.statusText || `HTTP ${res.status}`
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  }
  return body
}

/** 厂家 / 机型（含每个机型已登记的机器人数 unit_count） */
export function fetchVendors() {
  return request('/api/vendors')
}

/**
 * 获取某机型下所有机器人编号（后端已按编号升序）
 * @param {string} robotId 机型 id（如 'h2'）
 * @returns {Promise<string[]>}
 */
export function fetchRobotUnits(robotId) {
  return request(`/api/robots/${encodeURIComponent(robotId)}/units`)
}

/** 机器人详情：{unit_code, vendor, robot_model, counts{type:n}, active{type:{camera_role: item}}} */
export function fetchUnit(unitCode) {
  return request(`/api/robots/units/${encodeURIComponent(unitCode)}`)
}

/**
 * 某机器人的标定产物列表
 * @param {string} unitCode
 * @param {string} [type] extrinsic | intrinsic | camera-transform
 */
export async function fetchCalibrations(unitCode, type) {
  const q = type ? `?type=${encodeURIComponent(type)}` : ''
  const data = await request(`/api/robots/units/${encodeURIComponent(unitCode)}/calibrations${q}`)
  return data.items
}

export function fetchCalibrationManifest(unitCode, id) {
  return request(`/api/robots/units/${encodeURIComponent(unitCode)}/calibrations/${id}`)
}

export function calibrationFileUrl(unitCode, id, name) {
  return `${BASE}/api/robots/units/${encodeURIComponent(unitCode)}/calibrations/${id}/files/${encodeURIComponent(name)}`
}
