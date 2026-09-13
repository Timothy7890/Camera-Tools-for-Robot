<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, ref, watch } from 'vue'
import {
  calibrationFileUrl,
  fetchCalibrationFileJson,
  fetchCalibrationManifest,
  fetchCalibrationPreviewState,
} from '../api/robots'

const RobotUrdfViewer = defineAsyncComponent(() => import('./RobotUrdfViewer.vue'))

const props = defineProps({
  unitCode: { type: String, required: true },
  robot: { type: Object, default: null },
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
})

const ROLE_LABEL = { waist: '腰部相机', head: '头部相机' }
const ROLE_ORDER = { waist: 0, head: 1 }
const hydrated = ref([])
const hydrateError = ref('')
const selected = ref(null)
const viewer = ref(null)
let requestGeneration = 0
let previewTimer = null

const cameraItems = computed(() => props.items.filter((item) =>
  item.type === 'extrinsic' || item.type === 'intrinsic',
))

async function hydrate() {
  const generation = ++requestGeneration
  hydrateError.value = ''
  const byRole = new Map()
  for (const item of cameraItems.value) {
    const role = item.camera_role || item.subject_key
    if (!role) continue
    if (!byRole.has(role)) byRole.set(role, { role })
    const group = byRole.get(role)
    const current = group[item.type]
    if (!current || (item.status === 'active' && current.status !== 'active')) group[item.type] = item
  }

  try {
    const assets = await Promise.all([...byRole.values()].map(async (group) => {
      let extrinsicManifest = group.extrinsic || null
      let intrinsicManifest = group.intrinsic || null
      if (group.extrinsic?.id) {
        extrinsicManifest = await fetchCalibrationManifest(props.unitCode, group.extrinsic.id)
      }
      if (group.intrinsic?.id) {
        intrinsicManifest = await fetchCalibrationManifest(props.unitCode, group.intrinsic.id)
      }
      let intrinsics = {}
      if (group.intrinsic?.id) {
        const primary = intrinsicManifest?.primary_file
          || group.intrinsic.files?.find((file) => file.name === 'camera_intrinsics.json')?.name
          || group.intrinsic.files?.find((file) => file.name.endsWith('.json'))?.name
        if (primary) {
          try {
            intrinsics = await fetchCalibrationFileJson(props.unitCode, group.intrinsic.id, primary)
          } catch (error) {
            console.warn(`读取 ${group.role} 相机内参失败`, error)
          }
        }
      }
      const source = group.extrinsic || group.intrinsic
      return {
        ...group,
        label: source?.camera_label || ROLE_LABEL[group.role] || group.role,
        date: source?.created_at || '',
        status: group.extrinsic?.status || group.intrinsic?.status || 'draft',
        serial: source?.camera_serial || intrinsics.serial || '',
        transform: extrinsicManifest?.T_cam2base || null,
        parentFrame: extrinsicManifest?.frames?.parent || props.robot?.model?.anchorLink || 'torso_link',
        intrinsics,
        extrinsicManifest,
        intrinsicManifest,
        previewStatus: group.extrinsic?.preview_status || 'none',
        generatedPreviewUrl: group.extrinsic?.preview_url || '',
      }
    }))
    if (generation !== requestGeneration) return
    hydrated.value = assets.sort((a, b) =>
      (ROLE_ORDER[a.role] ?? 99) - (ROLE_ORDER[b.role] ?? 99) || a.label.localeCompare(b.label),
    )
    schedulePreviewRefresh()
  } catch (error) {
    if (generation !== requestGeneration) return
    hydrateError.value = error?.message || '相机标定详情加载失败'
    hydrated.value = []
  }
}

function shortDate(value) {
  if (!value) return '日期未知'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10)
  const pad = (number) => String(number).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function fullDate(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  }).format(date)
}

function statusText(status) {
  return { active: '生效中', draft: '草稿', superseded: '已替换' }[status] || status
}

function qualityText(asset) {
  const quality = asset.extrinsic?.quality || {}
  const parts = []
  if (quality.num_samples != null) {
    parts.push(quality.num_inliers != null
      ? `${quality.num_inliers}/${quality.num_samples} 内点`
      : `${quality.num_samples} 样本`)
  }
  if (quality.residual_translation_mm?.mean != null) {
    parts.push(`平移 ${Number(quality.residual_translation_mm.mean).toFixed(1)} mm`)
  }
  if (quality.residual_rotation_deg?.mean != null) {
    parts.push(`旋转 ${Number(quality.residual_rotation_deg.mean).toFixed(2)}°`)
  }
  return parts.join(' / ') || '-'
}

