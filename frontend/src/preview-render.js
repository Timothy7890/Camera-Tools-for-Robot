import * as THREE from 'three'
import { attachCameraFrame, cloneUrdfModel } from './lib/urdfScene'

const WIDTH = 1200
const HEIGHT = 800
const host = document.querySelector('#preview')

Object.assign(document.documentElement.style, { width: '100%', height: '100%', margin: '0' })
Object.assign(document.body.style, { width: '100%', height: '100%', margin: '0', overflow: 'hidden' })
Object.assign(host.style, { width: `${WIDTH}px`, height: `${HEIGHT}px`, background: '#f3f4f1' })

window.__PREVIEW_READY__ = false
window.__PREVIEW_ERROR__ = ''

renderPreview().catch((error) => {
  window.__PREVIEW_ERROR__ = error?.message || String(error)
  console.error(error)
})

async function renderPreview() {
  const encoded = window.location.hash.slice(1)
  if (!encoded) throw new Error('缺少预览参数')
  const base64 = encoded.replace(/-/g, '+').replace(/_/g, '/')
  const decoded = Uint8Array.from(atob(base64), (character) => character.charCodeAt(0))
  const payload = JSON.parse(new TextDecoder().decode(decoded))

  const scene = new THREE.Scene()
  scene.background = new THREE.Color(0xf3f4f1)
  scene.add(new THREE.HemisphereLight(0xffffff, 0x777b73, 2.5))
  const key = new THREE.DirectionalLight(0xffffff, 3.2)
  key.position.set(2.5, -3.5, 4.5)
  scene.add(key)
  const fill = new THREE.DirectionalLight(0xbfc8ff, 1.2)
  fill.position.set(-3, 2, 2)
  scene.add(fill)

  const grid = new THREE.GridHelper(3.2, 20, 0xc9ccc6, 0xdfe1dc)
  grid.rotation.x = Math.PI / 2
  grid.position.z = -0.002
  scene.add(grid)

  const robot = await cloneUrdfModel(payload.model)
  attachCameraFrame(
    robot,
    payload.model.anchorLink || 'torso_link',
    payload.transform,
    payload.intrinsics || {},
    payload.cameraRole === 'waist' ? 0x1f9c89 : 0x7657d6,
  )
  scene.add(robot)
  placeOnGround(robot)

  const camera = new THREE.PerspectiveCamera(32, WIDTH / HEIGHT, 0.01, 100)
  camera.up.set(0, 0, 1)
  fitView(robot, camera, payload.cameraRole)

  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' })
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.setPixelRatio(1)
  renderer.setSize(WIDTH, HEIGHT, false)
  renderer.domElement.id = 'preview-canvas'
  host.appendChild(renderer.domElement)
  renderer.render(scene, camera)
  await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))
  renderer.render(scene, camera)
  window.__PREVIEW_READY__ = true
}

function placeOnGround(object) {
  object.position.set(0, 0, 0)
  object.updateMatrixWorld(true)
  const box = new THREE.Box3().setFromObject(object)
  if (!box.isEmpty()) object.position.z = -box.min.z
  object.updateMatrixWorld(true)
}

function fitView(robot, camera, cameraRole) {
  const box = new THREE.Box3().setFromObject(robot)
  if (box.isEmpty()) throw new Error('模型没有可显示内容')
  const size = box.getSize(new THREE.Vector3())
  const center = box.getCenter(new THREE.Vector3())
  const maxDim = Math.max(size.x, size.y, size.z)
  const fitHeight = maxDim / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)))
  const direction = cameraRole === 'waist'
    ? new THREE.Vector3(1.15, -1.8, 0.78)
    : new THREE.Vector3(1.35, -1.75, 0.9)
  direction.normalize()
  camera.position.copy(center).addScaledVector(direction, fitHeight * 1.02)
  camera.near = Math.max(maxDim / 100, 0.005)
  camera.far = maxDim * 30
  camera.lookAt(center)
  camera.updateProjectionMatrix()
}
