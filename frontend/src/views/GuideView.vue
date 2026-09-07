<template>
  <section class="guide">
    <div class="guide-inner">
      <h1 class="guide-title">使用说明</h1>
      <p class="guide-desc">相机标定与工具标定的操作流程、注意事项及常见问题。</p>

      <!-- TODO: 使用说明正文待编写 -->
      <div class="placeholder">
        <div class="placeholder-badge">待开发</div>
        <p class="placeholder-text">此页面内容尚在整理中，后续将补充相机标定与工具标定的完整使用说明。</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.guide {
  flex: 1;
  min-width: 0;
}

.guide-inner {
  max-width: 1120px;
  margin: 0 auto;
  padding: 48px 32px;
}

.guide-title {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 600;
  color: #1a1a1a;
}

.guide-desc {
  margin: 0 0 40px;
  font-size: 14px;
  color: #666;
}

.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 72px 24px;
  border: 1px dashed #e8e8e8;
  border-radius: 6px;
  text-align: center;
}

.placeholder-badge {
  padding: 3px 10px;
  border-radius: 999px;
  background: #f0f0f0;
  font-size: 12px;
  color: #666;
}

.placeholder-text {
  margin: 0;
  font-size: 13px;
  color: #aaa;
}
</style>
