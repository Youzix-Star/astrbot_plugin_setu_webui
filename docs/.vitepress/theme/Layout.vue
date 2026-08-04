<script setup>
import DefaultTheme from 'vitepress/theme'
import { useData } from 'vitepress'
import Twikoo from './components/Twikoo.vue'

const { Layout } = DefaultTheme
const { page } = useData()
</script>

<template>
  <Layout>
    <!-- 所有页面底部都显示评论区 -->
    <template #doc-after>
      <Twikoo :key="page.relativePath" />
    </template>
  </Layout>
</template>