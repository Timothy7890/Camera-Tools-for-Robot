<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { attachCameraFrame, cloneUrdfModel } from '../lib/urdfScene'

const props = defineProps({
  model: { type: Object, required: true },
  transform: { type: Array, required: true },
  intrinsics: { type: Object, default: () => ({}) },
  interactive: { type: Boolean, default: false },
  cameraRole: { type: String, default: 'head' },
})

const host = ref(null)
const loading = ref(true)
const progress = ref(0)
const error = ref('')
let renderer = null
let scene = null
let viewCamera = null
let controls = null
let resizeObserver = null
let robot = null
let generation = 0

async function build() {
  const current = ++generation
  loading.value = true
  progress.value = 0
  error.value = ''
  await nextTick()
  try {
    if (!renderer) setupRenderer()
    if (robot) scene.remove(robot)
    robot = await cloneUrdfModel(props.model, (value) => {
      if (current === generation) progress.value = value
    })
    if (current !== generation) return
    attachCameraFrame(
      robot,
      props.model.anchorLink || 'torso_link',
      props.transform,
      props.intrinsics,
      props.cameraRole === 'waist' ? 0x1f9c89 : 0x7657d6,
    )
    scene.add(robot)
    placeOnGround(robot)
    fitView()
    loading.value = false
    render()
  } catch (reason) {
    if (current !== generation) return
    error.value = reason?.message || '三维模型加载失败'
    loading.value = false
  }
}

function setupRenderer() {
  scene = new THREE.Scene()
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

  viewCamera = new THREE.PerspectiveCamera(props.interactive ? 38 : 32, 1, 0.01, 100)
  viewCamera.up.set(0, 0, 1)
  renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' })
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, props.interactive ? 2 : 1.5))
  renderer.domElement.setAttribute('aria-label', props.interactive ? '可拖动的机器人相机三维视图' : '机器人相机三维预览')
  host.value.appendChild(renderer.domElement)

  controls = new OrbitControls(viewCamera, renderer.domElement)
  controls.enabled = props.interactive
  controls.enableDamping = props.interactive
  controls.dampingFactor = 0.08
  controls.minDistance = 0.6
  controls.maxDistance = 8
  controls.addEventListener('change', render)
  resizeObserver = new ResizeObserver(resize)
  resizeObserver.observe(host.value)
  resize()
}

function placeOnGround(object) {
  object.position.set(0, 0, 0)
  object.updateMatrixWorld(true)
  const box = new THREE.Box3().setFromObject(object)
  if (!box.isEmpty()) object.position.z = -box.min.z
  object.updateMatrixWorld(true)
}

function fitView() {
  if (!robot || !viewCamera) return
  const box = new THREE.Box3().setFromObject(robot)
  if (box.isEmpty()) return
  const size = box.getSize(new THREE.Vector3())
  const center = box.getCenter(new THREE.Vector3())
  const maxDim = Math.max(size.x, size.y, size.z)
  const fitHeight = maxDim / (2 * Math.tan(THREE.MathUtils.degToRad(viewCamera.fov / 2)))
  const direction = props.cameraRole === 'waist'
    ? new THREE.Vector3(1.15, -1.8, 0.78)
    : new THREE.Vector3(1.35, -1.75, 0.9)
  direction.normalize()
  viewCamera.position.copy(center).addScaledVector(direction, fitHeight * (props.interactive ? 1.08 : 1.02))
  viewCamera.near = Math.max(maxDim / 100, 0.005)
  viewCamera.far = maxDim * 30
  viewCamera.lookAt(center)
  viewCamera.updateProjectionMatrix()
  controls.target.copy(center)
  controls.update()
}

function resize() {
  if (!renderer || !host.value) return
  const width = Math.max(host.value.clientWidth, 1)
  const height = Math.max(host.value.clientHeight, 1)
  renderer.setSize(width, height, false)
  viewCamera.aspect = width / height
  viewCamera.updateProjectionMatrix()
  render()
}

function render() {
  if (renderer && scene && viewCamera) renderer.render(scene, viewCamera)
}

function resetView() {
  fitView()
}

watch(
  () => [props.model, props.transform, props.intrinsics, props.cameraRole],
  build,
  { deep: true },
)

onMounted(build)
onBeforeUnmount(() => {
  generation += 1
  resizeObserver?.disconnect()
  controls?.dispose()
  renderer?.dispose()
  renderer?.domElement.remove()
})

defineExpose({ resetView })
</script>

<template>
  <div ref="host" class="urdf-viewer" :class="{ 'is-interactive': interactive }">
    <div v-if="loading" class="viewer-state">
      <div class="viewer-loading-copy">
        <div class="viewer-loading-line">
          <span>正在加载模型</span>
          <span>{{ progress }}%</span>
        </div>
        <div
          class="viewer-progress"
          role="progressbar"
          aria-label="模型加载进度"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-valuenow="progress"
        >
          <span :style="{ width: `${progress}%` }"></span>
        </div>
        <small>首次加载稍慢</small>
      </div>
    </div>
    <div v-else-if="error" class="viewer-state is-error">{{ error }}</div>
    <div v-else-if="interactive" class="viewer-hint">拖动旋转 · 滚轮缩放 · 右键平移</div>
  </div>
</template>

<style scoped>
.urdf-viewer {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #f3f4f1;
}

.urdf-viewer :deep(canvas) {
  display: block;
  width: 100%;
  height: 100%;
  outline: none;
  pointer-events: none;
}

.urdf-viewer.is-interactive :deep(canvas) {
  pointer-events: auto;
  cursor: grab;
}

.urdf-viewer.is-interactive :deep(canvas):active {
  cursor: grabbing;
}

.viewer-state {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8a8e87;
  font-size: 13px;
}

.viewer-state.is-error {
  padding: 24px;
  color: #a3453d;
  text-align: center;
}

.viewer-loading-copy {
  width: min(240px, calc(100% - 48px));
}

.viewer-loading-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #555a53;
  font-size: 13px;
}

.viewer-progress {
  height: 4px;
  margin-top: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: #dfe2dc;
}

.viewer-progress span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #363a35;
  transition: width .18s ease;
}

.viewer-loading-copy small {
  display: block;
  margin-top: 9px;
  color: #9a9e98;
  text-align: center;
  font-size: 12px;
}

.viewer-hint {
  position: absolute;
  z-index: 2;
  left: 16px;
  bottom: 14px;
  padding: 6px 9px;
  border-radius: 4px;
  color: #686d66;
  background: rgba(255, 255, 255, .82);
  backdrop-filter: blur(6px);
  font-size: 12px;
  pointer-events: none;
}

</style>
