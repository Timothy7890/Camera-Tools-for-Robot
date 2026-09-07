<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { findRobotByUnitCode } from '../data/vendors'
import RobotPlaceholder from '../components/RobotPlaceholder.vue'

const route = useRoute()

const unitCode = computed(() => String(route.params.unitCode ?? ''))
const match = computed(() => findRobotByUnitCode(unitCode.value))
const robot = computed(() => match.value?.robot ?? null)
const vendor = computed(() => match.value?.vendor ?? null)
</script>

<template>
  <div class="detail">
    <header class="hero">
      <div class="hero-inner">
        <div class="hero-figure">
          <img v-if="robot?.image" :src="robot.image" :alt="robot.name" />
          <RobotPlaceholder v-else :size="200" />
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

    <!-- TODO: 相机与工具标定文件内容区，待设计 -->
    <section class="body">
      <div class="body-placeholder">内容区待设计</div>
    </section>
  </div>
</template>

<style scoped>
.detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.hero {
  background: #f5f5f5;
  border-bottom: 1px solid #ececec;
}

.hero-inner {
  display: flex;
  align-items: center;
  gap: 40px;
  max-width: 1120px;
  margin: 0 auto;
  padding: 36px 32px;
}

.hero-figure {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 200px;
  height: 220px;
  flex: 0 0 200px;
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
  font-size: 14px;
  color: #666;
  margin-bottom: 10px;
}

.dot {
  color: #bbb;
}

.hero-title {
  margin: 0;
  font-size: 40px;
  font-weight: 600;
  letter-spacing: 0.5px;
  color: #1a1a1a;
  font-variant-numeric: tabular-nums;
}

.body {
  flex: 1;
  max-width: 1120px;
  width: 100%;
  margin: 0 auto;
  padding: 48px 32px;
}

.body-placeholder {
  padding: 64px 0;
  text-align: center;
  font-size: 13px;
  color: #ccc;
  border: 1px dashed #e8e8e8;
  border-radius: 6px;
}
</style>
