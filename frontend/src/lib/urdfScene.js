import * as THREE from 'three'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'

// 同一机型的 URDF 与 STL 在整个页面生命周期只加载一次。弹窗 clone 场景树，
// 但共享 geometry / material，避免每颗相机重复下载和解析完整模型。
const templateCache = new Map()

export async function cloneUrdfModel(model, onProgress) {
  const key = `${model.urdfUrl}|${model.meshBaseUrl}`
  if (!templateCache.has(key)) {
    const entry = { progress: 0, listeners: new Set(), promise: null }
    const report = (value) => {
      entry.progress = Math.max(entry.progress, Math.min(100, Math.round(value)))
      for (const listener of entry.listeners) listener(entry.progress)
    }
    entry.promise = loadUrdfTemplate(model, report)
      .then((template) => {
        report(100)
        return template
      })
      .catch((error) => {
        templateCache.delete(key)
        throw error
      })
    templateCache.set(key, entry)
  }
  const entry = templateCache.get(key)
  if (onProgress) {
    entry.listeners.add(onProgress)
    onProgress(entry.progress)
  }
  try {
    const template = await entry.promise
    return template.clone(true)
  } finally {
    if (onProgress) entry.listeners.delete(onProgress)
  }
}

async function loadUrdfTemplate(model, report) {
  report(2)
  const response = await fetch(model.urdfUrl)
  if (!response.ok) throw new Error(`URDF 加载失败（HTTP ${response.status}）`)
  const xml = new DOMParser().parseFromString(await response.text(), 'application/xml')
  if (xml.querySelector('parsererror')) throw new Error('URDF 解析失败')
  report(7)

  const linkGroups = new Map()
  const jointsByParent = new Map()
  const childLinks = new Set()
  const meshTasks = []
  const loader = new STLLoader()
  let loadedMeshes = 0

  for (const linkEl of xml.querySelectorAll('link')) {
    const linkName = linkEl.getAttribute('name')
    const group = new THREE.Group()
    group.name = linkName
    linkGroups.set(linkName, group)

    for (const visualEl of linkEl.querySelectorAll('visual')) {
      const meshEl = visualEl.querySelector('geometry > mesh')
      if (!meshEl) continue
      const visualGroup = new THREE.Group()
      applyOrigin(visualGroup, parseOrigin(visualEl.querySelector('origin')))
      const scale = parseVector(meshEl.getAttribute('scale'), [1, 1, 1])
      const filename = meshEl.getAttribute('filename') || ''
      const material = materialFromVisual(visualEl)
      const meshUrl = resolveMeshUrl(model.meshBaseUrl, filename)
      meshTasks.push(async () => {
        try {
          const geometry = await loader.loadAsync(meshUrl)
          geometry.computeVertexNormals()
          const mesh = new THREE.Mesh(geometry, material)
          mesh.scale.set(...scale)
          mesh.castShadow = true
          mesh.receiveShadow = true
          visualGroup.add(mesh)
        } catch (error) {
          console.warn(`模型网格加载失败：${filename}`, error)
        } finally {
          loadedMeshes += 1
          report(7 + (loadedMeshes / meshTasks.length) * 91)
        }
      })
      group.add(visualGroup)
    }
  }

  for (const jointEl of xml.querySelectorAll('joint')) {
    const parent = jointEl.querySelector('parent')?.getAttribute('link')
    const child = jointEl.querySelector('child')?.getAttribute('link')
    if (!parent || !child) continue
    childLinks.add(child)
    const joint = {
      name: jointEl.getAttribute('name') || '',
      parent,
      child,
      origin: parseOrigin(jointEl.querySelector('origin')),
    }
    if (!jointsByParent.has(parent)) jointsByParent.set(parent, [])
    jointsByParent.get(parent).push(joint)
  }

  const rootLink = [...linkGroups.keys()].find((name) => !childLinks.has(name))
  if (!rootLink) throw new Error('URDF 没有根节点')
  const root = new THREE.Group()
  root.name = 'urdf-root'
  root.add(linkGroups.get(rootLink))
  attachChildren(rootLink)
  if (!meshTasks.length) report(98)
  await runLimited(meshTasks, 5)
  root.updateMatrixWorld(true)
  return root

  function attachChildren(parentName) {
    const parentGroup = linkGroups.get(parentName)
    for (const joint of jointsByParent.get(parentName) || []) {
      const originGroup = new THREE.Group()
      originGroup.name = `${joint.name}_origin`
      applyOrigin(originGroup, joint.origin)
      const childGroup = linkGroups.get(joint.child)
      if (!childGroup) continue
      originGroup.add(childGroup)
      parentGroup.add(originGroup)
      attachChildren(joint.child)
    }
  }
}

