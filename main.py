import json
import aiohttp
import logging
import tempfile
import os
import base64
import random
from datetime import datetime
from pathlib import Path
from astrbot.api.all import *
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.web import request, json_response, error_response

logger = logging.getLogger(__name__)

# 配置文件日志
_log_dir = Path(__file__).parent / "logs"
_log_dir.mkdir(exist_ok=True)
_file_handler = logging.FileHandler(_log_dir / "setu.log", encoding="utf-8")
_file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
logger.addHandler(_file_handler)
logger.setLevel(logging.INFO)

NAPCAT_HTTP = "http://127.0.0.1:3000"
NAPCAT_TOKEN = "awa"
PLUGIN_NAME = "astrbot_plugin_setu_webui"

@register(PLUGIN_NAME, "Youzix-Star & DeepSeek", "随机图片", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.llm_call_logs = []
        context.register_web_api(f"/{PLUGIN_NAME}/fetch", self.handle_fetch, ["POST"], "获取图片")
        context.register_web_api(f"/{PLUGIN_NAME}/groups", self.handle_groups, ["GET"], "群列表")
        context.register_web_api(f"/{PLUGIN_NAME}/send", self.handle_send, ["POST"], "发送图片")
        context.register_web_api(f"/{PLUGIN_NAME}/save_config", self.handle_save_config, ["POST"], "保存配置")
        context.register_web_api(f"/{PLUGIN_NAME}/get_config", self.handle_get_config, ["GET"], "获取配置")
        context.register_web_api(f"/{PLUGIN_NAME}/delete_config", self.handle_delete_config, ["POST"], "删除配置")
        context.register_web_api(f"/{PLUGIN_NAME}/list_configs", self.handle_list_configs, ["GET"], "列出配置")
        context.register_web_api(f"/{PLUGIN_NAME}/save_command", self.handle_save_command, ["POST"], "保存指令")
        context.register_web_api(f"/{PLUGIN_NAME}/get_command", self.handle_get_command, ["GET"], "获取指令")
        context.register_web_api(f"/{PLUGIN_NAME}/delete_command", self.handle_delete_command, ["POST"], "删除指令")
        context.register_web_api(f"/{PLUGIN_NAME}/list_commands", self.handle_list_commands, ["GET"], "列出指令")
        context.register_web_api(f"/{PLUGIN_NAME}/llm_logs", self.handle_llm_logs, ["GET"], "获取LLM调用记录")
        context.register_web_api(f"/{PLUGIN_NAME}/llm_log_detail", self.handle_llm_log_detail, ["GET"], "获取LLM调用详情")

    def _get_client(self):
        for platform in self.context.platform_manager.platform_insts:
            meta = platform.meta()
            if meta.name.lower() != "aiocqhttp":
                continue
            try:
                return platform.get_client()
            except Exception:
                continue
        return None

    def _config_dir(self):
        d = Path(__file__).parent / "configs"
        d.mkdir(exist_ok=True)
        return d

    def _commands_path(self):
        return Path(__file__).parent / "commands.json"

    def _load_commands(self):
        path = self._commands_path()
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save_commands(self, commands):
        with open(self._commands_path(), "w", encoding="utf-8") as f:
            json.dump(commands, f, ensure_ascii=False, indent=2)

    # ─── 调用记录辅助 ──────────────────────────

    def _append_log(self, entry):
        self.llm_call_logs.insert(0, entry)
        if len(self.llm_call_logs) > 100:
            self.llm_call_logs = self.llm_call_logs[:100]

    def _log_tag(self, body):
        tag = body.get("tag", "") if isinstance(body, dict) else ""
        if isinstance(tag, list):
            return ",".join(str(t) for t in tag)
        return str(tag or "")

    def _log_image_summary(self, images):
        out = []
        for img in images or []:
            if not isinstance(img, dict):
                continue
            url = img.get("source_url", "") or img.get("url", "")
            if url and not url.startswith("http"):
                url = "(本地临时文件)"
            out.append({
                "url": url,
                "title": img.get("title", ""),
                "author": img.get("author", ""),
                "pid": img.get("pid", ""),
            })
        return out

    def _describe_api(self, source, body):
        p = body or {}
        if source == "lolicon":
            payload = {}
            payload["r18"] = p.get("r18", 0)
            payload["num"] = p.get("num", 1)
            if p.get("tag"):
                payload["tag"] = p["tag"]
            if p.get("size"):
                payload["size"] = p["size"]
            if p.get("keyword"):
                payload["keyword"] = p["keyword"]
            if p.get("aspectRatio"):
                payload["aspectRatio"] = p["aspectRatio"]
            return "POST https://api.lolicon.app/setu/v2\n" + json.dumps(payload, ensure_ascii=False, indent=2)
        if source == "uapipro":
            qs = f"category={p.get('uapiCategory', 'acg')}"
            if p.get("uapiType"):
                qs += f"&type={p['uapiType']}"
            return f"GET https://uapis.cn/api/v1/random/image?{qs}"
        if source == "bing":
            if p.get("bingSource") == "official":
                return "GET https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=zh-CN"
            return "GET https://uapis.cn/api/v1/image/bing-daily?format=json&resolution=1080"
        if source == "imgapi":
            return f"GET https://imgapi.cn/api.php?zd={p.get('imgapiZd', '')}&fl={p.get('imgapiFl', '')}&gs=json"
        if source == "dmoe":
            return "GET https://www.dmoe.cc/random.php"
        if source == "loliapi":
            cat = p.get("loliapiCategory") or "acg"
            if cat == "random":
                cat = "acg"
            return f"GET https://www.loliapi.com/{cat}/"
        if source == "alcy":
            cat = p.get("alcyCategory") or "ycy"
            if cat == "random":
                cat = "ycy"
            return f"GET https://t.alcy.cc/json?{cat}=1"
        return source

    # ─── 全随机辅助 ──────────────────────────

    def _random_config(self):
        """全随机：把所有图源×子分类拍平成结果池，等概率抽一个（50 选 1）"""
        alcy_cats = ["ycy", "moez", "ai", "ysz", "pc", "moe", "fj", "bd", "ys",
                     "acg", "mp", "moemp", "ysmp", "aimp", "fjmp", "tx", "lai", "xhl"]
        loliapi_cats = ["acg", "bg", "acg/pc", "acg/pe", "acg/pp"]
        imgapi_cats = ["meizi", "dongman", "fengjing", "suiji"]
        uapi_main = ["acg", "landscape", "anime", "pc_wallpaper", "mobile_wallpaper",
                     "general_anime", "ai_drawing", "bq", "furry"]
        uapi_sub = {
            "acg": ["pc", "mb"],
            "bq": ["xiongmao", "waiguoren", "maomao", "ikun", "eciyuan"],
            "furry": ["z4k", "szs8k", "s4k", "4k"],
        }

        # 构建等概率叶子池：(图源, 额外参数)
        leaves = []
        leaves.append(("lolicon", {}))
        leaves.append(("bing", {}))
        leaves.append(("dmoe", {}))
        for c in alcy_cats:
            leaves.append(("alcy", {"alcyCategory": c}))
        for c in loliapi_cats:
            leaves.append(("loliapi", {"loliapiCategory": c}))
        for c in imgapi_cats:
            leaves.append(("imgapi", {"imgapiFl": c}))
        for main in uapi_main:
            leaves.append(("uapipro", {"uapiCategory": main}))
            for sub in uapi_sub.get(main, []):
                leaves.append(("uapipro", {"uapiCategory": main, "uapiType": sub}))

        source, extra = random.choice(leaves)
        body = {"source": source, "num": 1, "r18": 0, **extra}
        return source, body

    def _cmd_for(self, source, body):
        """根据图源与参数生成真实可用的指令字符串"""
        body = body or {}
        if source == "alcy":
            return f"/setu alcy {body.get('alcyCategory', 'ycy')}"
        if source == "loliapi":
            return f"/setu loliapi {body.get('loliapiCategory', 'acg')}"
        if source == "uapipro":
            main = body.get("uapiCategory", "acg")
            sub = body.get("uapiType", "")
            return f"/setu uapipro {main}" + (f"+{sub}" if sub else "")
        if source == "imgapi":
            return f"/setu imgapi {body.get('imgapiFl', 'suiji')}"
        if source == "bing":
            return "/setu bing"
        if source == "dmoe":
            return "/setu dmoe"
        tags = body.get("tag") or []
        return "/setu " + ",".join(tags) if tags else "/setu"

    async def napcat(self, action, data=None):
        headers = {"Content-Type": "application/json"}
        if NAPCAT_TOKEN:
            headers["Authorization"] = f"Bearer {NAPCAT_TOKEN}"
        async with aiohttp.ClientSession() as s:
            async with s.post(f"{NAPCAT_HTTP}/{action}", json=data or {}, headers=headers, timeout=15) as r:
                return await r.json()

    async def handle_groups(self):
        try:
            r = await self.napcat("get_group_list")
            out = []
            for g in r.get("data", []):
                out.append({"id": g["group_id"], "name": g.get("group_name", ""), "count": g.get("member_count", 0)})
            return json_response({"groups": out})
        except Exception as e:
            return error_response(str(e), 500)

    async def handle_fetch(self):
        try:
            body = await request.json(default={})
        except Exception:
            body = {}
        source = body.get("source", "lolicon")
        num = int(body.get("num", 5))
        if num < 1: num = 1
        if num > 20: num = 20
        random_mode = bool(body.get("random"))
        logger.info(f"[handle_fetch] source={source}, num={num}, random={random_mode}, body={json.dumps(body, ensure_ascii=False)}")
        try:
            if random_mode:
                # 全随机：每一张独立抽取图源+分类，各自带自己的指令/图源/API，并逐张写入调用记录
                data = []
                pending = []
                for _ in range(num):
                    src, rbody = self._random_config()
                    rbody["num"] = 1
                    try:
                        one = await self._fetch(src, rbody)
                        if one:
                            one[0]["command"] = self._cmd_for(src, rbody)
                            one[0]["source"] = src
                            one[0]["api"] = self._describe_api(src, rbody)
                            data.append(one[0])
                            pending.append((one[0], {
                                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "user": "WebUI",
                                "group": "-",
                                "source": src,
                                "tag": one[0]["command"],
                                "prompt": json.dumps(body, ensure_ascii=False),
                                "result": "成功",
                                "detail": "1 张",
                                "api": self._describe_api(src, rbody),
                                "raw": json.dumps(self._log_image_summary(one), ensure_ascii=False, indent=2),
                            }))
                    except Exception as e:
                        logger.warning(f"[random] draw failed: {e}")
                        continue
                n = len(pending)
                for i, (img, entry) in enumerate(pending):
                    self._append_log(entry)
                    img["log_index"] = n - 1 - i   # 后插入的条目会把前面的往下推
                return json_response({"images": data})

            # 普通模式：同一图源取 num 张，共用一条指令
            data = await self._fetch(source, body)
            logger.info(f"[handle_fetch] result count={len(data)}")
            cmd_str = self._cmd_for(source, body)
            for img in data:
                img["command"] = cmd_str
                img["source"] = source
                img["api"] = self._describe_api(source, body)
            self._append_log({
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user": "WebUI",
                "group": "-",
                "source": source,
                "tag": cmd_str,
                "prompt": json.dumps(body, ensure_ascii=False),
                "result": "成功" if data else "失败",
                "detail": f"{len(data)} 张" if data else "没有找到图片",
                "api": self._describe_api(source, body),
                "raw": json.dumps(self._log_image_summary(data), ensure_ascii=False, indent=2),
            })
            for img in data:
                img["log_index"] = 0
            return json_response({"images": data})
        except Exception as e:
            logger.error(f"[handle_fetch] failed: {e}", exc_info=True)
            self._append_log({
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user": "WebUI",
                "group": "-",
                "source": source,
                "tag": self._cmd_for(source, body) if not random_mode else "全随机",
                "prompt": json.dumps(body, ensure_ascii=False),
                "result": "失败",
                "detail": str(e),
                "api": self._describe_api(source, body),
                "raw": "[]",
            })
            return error_response(str(e), 500)

    async def fetch_lolicon(self, body):
        num = min(int(body.get("num", 5)), 20)
        params = {"r18": int(body.get("r18", 0)), "num": num, "size": body.get("size", ["original"])}
        tag = body.get("tag", [])
        if tag and isinstance(tag, list): params["tag"] = tag
        keyword = body.get("keyword", "")
        if keyword: params["keyword"] = keyword
        uid = body.get("uid")
        if uid: params["uid"] = uid
        proxy = body.get("proxy", "")
        if proxy: params["proxy"] = proxy
        ar = body.get("aspectRatio", "")
        if ar: params["aspectRatio"] = ar
        if body.get("excludeAI"): params["excludeAI"] = True
        if body.get("dsc"): params["dsc"] = True
        async with aiohttp.ClientSession() as s:
            async with s.post("https://api.lolicon.app/setu/v2", json=params, timeout=15) as r:
                data = await r.json()
                items = data.get("data", [])
                out = []
                for item in items:
                    urls = item.get("urls", {})
                    img_url = urls.get("original", "") or urls.get("regular", "") or urls.get("small", "") or urls.get("thumb", "") or urls.get("mini", "")
                    out.append({
                        "url": img_url,
                        "thumb": urls.get("thumb") or urls.get("small") or urls.get("regular") or img_url,
                        "title": item.get("title", ""),
                        "author": item.get("author", ""),
                        "pid": item.get("pid", "")
                    })
                return out

    async def fetch_uapi(self, body):
        category = body.get("uapiCategory", "acg")
        img_type = body.get("uapiType", "")
        num = min(int(body.get("num", 5)), 10)
        out = []
        for i in range(num):
            try:
                ts = int(__import__("time").time() * 1000)
                url = f"https://uapis.cn/api/v1/random/image?category={category}&_={ts}"
                if img_type: url += f"&type={img_type}"
                async with aiohttp.ClientSession() as s:
                    async with s.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                        ct = resp.headers.get("Content-Type", "")
                        img_data = await resp.read()
                        final_url = str(resp.url)
                suffix = ".jpg"
                if "png" in ct: suffix = ".png"
                elif "gif" in ct: suffix = ".gif"
                elif "webp" in ct: suffix = ".webp"
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                tmp.write(img_data); tmp.close()
                b64 = base64.b64encode(img_data).decode("ascii")
                out.append({"url": tmp.name, "source_url": final_url, "thumb": f"data:{ct};base64,{b64}", "title": f"UApiPro {category}", "author": img_type or category, "pid": f"uapi_{i}"})
            except Exception as e:
                logger.warning(f"[uapi] fetch failed[{i}]: {e}")
                continue
        return out

    async def fetch_bing(self, body):
        num = min(int(body.get("num", 5)), 8)
        bing_source = body.get("bingSource", "uapi")
        out = []
        if bing_source == "official":
            for i in range(num):
                try:
                    url = f"https://www.bing.com/HPImageArchive.aspx?format=js&idx={i}&n=1&mkt=zh-CN"
                    async with aiohttp.ClientSession() as s:
                        async with s.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                            data = await resp.json()
                    images = data.get("images", [])
                    if images:
                        img = images[0]
                        img_url = f"https://www.bing.com{img['url']}"
                        out.append({"url": img_url, "thumb": img_url.replace("1920x1080", "640x480"), "title": img.get("title", "Bing 壁纸"), "author": img.get("copyright", ""), "pid": f"bing_official_{img.get('startdate', i)}"})
                except Exception as e:
                    logger.warning(f"[bing] official fetch failed[{i}]: {e}")
                    continue
        else:
            for i in range(num):
                try:
                    rp = "&random=true" if num > 1 else ""
                    url = f"https://uapis.cn/api/v1/image/bing-daily?format=json&resolution=1080{rp}"
                    async with aiohttp.ClientSession() as s:
                        async with s.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                            data = await resp.json()
                    img_url = data.get("image_url") or data.get("image_url_4k") or data.get("image_url_1080") or ""
                    if img_url:
                        out.append({"url": img_url, "thumb": data.get("image_url_1080") or img_url, "title": data.get("title", "Bing 壁纸"), "author": data.get("copyright", ""), "pid": f"bing_{data.get('date', i)}"})
                except Exception as e:
                    logger.warning(f"[bing] uapi fetch failed[{i}]: {e}")
                    continue
        return out

    async def fetch_imgapi(self, body):
        zd = body.get("imgapiZd", "")
        fl = body.get("imgapiFl", "")
        num = min(int(body.get("num", 5)), 10)
        out = []
        for i in range(num):
            try:
                ts = int(__import__("time").time() * 1000)
                url = f"https://imgapi.cn/api.php?zd={zd}&fl={fl}&gs=json"
                async with aiohttp.ClientSession() as s:
                    async with s.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                        data = await resp.json(content_type=None)
                img_url = data.get("imgurl", "") or data.get("img", "") or data.get("url", "")
                if img_url:
                    async with aiohttp.ClientSession() as s:
                        async with s.get(img_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                            img_data = await resp.read()
                            ct = resp.headers.get("Content-Type", "image/jpeg")
                    suffix = ".jpg"
                    if "png" in ct: suffix = ".png"
                    elif "gif" in ct: suffix = ".gif"
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                    tmp.write(img_data); tmp.close()
                    b64 = base64.b64encode(img_data).decode("ascii")
                    out.append({"url": tmp.name, "source_url": img_url, "thumb": f"data:{ct};base64,{b64}", "title": f"imgapi {fl or '壁纸'}", "author": f"{data.get('width', '?')}x{data.get('height', '?')}", "pid": f"imgapi_{i}"})
            except Exception as e:
                logger.warning(f"[imgapi] fetch failed[{i}]: {e}")
                continue
        return out

    async def fetch_dmoe(self, body):
        num = min(int(body.get("num", 5)), 10)
        out = []
        for i in range(num):
            try:
                ts = int(__import__("time").time() * 1000)
                url = f"https://www.dmoe.cc/random.php?t={ts}"
                async with aiohttp.ClientSession() as s:
                    async with s.get(url, timeout=30, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                        img_data = await resp.read()
                        ct = resp.headers.get("Content-Type", "image/jpeg")
                        final_url = str(resp.url)
                suffix = ".jpg"
                if "png" in ct: suffix = ".png"
                elif "gif" in ct: suffix = ".gif"
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                tmp.write(img_data); tmp.close()
                b64 = base64.b64encode(img_data).decode("ascii")
                out.append({"url": tmp.name, "source_url": final_url, "thumb": f"data:{ct};base64,{b64}", "title": "dmoe 二次元", "author": "dmoe.cc", "pid": f"dmoe_{i}"})
            except Exception as e:
                logger.warning(f"[dmoe] fetch failed[{i}]: {e}")
                continue
        return out

    async def fetch_loliapi(self, body):
        category = body.get("loliapiCategory", "random")
        num = min(int(body.get("num", 5)), 10)
        all_cats = ["acg", "bg", "acg/pc", "acg/pe", "acg/pp"]
        out = []
        for i in range(num):
            try:
                if category == "random": cat = random.choice(all_cats)
                else: cat = category
                ts = int(__import__("time").time() * 1000)
                url = f"https://www.loliapi.com/{cat}/?_={ts}"
                async with aiohttp.ClientSession() as s:
                    async with s.get(url, timeout=30, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                        img_data = await resp.read()
                        ct = resp.headers.get("Content-Type", "image/jpeg")
                        final_url = str(resp.url)
                suffix = ".jpg"
                if "png" in ct: suffix = ".png"
                elif "gif" in ct: suffix = ".gif"
                elif "webp" in ct: suffix = ".webp"
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                tmp.write(img_data); tmp.close()
                b64 = base64.b64encode(img_data).decode("ascii")
                out.append({"url": tmp.name, "source_url": final_url, "thumb": f"data:{ct};base64,{b64}", "title": f"LoliAPI {cat}", "author": "loliapi.com", "pid": f"loliapi_{i}"})
            except Exception as e:
                logger.warning(f"[loliapi] fetch failed[{i}]: {e}")
                continue
        return out

    async def fetch_alcy(self, body):
        category = body.get("alcyCategory", "random")
        compress = body.get("alcyCompress", "800")
        num = min(int(body.get("num", 5)), 10)
        all_cats = ["ycy", "moez", "ai", "ysz", "pc", "moe", "fj", "bd", "ys", "acg", "mp", "moemp", "ysmp", "aimp", "fjmp", "tx", "lai", "xhl"]
        out = []
        for i in range(num):
            try:
                if category == "random": cat = random.choice(all_cats)
                else: cat = category
                url = f"https://t.alcy.cc/json?{cat}=1"
                async with aiohttp.ClientSession() as s:
                    async with s.get(url, timeout=60) as resp:
                        data = await resp.json(content_type=None)
                item = data.get("data", {})
                link = item.get("link", "")
                if link:
                    async with aiohttp.ClientSession() as s:
                        async with s.get(link, timeout=60, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://t.alcy.cc/"}) as resp:
                            img_data = await resp.read()
                    if compress != "none":
                        img_data = self._compress_image(img_data, int(compress))
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                    tmp.write(img_data); tmp.close()
                    b64 = base64.b64encode(img_data).decode("ascii")
                    out.append({"url": tmp.name, "source_url": link, "thumb": f"data:image/jpeg;base64,{b64}", "title": f"栗次元 {cat}", "author": "alcy.cc", "pid": f"alcy_{item.get('id', i)}"})
            except Exception as e:
                logger.warning(f"[alcy] fetch failed[{i}]: {e}")
                continue
        return out

    def _compress_image(self, img_data, max_width=800, quality=80):
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(img_data))
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.LANCZOS)
            output = io.BytesIO()
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            img.save(output, format='JPEG', quality=quality)
            return output.getvalue()
        except Exception as e:
            logger.warning(f"[compress] failed: {e}")
            return img_data

    # ══════════════════════════════════════════
    #  帮助海报（HTML 渲染 + Pillow 兜底）
    # ══════════════════════════════════════════

    def _build_help_poster_html(self) -> str:
        """读取 help_template.html 模板并填充动态内容（杂志风 · 无图标 · 附实用命令）"""
        import html as html_mod

        config_dir = self._config_dir()
        names = sorted(p.stem for p in config_dir.glob("*.json")) if config_dir.exists() else []
        cmds = self._load_commands()

        def esc(s):
            return html_mod.escape(str(s))

        def card(index, title, inner):
            return (
                '<div class="card">'
                f'<div class="card-head"><span class="sec-num">{index:02d}</span>'
                f'<span class="card-title">{esc(title)}</span></div>'
                f'<div class="card-body">{inner}</div>'
                "</div>"
            )

        cards_html = ""

        # 01 说人话
        nl_inner = (
            '<div class="msg-bubble">'
            "懒得记指令？直接说人话——<b>「来张原神的图」</b>"
            "<b>「想看风景」</b><b>「来只小狐狸」</b>，"
            "<br>AI 自己会去搞定，你负责躺着欣赏就行。"
            "</div>"
        )
        cards_html += card(1, "说人话", nl_inner)

        # 02 基本指令
        cmd_rows = ""
        for cmd, desc in [
            ("/setu", "随机来一张（默认 Lolicon）"),
            ("/setu random", "全随机：50 种图源×分类等概率抽取，玩的就是心跳"),
            ("/setu 关键词", "按标签搜，如 /setu 百合"),
            ("/setu list", "查看已保存的配置与指令"),
            ("/setu help", "召唤这本指南"),
        ]:
            cmd_rows += (
                f'<div class="cmd-row"><code>{esc(cmd)}</code>'
                f'<span class="cmd-desc">{esc(desc)}</span></div>'
            )
        cards_html += card(2, "基本指令", cmd_rows)

        # 03 图源 · 用法（分类树形图）
        cards_html += card(3, "图源 · 用法", f'<div class="src-grid">{self._build_source_rows()}</div>')

        # 04 网页面板
        web_rows = ""
        for name, desc in [
            ("快速获取", "网页上点几下就能取图，还能勾选群一键发送"),
            ("积木编程", "把常用设置存成积木，组合成指令，一句话召唤整套图"),
            ("调用记录", "查看 AI 帮你取过什么图，详情可一键复制"),
        ]:
            web_rows += (
                f'<div class="cmd-row"><span class="cmd-name">{esc(name)}</span>'
                f'<span class="cmd-desc">{esc(desc)}</span></div>'
            )
        cards_html += card(4, "网页面板", web_rows)

        if names:
            cards_html += card(5, "已保存配置", '<div class="plain">' + esc("    ".join(names)) + "</div>")
        if cmds:
            cmd_list = "".join(
                f'<div class="plain">· {esc(c["name"])}'
                f'（{"随机" if c.get("mode") == "random" else "分条" if c.get("mode") == "all" else "合并"}'
                f' {len(c.get("presets", []))}步）</div>'
                for c in cmds
            )
            cards_html += card(6, "已保存指令", cmd_list)

        template_path = Path(__file__).parent / "help_template.html"
        if template_path.exists():
            template = template_path.read_text(encoding="utf-8")
            return template.replace("<!--SECTIONS-->", cards_html)

        return (
            "<html><body style='width:100%;font-family:sans-serif;padding:20px;'>"
            + cards_html
            + "</body></html>"
        )

    def _build_source_rows(self) -> str:
        """生成「图源 · 用法」：每个图源 = 中文名 + 代码 + 真实命令 + 分类树形图"""
        import html as html_mod
        esc = html_mod.escape

        def chip(code, desc):
            if code:
                return (
                    f'<span class="src-cat"><span class="src-cat-code">{esc(code)}</span>'
                    f"<span>{esc(desc)}</span></span>"
                )
            return f'<span class="src-cat note"><span>{esc(desc)}</span></span>'

        def tree_block(groups):
            html = '<div class="tree">'
            for cat, items in groups:
                tags = "".join(chip(c, d) for c, d in items)
                html += (
                    f'<div class="tree-row">'
                    f'<span class="tree-cat">{esc(cat)}</span>'
                    f'<div class="tree-tags">{tags}</div>'
                    f"</div>"
                )
            html += "</div>"
            return html

        def block(name, code, example, groups):
            return (
                '<div class="src-item">'
                f'<div class="src-head">'
                f'<span class="src-name">{esc(name)}</span>'
                f'<span class="src-code">{esc(code)}</span>'
                f'<code class="src-example">{esc(example)}</code>'
                f"</div>"
                f'{tree_block(groups)}'
                "</div>"
            )

        rows = ""
        rows += block("Lolicon", "lolicon", "/setu 关键词", [
            ("使用", [("", "默认图源。直接 /setu 随机来一张；带关键词按角色/标签搜，如「原神」「泳装」")]),
        ])
        rows += block("栗次元", "alcy", "/setu alcy ycy", [
            ("自适应", [("ycy", "二次元"), ("moez", "萌版"), ("ai", "AI图"), ("ysz", "原神")]),
            ("横图", [("pc", "横版"), ("moe", "萌版横图"), ("fj", "风景"), ("bd", "白底"), ("ys", "原神横图")]),
            ("竖图", [("mp", "竖版"), ("moemp", "萌版竖图"), ("ysmp", "原神竖图"), ("aimp", "AI竖图"), ("fjmp", "风景竖图")]),
            ("其它", [("acg", "动图"), ("tx", "头像"), ("lai", "七濑胡桃"), ("xhl", "小狐狸")]),
        ])
        rows += block("UApiPro", "uapipro", "/setu uapipro acg", [
            ("主分类", [("acg", "二次元"), ("landscape", "风景"), ("anime", "动漫混合"), ("pc_wallpaper", "电脑壁纸"), ("mobile_wallpaper", "手机壁纸"), ("general_anime", "动漫图"), ("ai_drawing", "AI绘画"), ("bq", "表情包"), ("furry", "福瑞")]),
            ("acg 子类", [("acg+pc", "电脑壁纸"), ("acg+mb", "手机壁纸")]),
            ("bq 子类", [("bq+xiongmao", "熊猫"), ("bq+waiguoren", "歪果仁"), ("bq+maomao", "猫猫"), ("bq+ikun", "ikun"), ("bq+eciyuan", "二次元")]),
            ("furry 子类", [("furry+z4k", "画质Z"), ("furry+szs8k", "画质S"), ("furry+s4k", "画质S+"), ("furry+4k", "画质4K")]),
        ])
        rows += block("LoliAPI", "loliapi", "/setu loliapi acg", [
            ("分类", [("acg", "二次元自适应"), ("bg", "背景墙纸"), ("acg/pc", "电脑壁纸"), ("acg/pe", "手机壁纸"), ("acg/pp", "二次元头像")]),
        ])
        rows += block("imgapi", "imgapi", "/setu imgapi meizi", [
            ("分类", [("meizi", "美女"), ("dongman", "动漫"), ("fengjing", "风景"), ("suiji", "随机")]),
        ])
        rows += block("Bing 壁纸", "bing", "/setu bing", [
            ("使用", [("", "每日更新的高清风景摄影，无需分类")]),
        ])
        rows += block("dmoe 二次元", "dmoe", "/setu dmoe", [
            ("使用", [("", "二次元小站直出图，无需分类")]),
        ])
        return rows

    async def _render_help_poster(self) -> str:
        """渲染帮助海报为图片，返回本地文件路径。优先用 AstrBot 内置 html_render，失败回退 Pillow。"""
        html_content = self._build_help_poster_html()
        html_render = getattr(self, "html_render", None)
        if html_render is not None:
            # 渲染参数对齐「群日常分析」插件：全页截图 + ultra 高倍率(1.8x)保证清晰
            image_options = {
                "full_page": True,
                "type": "png",
                "device_scale_factor_level": "ultra",
                "timeout": 60000,
            }
            try:
                image_data = await html_render(html_content, {}, False, image_options)
                if isinstance(image_data, bytes) and image_data.startswith(b"\x89PNG"):
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                    tmp.write(image_data)
                    tmp.close()
                    return tmp.name
                if isinstance(image_data, str) and os.path.exists(image_data):
                    return image_data
                logger.warning("[help] html_render 返回数据无效，回退 Pillow 绘制")
            except Exception as e:
                logger.warning(f"[help] html_render 失败，回退 Pillow 绘制: {e}")
        return self._render_help_poster_pillow()

    # ─── 帮助海报 · Pillow 兜底版 ──────────────────────────

    def _find_cjk_font(self):
        candidates = [
            "/system/fonts/NotoSansCJK-Regular.ttc",
            "/system/fonts/NotoSansCJK-Bold.ttc",
            "/system/fonts/DroidSansFallback.ttf",
            "/system/fonts/SourceHanSansCN-Regular.otf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "/System/Library/Fonts/PingFang.ttc",
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return None

    def _wrap(self, text, font, max_width):
        lines = []
        for raw in str(text).split("\n"):
            if raw == "":
                lines.append("")
                continue
            cur = ""
            for ch in raw:
                if font.getlength(cur + ch) > max_width:
                    lines.append(cur.rstrip())
                    cur = ch
                else:
                    cur += ch
            lines.append(cur.rstrip())
        return lines

    def _render_help_poster_pillow(self) -> str:
        from PIL import Image, ImageDraw, ImageFont

        font_path = self._find_cjk_font()

        def F(size):
            if font_path:
                return ImageFont.truetype(font_path, size)
            return ImageFont.load_default()

        config_dir = self._config_dir()
        names = sorted(p.stem for p in config_dir.glob("*.json")) if config_dir.exists() else []
        cmds = self._load_commands()

        sections = [
            ("说人话", [
                "懒得记指令？直接说人话「来张原神的图」「想看风景」",
                "AI 自己会去搞定，你负责躺着欣赏就行",
            ]),
            ("基本指令", [
                "/setu             随机来一张（默认 Lolicon）",
                "/setu random      全随机：50 种图源×分类等概率",
                "/setu 关键词       按标签搜，如 /setu 百合",
                "/setu list        查看已保存的配置与指令",
                "/setu help        召唤这本指南",
            ]),
            ("图源", [
                "Lolicon(默认)  /setu 或 /setu 关键词",
                "栗次元(alcy)   /setu alcy ycy / xhl(小狐狸) / ysz(原神) ...",
                "UApiPro(uapipro) /setu uapipro acg / landscape(风景) ...",
                "LoliAPI(loliapi) /setu loliapi acg / bg(墙纸) ...",
                "imgapi        /setu imgapi meizi(美女) / dongman(动漫) ...",
                "Bing(bing)     /setu bing（每日风景）",
                "dmoe(dmoe)     /setu dmoe（二次元）",
            ]),
            ("网页面板", [
                "快速获取   网页上点几下就能取图，还能勾选群一键发送",
                "积木编程   把常用设置存成积木，组合成指令，一句话召唤整套图",
                "调用记录   查看 AI 帮你取过什么图，详情可一键复制",
            ]),
        ]
        if names:
            sections.append(("已保存配置", ["   " + "    ".join(names)]))
        if cmds:
            sections.append(("已保存指令", [f"  {c['name']}（{'随机' if c['mode']=='random' else '分条' if c['mode']=='all' else '合并'} {len(c['presets'])}步）" for c in cmds]))

        W = 860
        PAD = 48
        title_font = F(46)
        sub_font = F(24)
        sec_font = F(28)
        body_font = F(24)
        foot_font = F(22)
        banner_h = 170
        footer_h = 90
        line_h = 38

        content_h = 0
        for title, lines in sections:
            content_h += sec_font.size + 22 + 14
            for line in lines:
                content_h += len(self._wrap(line, body_font, W - PAD * 2 - 24)) * line_h + 6
        total_h = banner_h + PAD + content_h + PAD + footer_h

        img = Image.new("RGB", (W, total_h), "#faf7f2")
        draw = ImageDraw.Draw(img)

        draw.rectangle([0, 0, W, banner_h], fill="#161616")
        t_title = "云笺寻图 · 使用指南"
        tw = draw.textlength(t_title, font=title_font)
        draw.text(((W - tw) / 2, 42), t_title, font=title_font, fill="#faf7f2")
        t_sub = "不用记指令，直接说人话，图自己会来"
        sw = draw.textlength(t_sub, font=sub_font)
        draw.text(((W - sw) / 2, 108), t_sub, font=sub_font, fill="#ff4d2e")

        y = banner_h + PAD
        content_w = W - PAD * 2
        for idx, (title, lines) in enumerate(sections, 1):
            draw.text((PAD, y), f"{idx:02d}", font=sec_font, fill="#ff4d2e")
            draw.text((PAD + 60, y), title, font=sec_font, fill="#161616")
            y += sec_font.size + 22
            for line in lines:
                wrapped = self._wrap(line, body_font, content_w - 26)
                for wline in wrapped:
                    draw.text((PAD + 26, y), wline, font=body_font, fill="#33302b")
                    y += line_h
                y += 8
            y += 14

        draw.rectangle([0, total_h - footer_h, W, total_h], fill="#161616")
        t_ft = "云笺寻图 · 一键取图 · 祝玩得开心"
        fw = draw.textlength(t_ft, font=foot_font)
        draw.text(((W - fw) / 2, total_h - footer_h + 28), t_ft, font=foot_font, fill="#faf7f2")

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp.close()
        img.save(tmp.name)
        return tmp.name

    async def handle_send(self):
        try:
            body = await request.json(default={})
        except Exception:
            body = {}
        ids = body.get("group_ids", [])
        images = body.get("images", [])
        if not ids or not images:
            return error_response("no data", 400)
        client = self._get_client()
        if not client:
            return error_response("无法获取 aiocqhttp client", 500)
        ok = 0
        fail = 0
        for gid in ids:
            temp_files = []
            try:
                msg = []
                for idx, img in enumerate(images):
                    url = img.get("url", "")
                    if not url:
                        continue
                    if not url.startswith("http"):
                        msg.append({"type": "image", "data": {"file": f"file://{url}"}})
                    else:
                        try:
                            async with aiohttp.ClientSession() as s:
                                async with s.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": "https://www.pixiv.net/"}) as resp:
                                    img_data = await resp.read()
                            suffix = ".jpg"
                            if url.lower().endswith(".png"): suffix = ".png"
                            elif url.lower().endswith(".gif"): suffix = ".gif"
                            elif url.lower().endswith(".webp"): suffix = ".webp"
                            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                            tmp.write(img_data); tmp.close()
                            temp_files.append(tmp.name)
                            msg.append({"type": "image", "data": {"file": f"file://{tmp.name}"}})
                        except Exception as e:
                            logger.warning(f"[send] download failed for {url[:80]}: {e}")
                            msg.append({"type": "image", "data": {"file": url}})
                    t = img.get("title", ""); a = img.get("author", ""); p = img.get("pid", ""); cmd = img.get("command", "")
                    parts_txt = []
                    if t or a or p: parts_txt.append(f"{t} - {a} ({p})")
                    if cmd: parts_txt.append(f"📌 指令：{cmd}")
                    if parts_txt: msg.append({"type": "text", "data": {"text": "\n" + "\n".join(parts_txt)}})
                await client.api.call_action("send_group_msg", group_id=int(gid), message=msg)
                ok += 1
            except Exception as e:
                logger.warning(f"[send] send to {gid} failed: {e}")
                fail += 1
            finally:
                for fp in temp_files:
                    try: os.unlink(fp)
                    except: pass
        return json_response({"ok": ok, "fail": fail})

    async def _fetch(self, source, body):
        if source == "uapipro": return await self.fetch_uapi(body)
        elif source == "bing": return await self.fetch_bing(body)
        elif source == "imgapi": return await self.fetch_imgapi(body)
        elif source == "dmoe": return await self.fetch_dmoe(body)
        elif source == "loliapi": return await self.fetch_loliapi(body)
        elif source == "alcy": return await self.fetch_alcy(body)
        else: return await self.fetch_lolicon(body)

    async def _do_send_image(self, event, img, source_name="", command=""):
        url = img.get("url", "")
        if not url:
            await event.send("获取的图片 URL 为空，请重试")
            return
        title = img.get("title", "")
        author = img.get("author", "")
        if url.startswith("http"):
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.pixiv.net/"}) as resp:
                    img_data = await resp.read()
            suffix = ".jpg"
            if url.lower().endswith(".png"): suffix = ".png"
            elif url.lower().endswith(".gif"): suffix = ".gif"
            elif url.lower().endswith(".webp"): suffix = ".webp"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(img_data); tmp.close()
            file_path = tmp.name
        else:
            file_path = url
        text = f"📷 {title}" if title else "随机图片"
        if author: text += f"\n👤 {author}"
        if source_name: text += f"\n🔗 来源: {source_name}"
        if command: text += f"\n📌 指令：{command}"
        client = self._get_client()
        if client:
            try:
                await client.api.call_action("send_group_msg",
                    group_id=int(event.get_group_id()),
                    message=[{"type": "image", "data": {"file": f"file://{file_path}"}}, {"type": "text", "data": {"text": f"\n{text}"}}]
                )
            except Exception as e:
                logger.error(f"[do_send] send failed: {e}")
        if url.startswith("http"):
            try: os.unlink(file_path)
            except: pass

    # ─── 配置预设 ──────────────────────────

    async def handle_save_config(self):
        try:
            body = await request.json(default={})
        except Exception:
            body = {}
        name = body.get("name", "").strip()
        config = body.get("config", {})
        if not name: return error_response("name required", 400)
        with open(self._config_dir() / f"{name}.json", "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return json_response({"saved": True})

    async def handle_get_config(self):
        name = request.query.get("name", "")
        path = self._config_dir() / f"{name}.json"
        if not path.exists(): return error_response("not found", 404)
        with open(path, "r", encoding="utf-8") as f:
            return json_response({"config": json.load(f)})

    async def handle_delete_config(self):
        try:
            body = await request.json(default={})
        except Exception:
            body = {}
        name = body.get("name", "")
        path = self._config_dir() / f"{name}.json"
        if path.exists(): path.unlink()
        return json_response({"deleted": True})

    async def handle_list_configs(self):
        return json_response({"names": [p.stem for p in self._config_dir().glob("*.json")]})

    # ─── 指令管理 ──────────────────────────

    async def handle_save_command(self):
        try:
            body = await request.json(default={})
        except Exception:
            body = {}
        name = body.get("name", "").strip()
        presets = body.get("presets", [])
        mode = body.get("mode", "random")
        if not name or not presets: return error_response("name and presets required", 400)
        cmds = self._load_commands()
        found = False
        for c in cmds:
            if c["name"] == name:
                c["presets"] = presets; c["mode"] = mode; found = True; break
        if not found: cmds.append({"name": name, "presets": presets, "mode": mode})
        self._save_commands(cmds)
        return json_response({"saved": True})

    async def handle_get_command(self):
        name = request.query.get("name", "")
        for c in self._load_commands():
            if c["name"] == name: return json_response({"command": c})
        return error_response("not found", 404)

    async def handle_delete_command(self):
        try:
            body = await request.json(default={})
        except Exception:
            body = {}
        name = body.get("name", "")
        self._save_commands([c for c in self._load_commands() if c["name"] != name])
        return json_response({"deleted": True})

    async def handle_list_commands(self):
        return json_response({"commands": self._load_commands()})

    # ─── LLM 调用记录 ──────────────────────

    async def handle_llm_logs(self):
        page = int(request.query.get("page", 1))
        limit = int(request.query.get("limit", 20))
        start = (page - 1) * limit
        end = start + limit
        data = self.llm_call_logs[start:end] if start < len(self.llm_call_logs) else []
        return json_response({"logs": data, "total": len(self.llm_call_logs), "page": page, "limit": limit})

    async def handle_llm_log_detail(self):
        index = int(request.query.get("index", -1))
        if index < 0 or index >= len(self.llm_call_logs):
            return error_response("not found", 404)
        return json_response({"log": self.llm_call_logs[index]})

    # ─── LLM 工具 ──────────────────────────

    @filter.llm_tool(name="get_setu")
    async def tool_get_setu(self, event: AstrMessageEvent, source: str, tag: str) -> MessageEventResult:
        '''获取随机二次元/风景/美女图片并发送到群聊。

        Args:
            source(string): 图源。lolicon(Pixiv插画) / uapipro(多分类壁纸) / bing(风景壁纸) / imgapi(随机壁纸) / dmoe(二次元) / loliapi(多分类二次元) / alcy(栗次元多分类) / random(全随机：50种图源×分类等概率)
            tag(string): 搜索标签或分类。不同图源的可选值如下：

【random】全随机：从所有图源×分类结果池等概率抽取，tag 留空即可

【lolicon】标签名，多个用逗号分隔，如"原神,泳装"

【uapipro】主分类：
- acg=二次元 landscape=风景 anime=动漫混合 pc_wallpaper=电脑壁纸
- mobile_wallpaper=手机壁纸 general_anime=动漫图 ai_drawing=AI绘画
- bq=表情包 furry=福瑞
主分类为 acg 时可附加子分类：pc=PC端 mb=移动端
主分类为 bq 时可附加子分类：xiongmao=熊猫 waiguoren=歪果仁 maomao=猫猫 ikun eciyuan=二次元
主分类为 furry 时可附加子分类：z4k szs8k s4k 4k
子分类写法：主分类+子分类，如 acg+pc 表示二次元PC端壁纸

【bing】无需标签，留空即可

【imgapi】分类名：meizi=美女 dongman=动漫 fengjing=风景 suiji=随机

【loliapi】分类名：acg=二次元自适应 bg=背景墙纸 acg/pc=电脑壁纸 acg/pe=手机壁纸 acg/pp=二次元头像

【alcy/栗次元】
- ycy=二次元自适应 moez=萌版自适应 ai=AI自适应 ysz=原神自适应
- pc=PC横图 moe=萌版横图 fj=风景横图 bd=白底横图 ys=原神横图
- acg=ACG动图 mp=移动竖图 moemp=萌版竖图 ysmp=原神竖图
- aimp=AI竖图 fjmp=风景竖图 tx=头像方图 lai=七濑胡桃 xhl=小狐狸

【dmoe】无需标签，留空即可
        '''
        yield event.plain_result("正在获取图片，请稍候...")
        prompt = event.message_str
        log_entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": str(event.get_sender_id()),
            "group": str(event.get_group_id()),
            "source": source or "lolicon",
            "tag": tag or "",
            "prompt": prompt,
            "result": "",
            "detail": "",
            "api": "",
            "raw": ""
        }
        try:
            source = source or "lolicon"
            if source == "random":
                source, rbody = self._random_config()
                rbody["num"] = 1
                body = rbody
            elif source == "alcy":
                body = {"source": source, "num": 1, "alcyCategory": tag if tag else "random"}
            elif source == "loliapi":
                body = {"source": source, "num": 1, "loliapiCategory": tag if tag else "random"}
            elif source == "uapipro":
                if tag and "+" in tag:
                    cat, sub = tag.split("+", 1)
                    body = {"source": source, "num": 1, "uapiCategory": cat, "uapiType": sub}
                else:
                    body = {"source": source, "num": 1, "uapiCategory": tag if tag else "acg"}
            elif source == "imgapi":
                body = {"source": source, "num": 1, "imgapiFl": tag if tag else "dongman"}
            elif source == "bing":
                body = {"source": source, "num": 1}
            elif source == "dmoe":
                body = {"source": source, "num": 1}
            else:
                body = {"source": source, "num": 1, "r18": 0}
                if tag:
                    body["tag"] = [t.strip() for t in tag.split(",") if t.strip()]
            data = await self._fetch(source, body)
            if not data:
                log_entry["result"] = "失败"
                log_entry["detail"] = "没有找到图片"
                log_entry["api"] = self._describe_api(source, body)
                log_entry["raw"] = "[]"
                yield event.plain_result("没有找到图片 😢")
                return
            cmd_str = self._cmd_for(source, body)
            await self._do_send_image(event, data[0], source, cmd_str)
            log_entry["source"] = source
            log_entry["tag"] = cmd_str
            log_entry["result"] = "成功"
            log_entry["detail"] = data[0].get("title", "") + " - " + data[0].get("author", "")
            log_entry["api"] = self._describe_api(source, body)
            log_entry["raw"] = json.dumps(self._log_image_summary(data), ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"tool setu failed: {e}")
            log_entry["result"] = "失败"
            log_entry["detail"] = str(e)
            log_entry["api"] = self._describe_api(source or "lolicon", {"source": source or "lolicon", "num": 1})
            log_entry["raw"] = "[]"
            yield event.plain_result(f"获取失败: {str(e)}")
        finally:
            self._append_log(log_entry)

    # ─── 指令系统 ──────────────────────────

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("setu", alias={"色图", "随机图", "随机图片"})
    async def on_setu_command(self, event: AstrMessageEvent):
        parts = event.message_str.split()
        source = "lolicon"
        tags = []
        extra_params = {}

        if len(parts) > 1:
            cmd = parts[1].lower()

            if cmd in ["help", "h", "帮助", "用法"]:
                # 生成并发送帮助海报图片（HTML 渲染 + Pillow 兜底）
                try:
                    poster = await self._render_help_poster()
                except Exception as e:
                    logger.error(f"[help] render failed: {e}")
                    yield event.plain_result("帮助海报生成失败：" + str(e))
                    return
                client = self._get_client()
                if client:
                    try:
                        await client.api.call_action(
                            "send_group_msg",
                            group_id=int(event.get_group_id()),
                            message=[{"type": "image", "data": {"file": f"file://{poster}"}}]
                        )
                    except Exception as e:
                        logger.error(f"[help] send failed: {e}")
                        yield event.plain_result("帮助海报发送失败：" + str(e))
                    finally:
                        try: os.unlink(poster)
                        except: pass
                else:
                    yield event.plain_result("无法发送帮助海报（客户端不可用），请在 WebUI 查看帮助")
                return

            elif cmd in ["list", "ls", "列表"]:
                config_dir = self._config_dir()
                names = [p.stem for p in config_dir.glob("*.json")] if config_dir.exists() else []
                cmds = self._load_commands()
                lines = []
                if names: lines.append("📁 配置预设：\n" + "\n".join(f"  {n}" for n in names))
                if cmds: lines.append("\n📋 指令：\n" + "\n".join(f"  {c['name']} ({'随机' if c['mode']=='random' else '分条' if c['mode']=='all' else '合并'} {len(c['presets'])}个步骤)" for c in cmds))
                if not lines: yield event.plain_result("📂 暂无数据\n在 WebUI 点击「保存配置」即可创建")
                else: yield event.plain_result("\n".join(lines))
                return

            elif cmd in ["random", "rand", "全随机", "随"]:
                # 全随机：从 50 个结果池等概率抽取，发图并附带指令
                yield event.plain_result("🎲 全随机抽取中（50 种图源×分类等概率）...")
                log_entry = {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "user": str(event.get_sender_id()),
                    "group": str(event.get_group_id()),
                    "source": "random",
                    "tag": "全随机",
                    "prompt": event.message_str,
                    "result": "",
                    "detail": "",
                    "api": "",
                    "raw": ""
                }
                try:
                    source, params = self._random_config()
                    data = await self._fetch(source, params)
                    if not data:
                        log_entry["result"] = "失败"
                        log_entry["detail"] = "没有找到图片"
                        log_entry["api"] = self._describe_api(source, params)
                        log_entry["raw"] = "[]"
                        self._append_log(log_entry)
                        yield event.plain_result("没有找到图片 😢")
                        return
                    cmd_str = self._cmd_for(source, params)
                    await self._do_send_image(event, data[0], source, cmd_str)
                    log_entry["source"] = source
                    log_entry["tag"] = cmd_str
                    log_entry["result"] = "成功"
                    log_entry["detail"] = data[0].get("title", "") + " - " + data[0].get("author", "")
                    log_entry["api"] = self._describe_api(source, params)
                    log_entry["raw"] = json.dumps(self._log_image_summary(data), ensure_ascii=False, indent=2)
                except Exception as e:
                    logger.error(f"random setu failed: {e}")
                    log_entry["result"] = "失败"
                    log_entry["detail"] = str(e)
                    log_entry["raw"] = "[]"
                    yield event.plain_result(f"获取失败: {str(e)}")
                finally:
                    self._append_log(log_entry)
                return

            elif not cmd.startswith("/"):
                cmds = self._load_commands()
                for cmd_obj in cmds:
                    if cmd_obj["name"] == parts[1]:
                        presets = cmd_obj.get("presets", [])
                        mode = cmd_obj.get("mode", "random")
                        if not presets: break
                        config_dir = self._config_dir()
                        if mode == "all":
                            yield event.plain_result(f"「{parts[1]}」指令执行中（共{len(presets)}个步骤）...")
                            results = []
                            for preset_name in presets:
                                config_path = config_dir / f"{preset_name}.json"
                                if not config_path.exists():
                                    results.append(f"配置「{preset_name}」不存在")
                                    continue
                                with open(config_path, "r", encoding="utf-8") as f:
                                    saved = json.load(f)
                                saved.setdefault("source", "lolicon"); saved.setdefault("num", 1); saved.setdefault("r18", 0)
                                try:
                                    data = await self._fetch(saved["source"], saved)
                                    if data:
                                        await self._do_send_image(event, data[0], saved["source"])
                                        results.append(f"✅ {preset_name}")
                                    else:
                                        results.append(f"❌ {preset_name}（无图片）")
                                except Exception as e:
                                    results.append(f"❌ {preset_name}（{str(e)[:20]}）")
                            yield event.plain_result("执行完毕：\n" + "\n".join(results))
                        elif mode == "merge":
                            yield event.plain_result(f"「{parts[1]}」指令执行中（共{len(presets)}个步骤，合并发送）...")
                            msg_parts = []; temp_files = []; errors = []
                            for preset_name in presets:
                                config_path = config_dir / f"{preset_name}.json"
                                if not config_path.exists():
                                    errors.append(f"配置「{preset_name}」不存在")
                                    continue
                                with open(config_path, "r", encoding="utf-8") as f:
                                    saved = json.load(f)
                                saved.setdefault("source", "lolicon"); saved.setdefault("num", 1); saved.setdefault("r18", 0)
                                try:
                                    data = await self._fetch(saved["source"], saved)
                                    if data:
                                        img = data[0]
                                        url = img.get("url", "")
                                        if not url:
                                            errors.append(f"❌ {preset_name}（空URL）")
                                            continue
                                        title = img.get("title", ""); author = img.get("author", "")
                                        if url.startswith("http"):
                                            async with aiohttp.ClientSession() as s:
                                                async with s.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.pixiv.net/"}) as resp:
                                                    img_data = await resp.read()
                                            suffix = ".jpg"
                                            if url.lower().endswith(".png"): suffix = ".png"
                                            elif url.lower().endswith(".gif"): suffix = ".gif"
                                            elif url.lower().endswith(".webp"): suffix = ".webp"
                                            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                                            tmp.write(img_data); tmp.close()
                                            temp_files.append(tmp.name); file_path = tmp.name
                                        else:
                                            file_path = url
                                        msg_parts.append({"type": "image", "data": {"file": f"file://{file_path}"}})
                                        text = ""
                                        if title: text = f"📷 {title}"
                                        if author: text += f" 👤 {author}"
                                        if text: msg_parts.append({"type": "text", "data": {"text": f"\n[{preset_name}] {text}\n"}})
                                    else:
                                        errors.append(f"❌ {preset_name}（无图片）")
                                except Exception as e:
                                    errors.append(f"❌ {preset_name}（{str(e)[:20]}）")
                            if msg_parts:
                                client = self._get_client()
                                if client:
                                    await client.api.call_action("send_group_msg", group_id=int(event.get_group_id()), message=msg_parts)
                                else:
                                    yield event.plain_result("无法获取 client")
                            for fp in temp_files:
                                try: os.unlink(fp)
                                except: pass
                            result_text = f"合并发送完成（{len(presets)}个步骤）"
                            if errors: result_text += "\n" + "\n".join(errors)
                            yield event.plain_result(result_text)
                        else:
                            selected = random.choice(presets)
                            yield event.plain_result(f"「{parts[1]}」→ 随机选中「{selected}」")
                            config_path = config_dir / f"{selected}.json"
                            if not config_path.exists():
                                yield event.plain_result(f"配置「{selected}」不存在")
                                return
                            with open(config_path, "r", encoding="utf-8") as f:
                                saved = json.load(f)
                            saved.setdefault("source", "lolicon"); saved.setdefault("num", 1); saved.setdefault("r18", 0)
                            try:
                                data = await self._fetch(saved["source"], saved)
                                if not data:
                                    yield event.plain_result("没有找到图片 😢")
                                    return
                                await self._do_send_image(event, data[0], saved["source"])
                            except Exception as e:
                                yield event.plain_result(f"发送失败: {str(e)}")
                        return

                config_path = self._config_dir() / f"{parts[1]}.json"
                if config_path.exists():
                    with open(config_path, "r", encoding="utf-8") as f:
                        saved = json.load(f)
                    saved.setdefault("source", "lolicon"); saved.setdefault("num", 1); saved.setdefault("r18", 0)
                    yield event.plain_result(f"「{parts[1]}」配置加载中...")
                    try:
                        data = await self._fetch(saved["source"], saved)
                        if not data:
                            yield event.plain_result("没有找到图片 😢")
                            return
                        await self._do_send_image(event, data[0], saved["source"])
                        return
                    except Exception as e:
                        yield event.plain_result(f"发送失败: {str(e)}")
                        return

            if cmd in ["uapi", "uapipro"]:
                source = "uapipro"
                if len(parts) > 2:
                    tag_val = parts[2].lower()
                    if "+" in tag_val:
                        cat, sub = tag_val.split("+", 1)
                        extra_params["uapiCategory"] = cat
                        extra_params["uapiType"] = sub
                    else:
                        extra_params["uapiCategory"] = tag_val
            elif cmd == "bing":
                source = "bing"
            elif cmd == "imgapi":
                source = "imgapi"
                if len(parts) > 2:
                    extra_params["imgapiFl"] = parts[2].lower()
            elif cmd == "dmoe":
                source = "dmoe"
            elif cmd == "loliapi":
                source = "loliapi"
                if len(parts) > 2:
                    extra_params["loliapiCategory"] = parts[2].lower().replace("-", "/")
            elif cmd == "alcy":
                source = "alcy"
                if len(parts) > 2:
                    extra_params["alcyCategory"] = parts[2].lower()
            else:
                tag_str = " ".join(parts[1:])
                tags = [t.strip() for t in tag_str.replace("，", ",").split(",") if t.strip()]

        yield event.plain_result("正在获取图片，请稍候...")
        tag_str = ",".join(tags) if tags else (parts[1].lower() if len(parts) > 1 else "")
        log_entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": str(event.get_sender_id()),
            "group": str(event.get_group_id()),
            "source": source,
            "tag": tag_str,
            "prompt": event.message_str,
            "result": "",
            "detail": "",
            "api": "",
            "raw": ""
        }
        try:
            params = {"source": source, "num": 1, "r18": 0, "tag": tags, **extra_params}
            params = {k: v for k, v in params.items() if v is not None and v != "" and v != []}
            data = await self._fetch(source, params)
            if not data:
                log_entry["result"] = "失败"
                log_entry["detail"] = "没有找到图片"
                log_entry["api"] = self._describe_api(source, params)
                log_entry["raw"] = "[]"
                yield event.plain_result("没有找到图片 😢")
                return
            cmd_str = self._cmd_for(source, params)
            await self._do_send_image(event, data[0], source, cmd_str)
            log_entry["result"] = "成功"
            log_entry["tag"] = cmd_str
            log_entry["detail"] = data[0].get("title", "") + " - " + data[0].get("author", "")
            log_entry["api"] = self._describe_api(source, params)
            log_entry["raw"] = json.dumps(self._log_image_summary(data), ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"setu command failed: {e}")
            log_entry["result"] = "失败"
            log_entry["detail"] = str(e)
            log_entry["api"] = self._describe_api(source, {"source": source, "num": 1})
            log_entry["raw"] = "[]"
            yield event.plain_result(f"获取图片失败: {str(e)}")
        finally:
            self._append_log(log_entry)