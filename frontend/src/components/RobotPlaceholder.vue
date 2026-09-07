<script setup>
// 机器人图片占位（人形轮廓），待正式素材替换
defineProps({
  size: { type: Number, default: 160 },
})
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 100 100"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <g fill="#d4d4d4">
      <ellipse cx="50" cy="12" rx="7" ry="8" />
      <rect x="47" y="20" width="6" height="4" rx="1" />
      <path d="M38 25h24a3 3 0 0 1 3 3v22a3 3 0 0 1-3 3H38a3 3 0 0 1-3-3V28a3 3 0 0 1 3-3z" />
      <rect x="28" y="27" width="6" height="26" rx="3" />
      <rect x="66" y="27" width="6" height="26" rx="3" />
      <rect x="40" y="54" width="8" height="30" rx="3" />
      <rect x="52" y="54" width="8" height="30" rx="3" />
      <rect x="38" y="84" width="11" height="5" rx="2" />
      <rect x="51" y="84" width="11" height="5" rx="2" />
    </g>
  </svg>
</template>