function resolutionText(asset) {
  const width = asset.intrinsics?.width || asset.intrinsic?.quality?.width
  const height = asset.intrinsics?.height || asset.intrinsic?.quality?.height
  return width && height ? `${width} × ${height}` : '-'
}

function allFiles(asset) {
  const records = [asset.extrinsic, asset.intrinsic].filter(Boolean)
  return records.flatMap((record) => (record.files || []).map((file) => ({ ...file, record })))
}

function fileUrl(file) {
  return calibrationFileUrl(props.unitCode, file.record.id, file.name)
}

function previewUrl(asset) {
  return asset.generatedPreviewUrl || props.robot?.model?.previews?.[asset.role] || ''
}

function schedulePreviewRefresh() {
  if (previewTimer) clearTimeout(previewTimer)
  previewTimer = null
  if (hydrated.value.some((asset) => asset.extrinsic?.id && asset.previewStatus === 'pending')) {
    previewTimer = setTimeout(refreshPreviewStatuses, 1800)
  }
}

async function refreshPreviewStatuses() {
  previewTimer = null
  const generation = requestGeneration
  const pending = hydrated.value.filter((asset) => asset.extrinsic?.id && asset.previewStatus === 'pending')
  const results = await Promise.allSettled(pending.map(async (asset) => ({
    asset,
    state: await fetchCalibrationPreviewState(props.unitCode, asset.extrinsic.id),
  })))
  if (generation !== requestGeneration) return
  for (const result of results) {
    if (result.status !== 'fulfilled') continue
    result.value.asset.previewStatus = result.value.state.status
    result.value.asset.generatedPreviewUrl = result.value.state.preview_url || ''
  }
  schedulePreviewRefresh()
}

function open(asset) {
  selected.value = asset
  document.documentElement.classList.add('has-calib-dialog')
}

function close() {
  selected.value = null
  document.documentElement.classList.remove('has-calib-dialog')
}

function onKeydown(event) {
  if (event.key === 'Escape' && selected.value) close()
}

watch(cameraItems, hydrate, { immediate: true })
watch(selected, (value) => {
  if (value) window.addEventListener('keydown', onKeydown)
  else window.removeEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  requestGeneration += 1
  if (previewTimer) clearTimeout(previewTimer)
  window.removeEventListener('keydown', onKeydown)
  document.documentElement.classList.remove('has-calib-dialog')
})
</script>

