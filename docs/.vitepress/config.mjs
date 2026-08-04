import { defineConfig } from 'vitepress'

// GitHub Pages 子路径部署时传 DOCS_BASE=/仓库名/，Cloudflare Pages 默认 '/'
const base = process.env.DOCS_BASE || '/'

export default defineConfig({
  title: '云笺寻图',
  description: 'astrbot_plugin_nbsoutu_webui 使用文档',
  lang: 'zh-CN',
  base,
  lastUpdated: true,
  head: [
    ['link', { rel: 'preconnect', href: 'https://fonts.googleapis.com' }],
    ['link', { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' }],
    ['link', { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&display=swap' }],
  ],
  themeConfig: {
    logo: '/logo.png',
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