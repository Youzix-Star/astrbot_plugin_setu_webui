<script setup>
import { onMounted, nextTick } from 'vue'

// 你的 Twikoo 后端（Netlify 云函数）
const envId = 'https://youzix.dpdns.org/.netlify/functions/twikoo'

onMounted(async () => {
  await nextTick()
  // 只在浏览器环境加载 twikoo，避免 SSR 时 navigator 未定义报错
  if (typeof window !== 'undefined') {
    const twikoo = await import('twikoo')
    twikoo.init({
      envId,
      el: '#tcomment',
      path: window.location.pathname, // 按页面路径区分评论
      lang: 'zh-CN',
    })
  }
})
</script>

<template>
  <div id="tcomment"></div>
</template>