<script setup>
import DefaultTheme from 'vitepress/theme'
import { useData } from 'vitepress'
import Twikoo from './components/Twikoo.vue'

const { Layout } = DefaultTheme
const { page } = useData()
</script>

<template>
  <Layout>
    <!-- 文章页底部插入评论；首页 Hero 不显示 -->
    <template #doc-after>
      <Twikoo v-if="page.relativePath !== 'index.md'" :key="page.relativePath" />
    </template>
  </Layout>
</template>