<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'

// 你的 Twikoo 后端（Netlify 云函数）
const envId = 'https://youzix.dpdns.org/.netlify/functions/twikoo'

const el = ref(null)
let destroyed = false

onMounted(async () => {
  await nextTick()
  const node = el.value
  if (typeof window === 'undefined' || !node) return

  // 动态加载 twikoo（SSR 安全）
  const twikoo = await import('twikoo')

  // 切页后丢弃迟到的渲染，避免把上一页评论塞进新页面
  if (destroyed || !node.isConnected) return

  node.innerHTML = '' // 防御：清空容器
  twikoo.init({
    envId,
    el: node,          // 直接传元素，不靠全局 id 选择器
    path: window.location.pathname,
    lang: 'zh-CN',
  })
})

onUnmounted(() => { destroyed = true })
</script>

<template>
  <div ref="el"></div>
</template>