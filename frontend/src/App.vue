<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import logo from './assets/bwton-logo.png'
import CalibMenuPanel from './components/CalibMenuPanel.vue'

const router = useRouter()
const route = useRoute()

// 「相机与工具标定文件」为悬停展开的面板，不是独立页面
const menuOpen = ref(false)
let closeTimer = null

function openMenu() {
  clearTimeout(closeTimer)
  menuOpen.value = true
}

// 离开后稍作延迟再关闭，避免鼠标在页签与面板之间移动时闪烁
function scheduleClose() {
  clearTimeout(closeTimer)
  closeTimer = setTimeout(() => {
    menuOpen.value = false
  }, 120)
}

function closeMenu() {
  clearTimeout(closeTimer)
  menuOpen.value = false
}

// 「使用说明」鼠标移入即切换页面，同时收起面板
function hoverGuide() {
  closeMenu()
  if (route.name !== 'guide') router.push({ name: 'guide' })
}

function onUnitSelected(unit) {
  closeMenu()
  router.push({ name: 'robot-detail', params: { unitCode: unit } })
}

// 路由变化时收起面板
watch(() => route.fullPath, closeMenu)
</script>

<template>
  <div class="layout">
    <div class="header-zone" @mouseleave="scheduleClose">
      <header class="topbar">
        <RouterLink to="/" class="brand" @mouseenter="closeMenu">
          <img :src="logo" alt="八维通 BWTON" class="brand-logo" />
        </RouterLink>
        <nav class="nav">
          <RouterLink
            :to="{ name: 'guide' }"
            class="nav-link"
            active-class="is-active"
            @mouseenter="hoverGuide"
          >
            使用说明
          </RouterLink>
          <button
            class="nav-link nav-trigger"
            :class="{ 'is-open': menuOpen, 'is-active': route.name === 'robot-detail' }"
            @mouseenter="openMenu"
            @click="openMenu"
          >
            相机与工具标定文件
          </button>
        </nav>
      </header>

      <Transition name="menu">
        <div v-if="menuOpen" class="mega-menu" @mouseenter="openMenu">
          <CalibMenuPanel @select-unit="onUnitSelected" />
        </div>
      </Transition>
    </div>

    <!-- 遮罩：位于 header-zone 之外，鼠标移到遮罩上即触发面板关闭 -->
    <Transition name="fade">
      <div v-if="menuOpen" class="mask" @click="closeMenu"></div>
    </Transition>

    <main class="content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.header-zone {
  position: sticky;
  top: 0;
  z-index: 30;
}

.topbar {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  height: 56px;
  padding: 0 32px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
}

.brand {
  display: flex;
  align-items: center;
  height: 100%;
  margin-right: 48px;
}

.brand-logo {
  height: 36px;
  display: block;
  /* 源图为黑底白字，反色后适配白色导航栏 */
  filter: invert(1);
}

.nav {
  display: flex;
  align-items: stretch;
  height: 100%;
  gap: 8px;
}

.nav-link {
  position: relative;
  display: flex;
  align-items: center;
  height: 56px;
  padding: 0 12px;
  font-size: 14px;
  color: #333;
  transition: color 0.15s;
}

.nav-link:hover,
.nav-link.is-open {
  color: #000;
}

.nav-link.is-active {
  color: #000;
  font-weight: 500;
}

.nav-link.is-active::after,
.nav-link.is-open::after {
  content: '';
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 0;
  height: 2px;
  background: #1a1a1a;
}

/* 悬停展开的面板 */
.mega-menu {
  position: absolute;
  top: 56px;
  left: 0;
  right: 0;
  z-index: 1;
  max-height: calc(100vh - 56px);
  overflow-y: auto;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.08);
}

.mask {
  position: fixed;
  inset: 0;
  z-index: 20;
  background: rgba(0, 0, 0, 0.45);
}

.content {
  flex: 1;
  display: flex;
  min-height: 0;
}

/* 过渡 */
.menu-enter-active,
.menu-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.menu-enter-from,
.menu-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
