<script setup>
import { useRoute, useRouter } from 'vue-router'
import logo from './assets/bwton-logo.png'

const navItems = [
  { name: 'guide', label: '使用说明' },
  { name: 'camera-calibration', label: '相机标定文件' },
  { name: 'tool-calibration', label: '工具标定文件' },
]

const router = useRouter()
const route = useRoute()

// 鼠标移入即切换页签，无需点击
function switchTo(name) {
  if (route.name !== name) router.push({ name })
}
</script>

<template>
  <div class="layout">
    <header class="topbar">
      <RouterLink to="/" class="brand">
        <img :src="logo" alt="八维通 BWTON" class="brand-logo" />
      </RouterLink>
      <nav class="nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.name"
          :to="{ name: item.name }"
          class="nav-link"
          active-class="is-active"
          @mouseenter="switchTo(item.name)"
        >
          {{ item.label }}
        </RouterLink>
      </nav>
    </header>

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

.topbar {
  position: sticky;
  top: 0;
  z-index: 10;
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
  padding: 0 12px;
  font-size: 14px;
  color: #333;
  transition: color 0.15s;
}

.nav-link:hover {
  color: #000;
}

.nav-link.is-active {
  color: #000;
  font-weight: 500;
}

.nav-link.is-active::after {
  content: '';
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 0;
  height: 2px;
  background: #1a1a1a;
}

.content {
  flex: 1;
  display: flex;
  min-height: 0;
}
</style>
