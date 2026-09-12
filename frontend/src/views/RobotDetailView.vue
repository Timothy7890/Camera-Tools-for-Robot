<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { findRobotByUnitCode } from '../data/vendors'
import { calibSections, findSection } from '../data/calibSections'
import RobotPlaceholder from '../components/RobotPlaceholder.vue'
import CalibrationList from '../components/CalibrationList.vue'
import CameraCalibrationGallery from '../components/CameraCalibrationGallery.vue'
import { fetchCalibrations } from '../api/robots'

const route = useRoute()
const router = useRouter()

const unitCode = computed(() => String(route.params.unitCode ?? ''))
const match = computed(() => findRobotByUnitCode(unitCode.value))
const robot = computed(() => match.value?.robot ?? null)
const vendor = computed(() => match.value?.vendor ?? null)

// 顶部导航高度，滚动定位与滚动监听都要减去它
const HEADER_OFFSET = 56
// 判定"当前栏目"的视线位置：视口顶部再往下一点
const SPY_OFFSET = HEADER_OFFSET + 24

const activeSectionId = ref(calibSections[0].id)
const sectionEls = new Map()

function setSectionEl(id, el) {
  if (el) sectionEls.set(id, el)
  else sectionEls.delete(id)
}

// 各类产物在同一页面内连续排列，滚动时高亮当前经过的栏目
let ticking = false
function onScroll() {
  if (ticking) return
  ticking = true
  requestAnimationFrame(() => {
    ticking = false
    let current = calibSections[0].id
    for (const section of calibSections) {
      const el = sectionEls.get(section.id)
      if (!el) continue
      if (el.getBoundingClientRect().top - SPY_OFFSET <= 0) current = section.id
    }
    // 滚到底部时，确保最后一个栏目被高亮
    const doc = document.documentElement
    if (window.innerHeight + window.scrollY >= doc.scrollHeight - 2) {
      current = calibSections[calibSections.length - 1].id
    }
    activeSectionId.value = current
  })
}

function scrollToSection(id, smooth = true) {
  const el = sectionEls.get(id)
  if (!el) return
  const top = el.getBoundingClientRect().top + window.scrollY - HEADER_OFFSET
  window.scrollTo({ top, behavior: smooth ? 'smooth' : 'auto' })
}

function onMenuClick(section) {
  scrollToSection(section.id)
  // 同步到地址栏，便于分享定位；不触发页面重载
  router.replace({ name: 'robot-detail', params: { unitCode: unitCode.value, section: section.id } })
}

onMounted(async () => {
  window.addEventListener('scroll', onScroll, { passive: true })
  await nextTick()
  const initial = String(route.params.section ?? '')
  const initialSection = findSection(initial)
  if (initialSection) scrollToSection(initialSection.id, false)
  onScroll()
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
})

// 切换到另一台机器人时回到顶部
watch(unitCode, () => {
  window.scrollTo({ top: 0 })
  onScroll()
})

// ---- 标定产物：一次拉全量，按栏目类型分组 ----
// manifest 里的类型用下划线，栏目 id 用连字符
const SECTION_TYPE = {
  'camera-transform': 'camera_transform',
  'hand-mount': 'hand_mount',
  'tcp-profile': 'tcp_profile',
}

const calibLoading = ref(false)
const calibError = ref('')
const calibItems = ref([])

const itemsBySection = computed(() => {
  const out = {}
  for (const section of calibSections) out[section.id] = []
  for (const item of calibItems.value) {
    if (item.type === 'extrinsic' || item.type === 'intrinsic') {
      out.camera.push(item)
      continue
    }
    const sid = Object.keys(SECTION_TYPE).find((k) => SECTION_TYPE[k] === item.type)
    if (sid) out[sid].push(item)
  }
  return out
})

async function loadCalibrations() {
  const code = unitCode.value
  calibLoading.value = true
  calibError.value = ''
  try {
    const items = await fetchCalibrations(code)
    if (code === unitCode.value) calibItems.value = items
  } catch (e) {
    if (code === unitCode.value) {
      calibItems.value = []
      calibError.value = `加载失败：${e.message || e}`
    }
  } finally {
    if (code === unitCode.value) calibLoading.value = false
  }
}

