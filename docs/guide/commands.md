# 指令速查

## 基本指令

| 指令 | 说明 |
| --- | --- |
| `/setu` | 随机来一张（默认 Lolicon） |
| `/setu random` | 全随机：50 种图源 × 分类等概率抽取 |
| `/setu 关键词` | 按标签搜，如 `/setu 百合` |
| `/setu list` | 查看已保存的配置与指令 |
| `/setu help` | 召唤一张杂志风帮助海报 |

> 别名：`色图`、`随机图`、`随机图片` 也能触发 `/setu`

## 图源 · 指令全表

<details>
<summary><b>Lolicon（默认）</b></summary>

```
/setu              随机来一张
/setu 原神         按标签搜（多个逗号分隔）
```

</details>

<details>
<summary><b>栗次元 alcy</b></summary>

```
/setu alcy <分类>
```

| 分类 | 说明 |
| --- | --- |
| `ycy` | 二次元自适应 |
| `moez` | 萌版自适应 |
| `ai` | AI 自适应 |
| `ysz` | 原神自适应 |
| `pc` | PC 横图 |
| `moe` | 萌版横图 |
| `fj` | 风景横图 |
| `bd` | 白底横图 |
| `ys` | 原神横图 |
| `acg` | 动图 |
| `mp` | 移动竖图 |
| `moemp` | 萌版竖图 |
| `ysmp` | 原神竖图 |
| `aimp` | AI 竖图 |
| `fjmp` | 风景竖图 |
| `tx` | 头像方图 |
| `lai` | 七濑胡桃 |
| `xhl` | 小狐狸 |

</details>

<details>
<summary><b>UApiPro uapipro</b></summary>

```
/setu uapipro <主分类>
/setu uapipro <主分类+子分类>
```

主分类：

| 主分类 | 指令 | 说明 |
| --- | --- | --- |
| `acg` | `/setu uapipro acg` | 二次元 |
| `landscape` | `/setu uapipro landscape` | 风景 |
| `anime` | `/setu uapipro anime` | 动漫混合 |
| `pc_wallpaper` | `/setu uapipro pc_wallpaper` | 电脑壁纸 |
| `mobile_wallpaper` | `/setu uapipro mobile_wallpaper` | 手机壁纸 |
| `general_anime` | `/setu uapipro general_anime` | 动漫图 |
| `ai_drawing` | `/setu uapipro ai_drawing` | AI 绘画 |
| `bq` | `/setu uapipro bq` | 表情包 |
| `furry` | `/setu uapipro furry` | 福瑞 |

子分类：

| 主分类 | 示例 | 说明 |
| --- | --- | --- |
| acg | `/setu uapipro acg+pc` | 二次元电脑壁纸 |
| acg | `/setu uapipro acg+mb` | 二次元手机壁纸 |
| bq | `/setu uapipro bq+xiongmao` | 熊猫表情 |
| bq | `/setu uapipro bq+waiguoren` | 歪果仁表情 |
| bq | `/setu uapipro bq+maomao` | 猫猫表情 |
| bq | `/setu uapipro bq+ikun` | ikun |
| bq | `/setu uapipro bq+eciyuan` | 二次元表情 |
| furry | `/setu uapipro furry+z4k` | 画质 Z |
| furry | `/setu uapipro furry+szs8k` | 画质 S |
| furry | `/setu uapipro furry+s4k` | 画质 S+ |
| furry | `/setu uapipro furry+4k` | 画质 4K |

</details>

<details>
<summary><b>LoliAPI loliapi</b></summary>

```
/setu loliapi <分类>
```

| 分类 | 说明 |
| --- | --- |
| `acg` | 二次元自适应 |
| `bg` | 背景墙纸 |
| `acg/pc` | 电脑壁纸 |
| `acg/pe` | 手机壁纸 |
| `acg/pp` | 二次元头像 |

</details>

<details>
<summary><b>imgapi</b></summary>

```
/setu imgapi <分类>
```

| 分类 | 说明 |
| --- | --- |
| `meizi` | 美女 |
| `dongman` | 动漫 |
| `fengjing` | 风景 |
| `suiji` | 随机 |

</details>

<details>
<summary><b>Bing</b></summary>

```
/setu bing
```

每日更新的高清风景，无需分类。

</details>

<details>
<summary><b>dmoe</b></summary>

```
/setu dmoe
```

二次元小站直出图，无需分类。

</details>

> 分类太多记不清？使用 `/setu help` 看海报**或**前往[图源全表](https://setu.youzix.top/)快捷复制指令

## 图源 API 相关地址

| 图源 | API |
| --- | --- |
| Lolicon | [docs.api.lolicon.app](https://docs.api.lolicon.app/) |
| 栗次元 | [t.alcy.cc](https://t.alcy.cc/) |
| UApiPro | [uapis.cn](https://uapis.cn/) |
| LoliAPI | [docs.loliapi.com](https://docs.loliapi.com/) |
| imgapi | [imgapi.cn](https://imgapi.cn/) |
| Bing | [bing.com](https://www.bing.com/) |
| dmoe | [dmoe.cc](https://www.dmoe.cc/) |

## 🙏 致谢

感谢以上 **图源 API 提供方**免费开放接口：

- Lolicon API · 栗次元 alcy · UApiPro · LoliAPI · imgapi · Bing · dmoe

> 若图源 API 有变动或无法访问
> 欢迎在 [GitHub](https://github.com/Youzix-Star/astrbot_plugin_nbsoutu_webui) 提 issue **或**在本文章下方评论反馈