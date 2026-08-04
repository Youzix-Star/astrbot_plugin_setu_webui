# 快速开始

## 这是什么

**云笺寻图**（`astrbot_plugin_nbsoutu_webui`）是 AstrBot 的随机图片插件：

- 支持 **7 大图源**：Lolicon、UApiPro、Bing、imgapi、dmoe、LoliAPI、栗次元
- 指令、LLM 工具、WebUI **三种方式**取图
- 获取后**勾选群一键发送**

## 环境要求

- AstrBot（已运行）
- QQ 平台适配器（aiocqhttp / NapCat）
- 浏览器（使用 WebUI 时）

## 安装

1. 在 AstrBot 插件市场搜索「云笺寻图」，或手动克隆到 plugins 目录：

   ```bash
   git clone https://github.com/Youzix-Star/astrbot_plugin_nbsoutu_webui.git
   ```

2. 重启 AstrBot 使插件加载。

## 快速使用

| 方式 | 说明 |
| --- | --- |
| `/setu` | 随机来一张（默认 Lolicon） |
| `/setu random` | 全随机：50 种图源 × 分类等概率抽取 |
| `/setu 关键词` | 按标签搜，如 `/setu 百合` |
| WebUI | 插件页面点几下取图，勾选群一键发送 |

## 试试这些

```bash
/setu
/setu random
/setu alcy xhl
/setu uapipro furry+4k
```

::: tip 提示
群内输入 `/setu help` 会召唤一张杂志风帮助海报，分类一目了然。
:::