<script setup>
import { computed } from 'vue'
import { calibrationFileUrl } from '../api/robots'

const props = defineProps({
  unitCode: { type: String, required: true },
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
})

const STATUS = {
  active: { text: '生效中', cls: 'is-active' },
  superseded: { text: '已替换', cls: 'is-old' },
  draft: { text: '草稿', cls: 'is-draft' },
}

// 生效中的排最前，其余按时间倒序（后端已倒序）
const sorted = computed(() =>
  [...props.items].sort((a, b) => (a.status === 'active' ? -1 : 0) - (b.status === 'active' ? -1 : 0)),
)

function fmtTime(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

// 旧版 manifest 没有 camera_label 时，用内置位置名兜底
const ROLE_LABEL = { head: '头部相机', waist: '腰部相机' }

function cameraText(item) {
  const label = item.camera_label || ROLE_LABEL[item.camera_role] || item.camera_role
  return item.camera_serial ? `${label} · ${item.camera_serial}` : label
}

const ARM = { left: '左臂', right: '右臂' }

// 把 quality 压成一行摘要，不同类型字段不同
function qualityText(item) {
  const q = item.quality || {}
  const parts = []
  if (q.num_samples != null) {
    parts.push(q.num_inliers != null ? `${q.num_inliers}/${q.num_samples} 内点` : `${q.num_samples} 样本`)
  }
  const t = q.residual_translation_mm
  if (t?.mean != null) parts.push(`平移 ${Number(t.mean).toFixed(1)} mm`)
  const r = q.residual_rotation_deg
  if (r?.mean != null) parts.push(`旋转 ${Number(r.mean).toFixed(2)}°`)
  if (q.width && q.height) parts.push(`${q.width}×${q.height}`)
  if (q.source) parts.push(String(q.source))
  return parts.join(' / ')
}

function fileUrl(item, name) {
  return calibrationFileUrl(props.unitCode, item.id, name)
}
</script>

<template>
  <div class="list">
    <div v-if="loading" class="state">加载中…</div>
    <div v-else-if="error" class="state is-error">{{ error }}</div>
    <div v-else-if="!items.length" class="state">暂无数据。机器人侧完成标定并归档后会自动同步到这里。</div>

    <table v-else class="table">
      <thead>
        <tr>
          <th>运行</th>
          <th>相机</th>
          <th>手臂</th>
          <th>时间</th>
          <th>质量</th>
          <th>状态</th>
          <th>文件</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in sorted" :key="item.id" :class="{ 'row-active': item.status === 'active' }">
          <td class="mono nowrap">{{ item.run_id }}</td>
          <td class="nowrap">{{ cameraText(item) }}</td>
          <td class="nowrap">{{ ARM[item.arm] ?? item.arm ?? '-' }}</td>
          <td class="nowrap mono">{{ fmtTime(item.created_at) }}</td>
          <td class="quality">{{ qualityText(item) || '-' }}</td>
          <td class="nowrap">
            <span class="badge" :class="STATUS[item.status]?.cls">{{ STATUS[item.status]?.text ?? item.status }}</span>
          </td>
          <td class="files">
            <a
              v-for="f in item.files"
              :key="f.name"
              class="file"
              :href="fileUrl(item, f.name)"
              :download="f.name"
              :title="`${f.bytes ?? ''} bytes`"
            >{{ f.name }}</a>
            <a class="file file-meta" :href="`/api/robots/units/${encodeURIComponent(unitCode)}/calibrations/${item.id}`" target="_blank" rel="noopener">manifest</a>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.state {
  padding: 40px 24px;
  border: 1px dashed #e8e8e8;
  border-radius: 6px;
  text-align: center;
  font-size: 13px;
  color: #aaa;
}

.state.is-error {
  color: #c0392b;
  border-color: #f3d6d2;
}

.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.table th,
.table td {
  padding: 9px 10px;
  border-bottom: 1px solid #f0f0f0;
  text-align: left;
  vertical-align: top;
}

.table th {
  font-weight: 500;
  font-size: 12px;
  color: #999;
  white-space: nowrap;
}

.row-active td {
  background: #fafafa;
}

.mono {
  font-variant-numeric: tabular-nums;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12.5px;
}

.nowrap {
  white-space: nowrap;
}

.quality {
  color: #555;
  min-width: 160px;
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: #f0f0f0;
  color: #666;
}

.badge.is-active {
  background: #1a1a1a;
  color: #fff;
}

.badge.is-old {
  background: #f5f5f5;
  color: #999;
}

.files {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 10px;
}

.file {
  color: #1a1a1a;
  text-decoration: underline;
  text-decoration-color: #ccc;
  white-space: nowrap;
}

.file:hover {
  text-decoration-color: #1a1a1a;
}

.file-meta {
  color: #999;
}
</style>
