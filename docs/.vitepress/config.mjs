import { defineConfig } from 'vitepress'

// GitHub Pages 子路径部署时传 DOCS_BASE=/仓库名/，Cloudflare Pages 默认 '/'
const base = process.env.DOCS_BASE || '/'

export default defineConfig({
  title: '云笺寻图',
  description: 'astrbot_plugin_nbsoutu_webui 使用文档',
  lang: 'zh-CN',
  base,
  lastUpdated: true,
  themeConfig: {
    nav: [
      { text: '首页', link: '/' },
      { text: 'GitHub', link: 'https://github.com/Youzix-Star/astrbot_plugin_nbsoutu_webui' },
    ],
    search: { provider: 'local' },
    footer: {
      message: '云笺寻图 · 名字来源 · 陌袹陌',
      copyright: 'AGPLv3'
    },
    socialLinks: [
      { icon: 'github', link: 'https://github.com/Youzix-Star/astrbot_plugin_nbsoutu_webui' }
    ]
  }
})