export function attachCameraFrame(robot, anchorLink, transform, intrinsics, color = 0x7657d6) {
  const anchor = robot.getObjectByName(anchorLink)
  if (!anchor) throw new Error(`URDF 中找不到相机父节点 ${anchorLink}`)
  const frame = new THREE.Group()
  frame.name = 'calibrated-camera-frame'
  frame.matrixAutoUpdate = false
  frame.matrix.copy(matrixFromRows(transform))

  const bodyMaterial = new THREE.MeshStandardMaterial({ color, roughness: 0.42, metalness: 0.12 })
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.055, 0.024, 0.03), bodyMaterial)
  body.position.z = -0.018
  frame.add(body)
  frame.add(new THREE.AxesHelper(0.12))
  frame.add(buildFrustum(intrinsics, color))
  anchor.add(frame)
  robot.updateMatrixWorld(true)
  return frame
}

function buildFrustum(intrinsics = {}, color) {
  const width = Number(intrinsics.width || 1920)
  const height = Number(intrinsics.height || 1080)
  const matrix = intrinsics.camera_matrix || []
  const fx = Number(matrix[0]?.[0] || width * 0.8)
  const fy = Number(matrix[1]?.[1] || height * 1.4)
  const cx = Number(matrix[0]?.[2] || width / 2)
  const cy = Number(matrix[1]?.[2] || height / 2)
  const depth = 0.42
  const corners = [[0, 0], [width, 0], [width, height], [0, height]].map(
    ([u, v]) => new THREE.Vector3(((u - cx) / fx) * depth, ((v - cy) / fy) * depth, depth),
  )
  const points = []
  const origin = new THREE.Vector3()
  for (const corner of corners) points.push(origin, corner)
  for (let i = 0; i < 4; i += 1) points.push(corners[i], corners[(i + 1) % 4])
  const geometry = new THREE.BufferGeometry().setFromPoints(points)
  const material = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.88 })
  return new THREE.LineSegments(geometry, material)
}

function matrixFromRows(rows) {
  if (!Array.isArray(rows) || rows.length !== 4 || rows.some((row) => !Array.isArray(row) || row.length !== 4)) {
    throw new Error('外参缺少有效的 4×4 T_cam2base')
  }
  return new THREE.Matrix4().set(...rows.flat().map(Number))
}

function parseOrigin(originEl) {
  return {
    xyz: parseVector(originEl?.getAttribute('xyz'), [0, 0, 0]),
    rpy: parseVector(originEl?.getAttribute('rpy'), [0, 0, 0]),
  }
}

function parseVector(value, fallback) {
  if (!value) return fallback
  const values = value.trim().split(/\s+/).map(Number)
  return values.length === 3 && values.every(Number.isFinite) ? values : fallback
}

function applyOrigin(object, origin) {
  const [roll, pitch, yaw] = origin.rpy
  const cr = Math.cos(roll); const sr = Math.sin(roll)
  const cp = Math.cos(pitch); const sp = Math.sin(pitch)
  const cy = Math.cos(yaw); const sy = Math.sin(yaw)
  const matrix = new THREE.Matrix4().set(
    cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr, origin.xyz[0],
    sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr, origin.xyz[1],
    -sp, cp * sr, cp * cr, origin.xyz[2],
    0, 0, 0, 1,
  )
  matrix.decompose(object.position, object.quaternion, object.scale)
}

function materialFromVisual(visualEl) {
  const rgba = parseRgba(visualEl.querySelector('material > color')?.getAttribute('rgba'))
  return new THREE.MeshStandardMaterial({
    color: new THREE.Color(rgba[0], rgba[1], rgba[2]),
    transparent: rgba[3] < 1,
    opacity: rgba[3],
    roughness: 0.64,
    metalness: 0.06,
  })
}

function parseRgba(value) {
  const parts = value?.trim().split(/\s+/).map(Number)
  return parts?.length === 4 && parts.every(Number.isFinite) ? parts : [0.68, 0.72, 0.76, 1]
}

function resolveMeshUrl(base, filename) {
  const clean = filename.replace(/^package:\/\/[^/]+\//, '').replace(/^file:\/\//, '')
  const name = clean.split('/').pop()
  return `${base}${encodeURIComponent(name)}`
}

async function runLimited(tasks, limit) {
  const workers = Array.from({ length: Math.min(limit, tasks.length) }, async (_, workerIndex) => {
    for (let index = workerIndex; index < tasks.length; index += limit) await tasks[index]()
  })
  await Promise.all(workers)
}
