<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { fetchRobotUnits } from '../api/robots'

const props = defineProps({
  robot: { type: Object, required: true }, // { id, name, subtitle, image }
  vendorName: { type: String, default: '' },
})

const emit = defineEmits(['close', 'select'])

// 编号数量达到该值时显示搜索框；更少时直接列出即可
const SEARCH_THRESHOLD = 8

const units = ref([])
const loading = ref(false)
const error = ref('')
const query = ref('')
const searchInput = ref(null)

async function load() {
  loading.value = true
  error.value = ''
  query.value = ''
  try {
    units.value = await fetchRobotUnits(props.robot.id)
  } catch (e) {
    error.value = '加载机器人编号失败'
    units.value = []
  } finally {
    loading.value = false
    await nextTick()
    searchInput.value?.focus()
  }
}

watch(() => props.robot.id, load, { immediate: true })

const showSearch = computed(() => units.value.length >= SEARCH_THRESHOLD)

// 搜索：忽略大小写与连字符，输入 "13" 或 "g113" 都能匹配 "G1-1336"
function normalize(s) {
  return s.toLowerCase().replace(/[-\s]/g, '')
}

const filtered = computed(() => {
  const q = normalize(query.value)
  if (!q) return units.value
  return units.value.filter((u) => normalize(u).includes(q))
})

// 高亮匹配片段：返回 [前缀, 匹配, 后缀]
function highlight(unit) {
  const q = normalize(query.value)
  if (!q) return [unit, '', '']
  // 在原字符串上定位：逐字符跳过连字符建立映射
  const map = []
  for (let i = 0; i < unit.length; i++) {
    if (!/[-\s]/.test(unit[i])) map.push(i)
  }
  const idx = normalize(unit).indexOf(q)
  if (idx < 0) return [unit, '', '']
  const start = map[idx]
  const end = map[idx + q.length - 1] + 1
  return [unit.slice(0, start), unit.slice(start, end), unit.slice(end)]
}

function onKeydown(e) {
  if (e.key === 'Escape') {
    if (query.value) {
      query.value = ''
    } else {
      emit('close')
    }
  } else if (e.key === 'Enter' && filtered.value.length === 1) {
    // 搜索结果唯一时回车直接选中
    emit('select', filtered.value[0])
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="dialog" role="dialog" aria-modal="true">
      <header class="dialog-header">
        <div>
          <div class="dialog-eyebrow">{{ vendorName }}</div>
          <h2 class="dialog-title">
            {{ robot.name }} · 选择机器人编号
            <span v-if="units.length" class="dialog-count">共 {{ units.length }} 台</span>
          </h2>
        </div>
        <button class="close-btn" aria-label="关闭" @click="emit('close')">×</button>
      </header>

      <div v-if="showSearch" class="search">
        <svg class="search-icon" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <circle cx="9" cy="9" r="6" stroke="currentColor" stroke-width="1.6" />
          <path d="M13.5 13.5L17 17" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
        </svg>
        <input
          ref="searchInput"
          v-model="query"
          class="search-input"
          type="text"
          placeholder="输入编号搜索，如 1336"
          autocomplete="off"
          spellcheck="false"
        />
        <button v-if="query" class="search-clear" aria-label="清空" @click="query = ''">×</button>
      </div>

      <div class="dialog-body">
        <div v-if="loading" class="state">加载中…</div>
        <div v-else-if="error" class="state state-error">{{ error }}</div>
        <div v-else-if="!units.length" class="state">该机型下暂无机器人编号</div>
        <div v-else-if="!filtered.length" class="state">
          没有匹配「{{ query }}」的编号
        </div>
        <ul v-else class="unit-grid" :class="{ 'is-compact': !showSearch }">
          <li v-for="unit in filtered" :key="unit">
            <button class="unit-chip" @click="emit('select', unit)">
              <template v-if="query">
                <span>{{ highlight(unit)[0] }}</span><mark>{{ highlight(unit)[1] }}</mark><span>{{ highlight(unit)[2] }}</span>
              </template>
              <template v-else>{{ unit }}</template>
            </button>
          </li>
        </ul>
      </div>

      <footer v-if="showSearch && !loading && filtered.length" class="dialog-footer">
        <span v-if="query">匹配 {{ filtered.length }} 台</span>
        <span v-else>&nbsp;</span>
        <span v-if="filtered.length === 1" class="hint">按 Enter 选择</span>
        <span v-else class="hint">Esc 关闭</span>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 12vh;
  background: rgba(0, 0, 0, 0.35);
  animation: fade-in 0.15s ease;
}

.dialog {
  width: 480px;
  max-width: calc(100vw - 32px);
  max-height: 72vh;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.18);
  animation: pop-in 0.18s ease;
}

.dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 20px 20px 14px 24px;
}

.dialog-eyebrow {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}

.dialog-title {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: #1a1a1a;
}

.dialog-count {
  font-size: 12px;
  font-weight: 400;
  color: #999;
}

.close-btn {
  width: 28px;
  height: 28px;
  border-radius: 4px;
  font-size: 22px;
  line-height: 1;
  color: #999;
}

.close-btn:hover {
  background: #f5f5f5;
  color: #333;
}

/* 搜索框 */
.search {
  position: relative;
  display: flex;
  align-items: center;
  margin: 0 24px 4px;
  border-bottom: 1px solid #e8e8e8;
  transition: border-color 0.15s;
}

.search:focus-within {
  border-bottom-color: #1a1a1a;
}

.search-icon {
  width: 18px;
  height: 18px;
  flex: 0 0 18px;
  color: #999;
}

.search-input {
  flex: 1;
  min-width: 0;
  padding: 10px 10px;
  border: 0;
  outline: none;
  font: inherit;
  font-size: 15px;
  color: #1a1a1a;
  background: transparent;
}

.search-input::placeholder {
  color: #bbb;
}

.search-clear {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  font-size: 16px;
  line-height: 1;
  color: #999;
  background: #f0f0f0;
}

.search-clear:hover {
  color: #333;
  background: #e4e4e4;
}

.dialog-body {
  flex: 1;
  min-height: 0;
  padding: 12px 24px 16px;
  overflow-y: auto;
}

.state {
  padding: 32px 12px;
  text-align: center;
  font-size: 13px;
  color: #999;
}

.state-error {
  color: #d04040;
}

/* 编号网格 */
.unit-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.unit-grid.is-compact {
  grid-template-columns: repeat(2, 1fr);
}

.unit-chip {
  display: block;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  background: #fafafa;
  text-align: center;
  font-size: 14px;
  font-weight: 500;
  color: #1a1a1a;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.2px;
  transition: background 0.15s, border-color 0.15s, transform 0.15s;
}

.unit-chip:hover {
  background: #fff;
  border-color: #1a1a1a;
  transform: translateY(-1px);
}

.unit-chip mark {
  background: none;
  color: inherit;
  text-decoration: underline;
  text-decoration-color: #1a1a1a;
  text-decoration-thickness: 2px;
  text-underline-offset: 3px;
}

.dialog-footer {
  display: flex;
  justify-content: space-between;
  padding: 10px 24px 12px;
  border-top: 1px solid #f0f0f0;
  font-size: 12px;
  color: #999;
}

.hint {
  color: #bbb;
}

@keyframes fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes pop-in {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
</style>
