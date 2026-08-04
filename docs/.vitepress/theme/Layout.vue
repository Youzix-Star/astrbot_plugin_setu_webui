<script setup>
import DefaultTheme from 'vitepress/theme'
import Twikoo from './Twikoo.vue'

const { Layout } = DefaultTheme
</script>

<template>
  <Layout>
    <!-- 文章页底部评论区（首页不显示，保持现状） -->
    <template #doc-after>
      <Twikoo></Twikoo>
    </template>
  </Layout>
</template>

<style>
.twikoo .el-loading-spinner .circular {
  margin-left: auto;
  margin-right: auto;
}
</style>