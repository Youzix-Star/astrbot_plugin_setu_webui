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
    ['link', { rel: 'icon', type: 'image/png', href: '/logo.png' }],
  ],
  themeConfig: {
    logo: '/logo.png',
    nav: [
      { text: '首页', link: '/' },
      {
        text: '指南',
        items: [
          { text: '快速开始', link: '/guide/' },
          { text: '快速部署与使用', link: '/guide/deploy' },
          { text: '指令速查', link: '/guide/commands' },
          { text: '配置与积木编程', link: '/guide/presets' },
          { text: 'WebUI 指南', link: '/guide/webui' },
        ],
      },
      { text: 'GitHub', link: 'https://github.com/Youzix-Star/astrbot_plugin_nbsoutu_webui' },
    ],
    sidebar: [
      {
        text: '指南',
        items: [
          { text: '快速开始', link: '/guide/' },
          { text: '快速部署与使用', link: '/guide/deploy' },
          { text: '指令速查', link: '/guide/commands' },
          { text: '配置与积木编程', link: '/guide/presets' },
          { text: 'WebUI 指南', link: '/guide/webui' },
        ],
      },
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