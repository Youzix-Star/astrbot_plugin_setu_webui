# 快速部署与使用

## 1. 准备 AstrBot

- 安装并启动 AstrBot（安装方式见 AstrBot 官方文档）。
- 确保 AstrBot 能正常打开 WebUI。

## 2. 配置 QQ 适配器

插件通过 **NapCat 的 HTTP API** 与 QQ 通信，请按以下步骤准备：

1. 安装并启动 [**NapCat**](https://napneko.github.io/)；
   > 大概你已经装了，那就跳过~
2. 访问 `http://你的IP:6099`；
   > 端口按 NapCat 实际的来，别真拿 6099 撞南墙
3. 在 NapCat 的 WebUI **左上角**打开**网络配置**；
4. 新建 HTTP 服务器配置如下：

   | 配置 | 默认值 | 说明 |
   | --- | --- | --- |
   | HTTP 地址 | `http://127.0.0.1:3000` | NapCat HTTP 服务 |
   | token | `awa` | Bearer Token |

   ::: warning 注意
   以上默认值硬编码在 `main.py` 顶部（`NAPCAT_HTTP` / `NAPCAT_TOKEN`）。如与你的 NapCat 配置不一致，请修改后重启 AstrBot。
   :::

5. 确保 AstrBot 所在环境能访问该地址（同机一般没问题）；
6. 在 AstrBot 中添加 **aiocqhttp** 平台适配器并连接 NapCat（发送图片依赖它）。

## 3. 安装插件

1. 安装本插件：`https://github.com/Youzix-Star/astrbot_plugin_nbsoutu_webui.git`
2. 重启 AstrBot 使插件生效。

## 4. 开始使用

| 方式 | 操作 |
| --- | --- |
| 群内指令 | 输入 `/setu`、`/setu random`、`/setu alcy xhl` 等 |
| LLM 对话 | 让 AI「来张原神的图」，AI 会自动调用 |
| WebUI | AstrBot 插件页打开「云笺寻图」，快速获取 / 积木编程 / 调用记录 |

## 5. 常见问题

| 现象 | 排查 |
| --- | --- |
| 取图失败 | 推荐使用大陆服务器，否则部分 API 无法访问 |
| 群列表加载失败 | 确认正确配置 NapCat HTTP 服务器 |
| 日志看不到记录 | 调用记录上限 100 条，超限会丢弃最旧记录 |