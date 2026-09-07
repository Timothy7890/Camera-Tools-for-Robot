<script setup>
import { computed, ref } from 'vue'
import { vendors } from '../data/vendors'
import RobotPlaceholder from '../components/RobotPlaceholder.vue'
import RobotUnitPicker from '../components/RobotUnitPicker.vue'

const activeVendorId = ref(vendors[0]?.id ?? null)

const activeVendor = computed(() => vendors.find((v) => v.id === activeVendorId.value) ?? null)

// 鼠标移入厂家即切换，无需点击
function selectVendor(vendor) {
  activeVendorId.value = vendor.id
}

// 点击机型卡片 -> 弹出机器人编号选择
const pickingRobot = ref(null)

function openUnitPicker(robot) {
  pickingRobot.value = robot
}

function closeUnitPicker() {
  pickingRobot.value = null
}

function onUnitSelected(unit) {
  // TODO(backend): 选中编号后加载该机器人的相机标定文件列表
  console.log('[mock] 选中机器人编号:', unit)
  closeUnitPicker()
}
</script>

<template>
  <div class="page">
    <aside class="sidebar">
      <div class="sidebar-title">机器人厂家</div>

      <div
        v-for="vendor in vendors"
        :key="vendor.id"
        class="vendor-group"
        :class="{ 'is-active': vendor.id === activeVendorId }"
        @mouseenter="selectVendor(vendor)"
      >
        <div class="vendor-name">{{ vendor.name }}</div>

        <!-- 机型列表仅作展示，不可点击 -->
        <ul v-if="vendor.robots.length" class="robot-list">
          <li v-for="robot in vendor.robots" :key="robot.id" class="robot-item">
            <span class="robot-thumb">
              <img v-if="robot.image" :src="robot.image" :alt="robot.name" />
              <RobotPlaceholder v-else :size="28" />
            </span>
            <span class="robot-name">{{ robot.name }}</span>
          </li>
        </ul>
        <div v-else class="robot-empty">待补充</div>
      </div>
    </aside>

    <section class="main">
      <template v-if="activeVendor && activeVendor.robots.length">
        <div class="card-grid">
          <article
            v-for="robot in activeVendor.robots"
            :key="robot.id"
            class="robot-card"
            @click="openUnitPicker(robot)"
          >
            <div class="card-figure">
              <img v-if="robot.image" :src="robot.image" :alt="robot.name" />
              <RobotPlaceholder v-else :size="180" />
            </div>
            <h3 class="card-title">{{ robot.name }}</h3>
            <p class="card-subtitle">{{ robot.subtitle }}</p>
          </article>
        </div>
      </template>
      <div v-else class="main-empty">该厂家机型待补充</div>
    </section>

    <RobotUnitPicker
      v-if="pickingRobot"
      :robot="pickingRobot"
      :vendor-name="activeVendor?.name ?? ''"
      @close="closeUnitPicker"
      @select="onUnitSelected"
    />
  </div>
</template>

<style scoped>
.page {
  flex: 1;
  display: flex;
  min-height: 0;
}

/* 左侧栏 */
.sidebar {
  flex: 0 0 236px;
  padding: 24px 24px 24px 32px;
  border-right: 1px solid #f0f0f0;
}

.sidebar-title {
  font-size: 12px;
  color: #999;
  margin-bottom: 12px;
}

.vendor-group {
  padding: 4px 0 8px;
  border-radius: 4px;
  cursor: default;
  transition: background 0.15s;
}

.vendor-group + .vendor-group {
  margin-top: 12px;
}

.vendor-group.is-active {
  background: #f5f5f5;
}

.vendor-name {
  padding: 6px 8px;
  font-size: 13px;
  font-weight: 500;
  color: #444;
}

.vendor-group.is-active .vendor-name {
  color: #000;
}

.robot-list {
  list-style: none;
  margin: 4px 0 0;
  padding: 0;
}

.robot-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 8px;
  color: #333;
  user-select: none;
}

.robot-thumb {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
}

.robot-thumb img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.robot-name {
  font-size: 14px;
}

.robot-empty {
  padding: 6px 16px;
  font-size: 12px;
  color: #bbb;
}

/* 右侧内容区 */
.main {
  flex: 1;
  padding: 32px;
  min-width: 0;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
  max-width: 760px;
}

.robot-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 36px 16px 32px;
  background: #f5f5f5;
  border-radius: 4px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.robot-card:hover {
  background: #f0f0f0;
  transform: translateY(-3px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.06);
}

.robot-card:hover .card-figure {
  transform: scale(1.04);
}

.card-figure {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 200px;
  height: 220px;
  margin-bottom: 20px;
  transition: transform 0.25s ease;
}

.card-figure img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.card-title {
  margin: 0;
  font-size: 18px;
  font-weight: 500;
  color: #1a1a1a;
}

.card-subtitle {
  margin: 8px 0 0;
  font-size: 13px;
  color: #666;
}

.main-empty {
  color: #999;
  font-size: 14px;
}
</style>