watch(unitCode, loadCalibrations, { immediate: true })
</script>

<template>
  <div class="detail">
    <header class="hero">
      <div class="hero-inner">
        <div class="hero-figure">
          <img v-if="robot?.image" :src="robot.image" :alt="robot.name" />
          <RobotPlaceholder v-else :size="96" />
        </div>
        <div class="hero-text">
          <div class="hero-eyebrow">
            <span v-if="vendor">{{ vendor.name }}</span>
            <span v-if="vendor && robot" class="dot">·</span>
            <span v-if="robot">{{ robot.name }} {{ robot.subtitle }}</span>
            <span v-if="!robot">未知机型</span>
          </div>
          <h1 class="hero-title">{{ unitCode }}</h1>
        </div>
      </div>
    </header>

    <div class="body">
      <aside class="side">
        <div class="side-sticky">
          <div class="side-title">标定文件</div>
          <nav class="side-menu">
            <button
              v-for="section in calibSections"
              :key="section.id"
              class="side-item"
              :class="{ 'is-active': section.id === activeSectionId }"
              @click="onMenuClick(section)"
            >
              {{ section.name }}
            </button>
          </nav>
        </div>
      </aside>

      <main class="main">
        <section
          v-for="section in calibSections"
          :key="section.id"
          :id="section.id"
          :ref="(el) => setSectionEl(section.id, el)"
          class="block"
        >
          <header class="block-header">
            <h2 class="block-title">{{ section.name }}</h2>
            <p class="block-desc">{{ section.desc }}</p>
          </header>

          <CameraCalibrationGallery
            v-if="section.id === 'camera'"
            :unit-code="unitCode"
            :robot="robot"
            :items="itemsBySection.camera"
            :loading="calibLoading"
            :error="calibError"
          />
          <CalibrationList
            v-else
            :unit-code="unitCode"
            :items="itemsBySection[section.id]"
            :loading="calibLoading"
            :error="calibError"
          />
        </section>
      </main>
    </div>
  </div>
</template>

<style scoped>
.detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* 顶部 hero：压缩为一条信息栏 */
.hero {
  background: #f5f5f5;
  border-bottom: 1px solid #ececec;
}

.hero-inner {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 14px 32px;
}

.hero-figure {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 96px;
  flex: 0 0 72px;
}

.hero-figure img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.hero-text {
  min-width: 0;
}

.hero-eyebrow {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #666;
  margin-bottom: 4px;
}

.dot {
  color: #bbb;
}

.hero-title {
  margin: 0;
  font-size: 28px;
  font-weight: 600;
  letter-spacing: 0.5px;
  color: #1a1a1a;
  font-variant-numeric: tabular-nums;
}

/* 下方：左菜单贴边 + 右内容 */
.body {
  flex: 1;
  display: flex;
  min-height: 0;
}

.side {
  flex: 0 0 220px;
  border-right: 1px solid #f0f0f0;
}

.side-sticky {
  position: sticky;
  top: 56px;
  padding: 24px 16px 24px 24px;
}

.side-title {
  padding: 0 12px;
  margin-bottom: 8px;
  font-size: 12px;
  color: #999;
}

.side-menu {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.side-item {
  position: relative;
  display: block;
  width: 100%;
  padding: 9px 12px;
  border-radius: 4px;
  text-align: left;
  font-size: 14px;
  color: #444;
  transition: background 0.15s, color 0.15s;
}

.side-item:hover {
  background: #f7f7f7;
  color: #000;
}

.side-item.is-active {
  background: #f2f2f2;
  color: #000;
  font-weight: 500;
}

.side-item.is-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 2px;
  border-radius: 1px;
  background: #1a1a1a;
}

.main {
  flex: 1;
  min-width: 0;
  max-width: 960px;
  padding: 8px 40px 40px;
}

/* 每个栏目为一个区块，连续排列 */
.block {
  padding: 24px 0 8px;
  scroll-margin-top: 56px;
}

.block + .block {
  margin-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.block-header {
  margin-bottom: 20px;
}

.block-title {
  margin: 0 0 6px;
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
}

.block-desc {
  margin: 0;
  font-size: 13px;
  color: #888;
}

</style>
