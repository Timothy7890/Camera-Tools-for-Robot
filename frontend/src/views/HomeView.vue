<script setup>
import { calibSections } from '../data/calibSections'
</script>

<template>
  <section class="home">
    <div class="home-inner">
      <header class="home-header">
        <h1 class="home-title">相机与工具标定文件</h1>
        <p class="home-desc">
          按机器人厂家与机型管理各台机器人的标定文件。从顶部导航选择机型与编号后进入对应机器人的文件页面。
        </p>
      </header>

      <div class="section-grid">
        <article v-for="section in calibSections" :key="section.id" class="section-card">
          <h2 class="section-name">{{ section.name }}</h2>
          <p class="section-desc">{{ section.desc }}</p>
          <!-- TODO: 各分类的概览内容待设计 -->
          <div class="section-status">待开发</div>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.home {
  flex: 1;
  min-width: 0;
}

.home-inner {
  max-width: 1120px;
  margin: 0 auto;
  padding: 48px 32px;
}

.home-header {
  margin-bottom: 36px;
}

.home-title {
  margin: 0 0 10px;
  font-size: 28px;
  font-weight: 600;
  color: #1a1a1a;
}

.home-desc {
  margin: 0;
  max-width: 640px;
  font-size: 14px;
  line-height: 1.7;
  color: #666;
}

.section-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.section-card {
  display: flex;
  flex-direction: column;
  padding: 28px 24px 22px;
  background: #f5f5f5;
  border-radius: 6px;
  min-height: 180px;
}

.section-name {
  margin: 0 0 8px;
  font-size: 17px;
  font-weight: 500;
  color: #1a1a1a;
}

.section-desc {
  margin: 0;
  flex: 1;
  font-size: 13px;
  line-height: 1.6;
  color: #777;
}

.section-status {
  align-self: flex-start;
  margin-top: 20px;
  padding: 3px 10px;
  border-radius: 999px;
  background: #e9e9e9;
  font-size: 12px;
  color: #666;
}

@media (max-width: 900px) {
  .section-grid {
    grid-template-columns: 1fr;
  }
}
</style>
