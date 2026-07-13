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

NAPCAT_HTTP = "http://127.0.0.1:3001"
NAPCAT_TOKEN = "iloveu"
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
        logger.info(f"[handle_fetch] source={source}, num={num}, body={json.dumps(body, ensure_ascii=False)}")
        try:
            data = await self._fetch(source, body)
            logger.info(f"[handle_fetch] result count={len(data)}")
            return json_response({"images": data})
        except Exception as e:
            logger.error(f"[handle_fetch] failed: {e}", exc_info=True)
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
                suffix = ".jpg"
                if "png" in ct: suffix = ".png"
                elif "gif" in ct: suffix = ".gif"
                elif "webp" in ct: suffix = ".webp"
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                tmp.write(img_data); tmp.close()
                b64 = base64.b64encode(img_data).decode("ascii")
                out.append({"url": tmp.name, "thumb": f"data:{ct};base64,{b64}", "title": f"UApiPro {category}", "author": img_type or category, "pid": f"uapi_{i}"})
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
                    out.append({"url": tmp.name, "thumb": f"data:{ct};base64,{b64}", "title": f"imgapi {fl or '壁纸'}", "author": f"{data.get('width', '?')}x{data.get('height', '?')}", "pid": f"imgapi_{i}"})
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
                suffix = ".jpg"
                if "png" in ct: suffix = ".png"
                elif "gif" in ct: suffix = ".gif"
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                tmp.write(img_data); tmp.close()
                b64 = base64.b64encode(img_data).decode("ascii")
                out.append({"url": tmp.name, "thumb": f"data:{ct};base64,{b64}", "title": "dmoe 二次元", "author": "dmoe.cc", "pid": f"dmoe_{i}"})
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
                suffix = ".jpg"
                if "png" in ct: suffix = ".png"
                elif "gif" in ct: suffix = ".gif"
                elif "webp" in ct: suffix = ".webp"
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                tmp.write(img_data); tmp.close()
                b64 = base64.b64encode(img_data).decode("ascii")
                out.append({"url": tmp.name, "thumb": f"data:{ct};base64,{b64}", "title": f"LoliAPI {cat}", "author": "loliapi.com", "pid": f"loliapi_{i}"})
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
                    out.append({"url": tmp.name, "thumb": f"data:image/jpeg;base64,{b64}", "title": f"栗次元 {cat}", "author": "alcy.cc", "pid": f"alcy_{item.get('id', i)}"})
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
                    t = img.get("title", ""); a = img.get("author", ""); p = img.get("pid", "")
                    if t or a or p: msg.append({"type": "text", "data": {"text": f"\n{t} - {a} ({p})"}})
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

    async def _do_send_image(self, event, img, source_name=""):
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
            source(string): 图源。lolicon(Pixiv插画) / uapipro(多分类壁纸) / bing(风景壁纸) / imgapi(随机壁纸) / dmoe(二次元) / loliapi(多分类二次元) / alcy(栗次元多分类)
            tag(string): 搜索标签或分类。不同图源的可选值如下：

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
            "detail": ""
        }
        try:
            source = source or "lolicon"
            if source == "alcy":
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
                yield event.plain_result("没有找到图片 😢")
                return
            await self._do_send_image(event, data[0], source)
            log_entry["result"] = "成功"
            log_entry["detail"] = data[0].get("title", "") + " - " + data[0].get("author", "")
        except Exception as e:
            logger.error(f"tool setu failed: {e}")
            log_entry["result"] = "失败"
            log_entry["detail"] = str(e)
            yield event.plain_result(f"获取失败: {str(e)}")
        finally:
            self.llm_call_logs.insert(0, log_entry)
            if len(self.llm_call_logs) > 100:
                self.llm_call_logs = self.llm_call_logs[:100]

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
                config_dir = self._config_dir()
                names = [p.stem for p in config_dir.glob("*.json")] if config_dir.exists() else []
                cmds = self._load_commands()
                config_tip = ""
                if names: config_tip = "\n".join(f"    · {n}" for n in names)
                cmd_tip = ""
                if cmds: cmd_tip = "\n".join(f"    · {c['name']}（{'随机' if c['mode']=='random' else '分条' if c['mode']=='all' else '合并'} {len(c['presets'])}个步骤）" for c in cmds)
                yield event.plain_result(
                    "📖 随机图片插件 · 完整帮助\n\n"
                    "━━━ 💬 自然语言调用 ━━━\n\n"
                    "直接对我说「发张二次元图」「来张原神」「看风景」「小狐狸」等，\n"
                    "AI 会自动理解并调用插件获取图片，无需记指令！\n\n"
                    "━━━ 📟 指令用法 ━━━\n\n"
                    "▶ /setu\n  默认 Lolicon 随机图\n\n"
                    "▶ /setu <标签>\n  Lolicon 按标签搜索，如 /setu 百合\n\n"
                    "▶ /setu <图源>\n  切换图源，如 /setu alcy\n\n"
                    "▶ /setu <图源> <分类>\n  切换图源并指定分类，如 /setu alcy xhl\n\n"
                    "▶ /setu list\n  查看已保存的配置预设和指令\n\n"
                    "▶ /setu help\n  显示本帮助\n\n"
                    "━━━ 🎨 图源 & 分类一览 ━━━\n\n"
                    "🎨 Lolicon\n  标签：任意关键词，如 原神,泳装\n  逗号表示 AND 搜索，竖线 | 表示 OR\n\n"
                    "📦 UApiPro\n  主分类：二次元(acg) 风景(landscape) 动漫混合(anime)\n          电脑壁纸(pc_wallpaper) 手机壁纸(mobile_wallpaper)\n          动漫图(general_anime) AI绘画(ai_drawing)\n          表情包(bq) 福瑞(furry)\n  子分类（用+连接）：acg+pc acg+mb\n    bq+xiongmao bq+waiguoren bq+maomao bq+ikun bq+eciyuan\n    furry+z4k furry+szs8k furry+s4k furry+4k\n\n"
                    "🌿 LoliAPI\n  acg(自适应) bg(墙纸) acg/pc(电脑) acg/pe(手机) acg/pp(头像)\n\n"
                    "🎯 栗次元\n  ycy(自适应) moez(萌版) ai(AI) ysz(原神)\n  pc(横图) moe(萌横) fj(风景) bd(白底) ys(原横)\n  acg(动图) mp(竖图) moemp(萌竖) ysmp(原竖)\n  aimp(AI竖) fjmp(风竖) tx(头像) lai(胡桃) xhl(狐狸)\n\n"
                    "🖼️ imgapi\n  meizi(美女) dongman(动漫) fengjing(风景) suiji(随机)\n\n"
                    "🏔️ Bing · 🎨 dmoe\n  无分类，直接 /setu bing 或 /setu dmoe\n\n"
                    "━━━ 🧩 WebUI 功能 ━━━\n\n"
                    "在插件 WebUI 中还有更多功能：\n\n"
                    "🔍 快速获取\n  可视化调参，7 个图源完整自定义选项，\n  选择图片后勾选群一键发送\n\n"
                    "🧱 积木编程\n  ① 调好参数 → 保存为配置预设（积木块）\n  ② 组合多个积木块 → 保存为指令\n  ③ 支持三种输出模式：\n     · 随机选一个：每次随机挑一个积木块执行\n     · 分条输出：每个积木块发一条消息\n     · 合并输出：所有图片合并成一条消息\n  ④ 保存后可通过 /setu <指令名> 在群聊中调用\n\n"
                    "📋 调用记录\n  查看 AI 调用插件的记录，点击可查看详情，\n  方便调试和追踪使用情况\n\n"
                    "━━━ 📁 已保存的配置 ━━━\n"
                    + (config_tip if config_tip else "    暂无，在 WebUI 调好参数后点击「保存配置」即可创建\n")
                    + ("\n" if config_tip else "")
                    + ("━━━ 📋 已保存的指令 ━━━\n" + cmd_tip + "\n" if cmd_tip else "")
                )
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
        try:
            params = {"source": source, "num": 1, "r18": 0, "tag": tags, **extra_params}
            params = {k: v for k, v in params.items() if v is not None and v != "" and v != []}
            data = await self._fetch(source, params)
            if not data:
                yield event.plain_result("没有找到图片 😢")
                return
            await self._do_send_image(event, data[0], source)
        except Exception as e:
            logger.error(f"setu command failed: {e}")
            yield event.plain_result(f"获取图片失败: {str(e)}")