<template>
  <div class="camera-gallery-wrap">
    <div v-if="loading" class="gallery-state">正在加载相机标定…</div>
    <div v-else-if="error || hydrateError" class="gallery-state is-error">{{ error || hydrateError }}</div>
    <div v-else-if="!hydrated.length" class="gallery-state">
      暂无相机标定。机器人侧完成标定并归档后会自动同步到这里。
    </div>
    <div v-else class="camera-gallery">
      <button
        v-for="asset in hydrated"
        :key="asset.role"
        type="button"
        class="camera-card"
        :disabled="!robot?.model || !asset.transform"
        @click="open(asset)"
      >
        <div class="camera-preview">
          <img
            v-if="previewUrl(asset)"
            :src="previewUrl(asset)"
            :alt="`${asset.label}在机器人上的位置`"
            width="1200"
            height="800"
            decoding="async"
          />
          <div v-else class="preview-unavailable">
            <span>预览不可用</span>
            <small>{{ !robot?.model ? '该机型尚未配置模型' : '缺少预览图' }}</small>
          </div>
          <span v-if="robot?.model && asset.transform" class="preview-action">点击查看 3D</span>
        </div>
        <div class="camera-summary">
          <div>
            <strong>{{ asset.label }}</strong>
            <time :datetime="asset.date">{{ shortDate(asset.date) }}</time>
          </div>
          <span class="status" :class="`is-${asset.status}`">{{ statusText(asset.status) }}</span>
        </div>
      </button>
    </div>

    <Teleport to="body">
      <Transition name="viewer-dialog">
        <div v-if="selected" class="camera-dialog-backdrop" @click.self="close">
          <section class="camera-dialog" role="dialog" aria-modal="true" :aria-label="`${selected.label}三维查看器`">
            <header class="camera-dialog-header">
              <div>
                <div class="dialog-title-line">
                  <h2>{{ selected.label }}</h2>
                  <span class="status" :class="`is-${selected.status}`">{{ statusText(selected.status) }}</span>
                </div>
                <p>{{ unitCode }} · {{ selected.parentFrame }}</p>
              </div>
              <div class="dialog-header-actions">
                <button type="button" class="secondary-btn" @click="viewer?.resetView()">重置视角</button>
                <button type="button" class="close-btn" aria-label="关闭三维查看器" @click="close">×</button>
              </div>
            </header>
            <div class="camera-dialog-body">
              <div class="dialog-viewer">
                <Suspense>
                  <RobotUrdfViewer
                    ref="viewer"
                    :model="robot.model"
                    :transform="selected.transform"
                    :intrinsics="selected.intrinsics"
                    :camera-role="selected.role"
                    interactive
                  />
                  <template #fallback>
                    <div class="model-preparing">
                      <span>正在加载模型</span>
                      <div class="model-preparing-bar" role="progressbar" aria-label="模型加载进度">
                        <span></span>
                      </div>
                      <small>首次加载稍慢</small>
                    </div>
                  </template>
                </Suspense>
              </div>
              <aside class="camera-details">
                <h3>标定详情</h3>
                <dl>
                  <div><dt>相机位置</dt><dd>{{ selected.label }}</dd></div>
                  <div><dt>标定日期</dt><dd>{{ fullDate(selected.date) }}</dd></div>
                  <div><dt>序列号</dt><dd class="mono">{{ selected.serial || '-' }}</dd></div>
                  <div><dt>标定质量</dt><dd>{{ qualityText(selected) }}</dd></div>
                  <div><dt>图像尺寸</dt><dd>{{ resolutionText(selected) }}</dd></div>
                </dl>
                <div v-if="allFiles(selected).length" class="detail-files">
                  <h3>相关文件</h3>
                  <a v-for="file in allFiles(selected)" :key="`${file.record.id}-${file.name}`" :href="fileUrl(file)" :download="file.name">
                    <span>{{ file.name }}</span><span aria-hidden="true">↓</span>
                  </a>
                </div>
              </aside>
            </div>
          </section>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.camera-gallery {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.camera-card {
  min-width: 0;
  overflow: hidden;
  padding: 0;
  border: 1px solid #e5e7e2;
  border-radius: 9px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
}

.camera-card:hover:not(:disabled) {
  transform: translateY(-2px);
  border-color: #cfd2cc;
  box-shadow: 0 8px 22px rgba(25, 28, 23, .08);
}

.camera-card:focus-visible { outline: 2px solid #1a1a1a; outline-offset: 3px; }
.camera-card:disabled { cursor: default; }

.camera-preview {
  position: relative;
  height: 292px;
  overflow: hidden;
  background: #f3f4f1;
}

.camera-preview > img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-action {
  position: absolute;
  top: 13px;
  right: 13px;
  padding: 6px 9px;
  border: 1px solid rgba(0, 0, 0, .07);
  border-radius: 999px;
  color: #4d514b;
  background: rgba(255, 255, 255, .88);
  box-shadow: 0 2px 8px rgba(0, 0, 0, .06);
  font-size: 12px;
  pointer-events: none;
}

.preview-unavailable {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  color: #777;
}

.preview-unavailable small { color: #aaa; }

.camera-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 15px 16px 16px;
}

.camera-summary strong { display: block; color: #1b1d1a; font-size: 15px; font-weight: 500; }
.camera-summary time { display: block; margin-top: 4px; color: #858985; font-size: 13px; font-variant-numeric: tabular-nums; }

.status {
  display: inline-flex;
  align-items: center;
  flex: 0 0 auto;
  padding: 3px 8px;
  border-radius: 999px;
  background: #f0f1ef;
  color: #696d67;
  font-size: 12px;
  font-weight: 400;
}

.status.is-active { background: #1f211f; color: #fff; }
.status.is-superseded { color: #999; }
.status.is-draft { background: #eee9dc; color: #775e22; }

.gallery-state {
  padding: 54px 24px;
  border: 1px dashed #e1e3de;
  border-radius: 8px;
  color: #999;
  text-align: center;
  font-size: 13px;
}

.gallery-state.is-error { color: #a3453d; border-color: #ebcfcc; }

@media (max-width: 920px) {
  .camera-gallery { grid-template-columns: 1fr; }
  .camera-preview { height: 330px; }
}
</style>

<style>
html.has-calib-dialog { overflow: hidden; }

.camera-dialog-backdrop {
  position: fixed;
  z-index: 100;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 26px;
  background: rgba(20, 22, 19, .52);
  backdrop-filter: blur(5px);
}

.camera-dialog {
  width: min(1120px, 100%);
  max-height: calc(100vh - 52px);
  overflow: hidden;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 24px 70px rgba(0, 0, 0, .24);
}

.camera-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px 15px 22px;
  border-bottom: 1px solid #e8e9e6;
}

.dialog-title-line { display: flex; align-items: center; gap: 10px; }
.dialog-title-line h2 { margin: 0; color: #191b18; font-size: 19px; font-weight: 500; }
.camera-dialog-header p { margin: 4px 0 0; color: #898d87; font-size: 12px; }
.dialog-header-actions { display: flex; align-items: center; gap: 8px; }

.secondary-btn {
  height: 34px;
  padding: 0 12px;
  border: 1px solid #dedfdb;
  border-radius: 6px;
  color: #484c46;
  background: #fff;
  font-size: 13px;
}

.secondary-btn:hover { background: #f5f6f3; }

.camera-dialog .close-btn {
  width: 34px;
  height: 34px;
  border-radius: 6px;
  color: #777b75;
  font-size: 24px;
  line-height: 1;
}

.camera-dialog .close-btn:hover { background: #f3f4f1; color: #222; }

.camera-dialog-body { display: grid; grid-template-columns: minmax(0, 1fr) 300px; min-height: 0; }
.dialog-viewer {
  position: relative;
  height: min(680px, calc(100vh - 126px));
  min-height: 480px;
  background: #f3f4f1;
}

.model-preparing {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #555a53;
  font-size: 13px;
}

.model-preparing-bar {
  width: min(240px, calc(100% - 48px));
  height: 4px;
  margin-top: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: #dfe2dc;
}

.model-preparing-bar span {
  display: block;
  width: 38%;
  height: 100%;
  border-radius: inherit;
  background: #363a35;
  animation: model-preparing 1.1s ease-in-out infinite;
}

.model-preparing small {
  margin-top: 9px;
  color: #9a9e98;
  font-size: 12px;
}

.camera-details {
  max-height: min(680px, calc(100vh - 126px));
  overflow-y: auto;
  padding: 22px;
  border-left: 1px solid #e8e9e6;
}

.camera-details h3 { margin: 0 0 10px; color: #222420; font-size: 13px; font-weight: 500; }
.camera-details dl { margin: 0; }
.camera-details dl div { padding: 10px 0; border-bottom: 1px solid #eee; }
.camera-details dt { color: #999d97; font-size: 12px; }
.camera-details dd { margin: 3px 0 0; color: #353832; font-size: 13px; line-height: 1.5; }
.camera-details .mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.detail-files { margin-top: 24px; }

.detail-files a {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 0;
  border-bottom: 1px solid #eee;
  color: #3f433d;
  font-size: 12.5px;
  text-decoration: none;
}

.detail-files a:hover { color: #000; }
.viewer-dialog-enter-active, .viewer-dialog-leave-active { transition: opacity .18s ease; }
.viewer-dialog-enter-active .camera-dialog, .viewer-dialog-leave-active .camera-dialog { transition: transform .18s ease; }
.viewer-dialog-enter-from, .viewer-dialog-leave-to { opacity: 0; }
.viewer-dialog-enter-from .camera-dialog, .viewer-dialog-leave-to .camera-dialog { transform: translateY(8px) scale(.99); }

@keyframes model-preparing {
  from { transform: translateX(-155%); }
  to { transform: translateX(265%); }
}

@media (max-width: 760px) {
  .camera-dialog-backdrop { padding: 10px; align-items: flex-start; }
  .camera-dialog { max-height: calc(100vh - 20px); overflow-y: auto; }
  .camera-dialog-body { grid-template-columns: 1fr; }
  .dialog-viewer { height: 52vh; min-height: 330px; }
  .camera-details { max-height: none; border-left: 0; border-top: 1px solid #e8e9e6; }
  .secondary-btn { display: none; }
}
</style>
