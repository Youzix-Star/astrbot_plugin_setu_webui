import json
import aiohttp
import logging
import tempfile
import os
import base64
import random
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

        logger.info(f"[lolicon] request params: {json.dumps(params, ensure_ascii=False)}")

        async with aiohttp.ClientSession() as s:
            async with s.post("https://api.lolicon.app/setu/v2", json=params, timeout=15) as r:
                data = await r.json()
                items = data.get("data", [])
                logger.info(f"[lolicon] response: {json.dumps(data, ensure_ascii=False)[:2000]}")
                logger.info(f"[lolicon] items count={len(items)}")
                out = []
                for i, item in enumerate(items):
                    urls = item.get("urls", {})
                    logger.info(f"[lolicon] item[{i}] urls={json.dumps(urls, ensure_ascii=False)}")
                    img_url = urls.get("original", "") or urls.get("regular", "") or urls.get("small", "") or urls.get("thumb", "") or urls.get("mini", "")
                    logger.info(f"[lolicon] item[{i}] selected_url={img_url}")
                    out.append({
                        "url": img_url,
                        "thumb": urls.get("thumb") or urls.get("small") or urls.get("regular") or img_url,
                        "title": item.get("title", ""),
                        "author": item.get("author", ""),
                        "pid": item.get("pid", "")
                    })
                logger.info(f"[lolicon] returning {len(out)} images")
                return out

    async def fetch_uapi(self, body):
        category = body.get("uapiCategory", "acg")
        img_type = body.get("uapiType", "")
        num = min(int(body.get("num", 5)), 10)
        logger.info(f"[uapi] category={category}, type={img_type}, num={num}")
        out = []
        for i in range(num):
            try:
                ts = int(__import__("time").time() * 1000)
                url = f"https://uapis.cn/api/v1/random/image?category={category}&_={ts}"
                if img_type: url += f"&type={img_type}"
                logger.info(f"[uapi] requesting: {url}")
                async with aiohttp.ClientSession() as s:
                    async with s.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                        ct = resp.headers.get("Content-Type", "")
                        img_data = await resp.read()
                        logger.info(f"[uapi] resp status={resp.status}, content-type={ct}, size={len(img_data)}")
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
        logger.info(f"[uapi] returning {len(out)} images")
        return out

    async def fetch_bing(self, body):
        num = min(int(body.get("num", 5)), 8)
        bing_source = body.get("bingSource", "uapi")
        logger.info(f"[bing] source={bing_source}, num={num}")
        out = []
        if bing_source == "official":
            for i in range(num):
                try:
                    url = f"https://www.bing.com/HPImageArchive.aspx?format=js&idx={i}&n=1&mkt=zh-CN"
                    logger.info(f"[bing] official request: {url}")
                    async with aiohttp.ClientSession() as s:
                        async with s.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                            data = await resp.json()
                    images = data.get("images", [])
                    logger.info(f"[bing] official response images={len(images)}")
                    if images:
                        img = images[0]
                        img_url = f"https://www.bing.com{img['url']}"
                        logger.info(f"[bing] official image url={img_url}")
                        out.append({"url": img_url, "thumb": img_url.replace("1920x1080", "640x480"), "title": img.get("title", "Bing 壁纸"), "author": img.get("copyright", ""), "pid": f"bing_official_{img.get('startdate', i)}"})
                except Exception as e:
                    logger.warning(f"[bing] official fetch failed[{i}]: {e}")
                    continue
        else:
            for i in range(num):
                try:
                    rp = "&random=true" if num > 1 else ""
                    url = f"https://uapis.cn/api/v1/image/bing-daily?format=json&resolution=1080{rp}"
                    logger.info(f"[bing] uapi request: {url}")
                    async with aiohttp.ClientSession() as s:
                        async with s.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                            data = await resp.json()
                    img_url = data.get("image_url") or data.get("image_url_4k") or data.get("image_url_1080") or ""
                    logger.info(f"[bing] uapi response img_url={img_url}, title={data.get('title', '')}")
                    if img_url:
                        out.append({"url": img_url, "thumb": data.get("image_url_1080") or img_url, "title": data.get("title", "Bing 壁纸"), "author": data.get("copyright", ""), "pid": f"bing_{data.get('date', i)}"})
                except Exception as e:
                    logger.warning(f"[bing] uapi fetch failed[{i}]: {e}")
                    continue
        logger.info(f"[bing] returning {len(out)} images")
        return out

    async def fetch_imgapi(self, body):
        zd = body.get("imgapiZd", "")
        fl = body.get("imgapiFl", "")
        num = min(int(body.get("num", 5)), 10)
        logger.info(f"[imgapi] zd={zd}, fl={fl}, num={num}")
        out = []
        for i in range(num):
            try:
                ts = int(__import__("time").time() * 1000)
                url = f"https://imgapi.cn/api.php?zd={zd}&fl={fl}&gs=json"
                logger.info(f"[imgapi] request: {url}")
                async with aiohttp.ClientSession() as s:
                    async with s.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                        data = await resp.json(content_type=None)
                logger.info(f"[imgapi] response: {data}")
                img_url = data.get("imgurl", "") or data.get("img", "") or data.get("url", "")
                if img_url:
                    logger.info(f"[imgapi] downloading: {img_url}")
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
                else:
                    logger.warning(f"[imgapi] no image url in response")
            except Exception as e:
                logger.warning(f"[imgapi] fetch failed[{i}]: {e}")
                continue
        logger.info(f"[imgapi] returning {len(out)} images")
        return out

    async def fetch_dmoe(self, body):
        num = min(int(body.get("num", 5)), 10)
        logger.info(f"[dmoe] num={num}")
        out = []
        for i in range(num):
            try:
                ts = int(__import__("time").time() * 1000)
                url = f"https://www.dmoe.cc/random.php?t={ts}"
                logger.info(f"[dmoe] request: {url}")
                async with aiohttp.ClientSession() as s:
                    async with s.get(url, timeout=30, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                        img_data = await resp.read()
                        ct = resp.headers.get("Content-Type", "image/jpeg")
                        logger.info(f"[dmoe] resp status={resp.status}, content-type={ct}, size={len(img_data)}, final_url={resp.url}")
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
        logger.info(f"[dmoe] returning {len(out)} images")
        return out

    async def fetch_loliapi(self, body):
        category = body.get("loliapiCategory", "random")
        num = min(int(body.get("num", 5)), 10)
        all_cats = ["acg", "bg", "acg/pc", "acg/pe", "acg/pp"]
        logger.info(f"[loliapi] category={category}, num={num}")
        out = []
        for i in range(num):
            try:
                if category == "random": cat = random.choice(all_cats)
                else: cat = category
                ts = int(__import__("time").time() * 1000)
                url = f"https://www.loliapi.com/{cat}/?_={ts}"
                logger.info(f"[loliapi] request: {url}")
                async with aiohttp.ClientSession() as s:
                    async with s.get(url, timeout=30, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                        img_data = await resp.read()
                        ct = resp.headers.get("Content-Type", "image/jpeg")
                        logger.info(f"[loliapi] resp status={resp.status}, content-type={ct}, size={len(img_data)}")
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
        logger.info(f"[loliapi] returning {len(out)} images")
        return out

    async def fetch_alcy(self, body):
        category = body.get("alcyCategory", "random")
        compress = body.get("alcyCompress", "800")
        num = min(int(body.get("num", 5)), 10)
        all_cats = ["ycy", "moez", "ai", "ysz", "pc", "moe", "fj", "bd", "ys", "acg", "mp", "moemp", "ysmp", "aimp", "fjmp", "tx", "lai", "xhl"]
        logger.info(f"[alcy] category={category}, compress={compress}, num={num}")
        out = []
        for i in range(num):
            try:
                if category == "random": cat = random.choice(all_cats)
                else: cat = category
                url = f"https://t.alcy.cc/json?{cat}=1"
                logger.info(f"[alcy] request: {url}")
                async with aiohttp.ClientSession() as s:
                    async with s.get(url, timeout=15) as resp:
                        data = await resp.json(content_type=None)
                item = data.get("data", {})
                link = item.get("link", "")
                logger.info(f"[alcy] response link={link}")
                if link:
                    logger.info(f"[alcy] downloading: {link}")
                    async with aiohttp.ClientSession() as s:
                        async with s.get(link, timeout=30, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://t.alcy.cc/"}) as resp:
                            img_data = await resp.read()
                            logger.info(f"[alcy] download size={len(img_data)}")
                    if compress != "none":
                        img_data = self._compress_image(img_data, int(compress))
                        logger.info(f"[alcy] after compress size={len(img_data)}")
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                    tmp.write(img_data); tmp.close()
                    b64 = base64.b64encode(img_data).decode("ascii")
                    out.append({"url": tmp.name, "thumb": f"data:image/jpeg;base64,{b64}", "title": f"栗次元 {cat}", "author": "alcy.cc", "pid": f"alcy_{item.get('id', i)}"})
            except Exception as e:
                logger.warning(f"[alcy] fetch failed[{i}]: {e}")
                continue
        logger.info(f"[alcy] returning {len(out)} images")
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
        logger.info(f"[send] groups={ids}, images_count={len(images)}")
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
                        logger.warning(f"[send] image[{idx}] has empty url, skipping")
                        continue
                    logger.info(f"[send] image[{idx}] url={url[:100]}")
                    if not url.startswith("http"):
                        msg.append({"type": "image", "data": {"file": f"file://{url}"}})
                    else:
                        try:
                            async with aiohttp.ClientSession() as s:
                                async with s.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": "https://www.pixiv.net/"}) as resp:
                                    img_data = await resp.read()
                                    logger.info(f"[send] downloaded {len(img_data)} bytes from {url[:80]}")
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
                logger.info(f"[send] sending to group {gid}, msg_parts={len(msg)}")
                await client.api.call_action("send_group_msg", group_id=int(gid), message=msg)
                ok += 1
                logger.info(f"[send] success to {gid}")
            except Exception as e:
                logger.warning(f"[send] send to {gid} failed: {e}")
                fail += 1
            finally:
                for fp in temp_files:
                    try: os.unlink(fp)
                    except: pass
        logger.info(f"[send] done: ok={ok}, fail={fail}")
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
        logger.info(f"[do_send] url={url[:100] if url else 'EMPTY'}")
        if not url:
            logger.error(f"[do_send] URL is empty, img={img}")
            await event.send("获取的图片 URL 为空，请重试")
            return
        title = img.get("title", "")
        author = img.get("author", "")
        if url.startswith("http"):
            logger.info(f"[do_send] downloading {url[:80]}")
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.pixiv.net/"}) as resp:
                    img_data = await resp.read()
                    logger.info(f"[do_send] downloaded {len(img_data)} bytes, status={resp.status}")
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
            logger.info(f"[do_send] sending to group {event.get_group_id()}")
            try:
                await client.api.call_action("send_group_msg",
                    group_id=int(event.get_group_id()),
                    message=[
                        {"type": "image", "data": {"file": f"file://{file_path}"}},
                        {"type": "text", "data": {"text": f"\n{text}"}}
                    ]
                )
                logger.info(f"[do_send] send success")
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

    # ─── 指令系统 ──────────────────────────

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("setu", alias={"色图", "随机图", "随机图片"})
    async def on_setu_command(self, event: AstrMessageEvent):
        parts = event.message_str.split()
        source = "lolicon"
        tags = []

        if len(parts) > 1:
            cmd = parts[1].lower()

            if cmd in ["help", "h", "帮助", "用法"]:
                config_dir = self._config_dir()
                names = [p.stem for p in config_dir.glob("*.json")] if config_dir.exists() else []
                cmds = self._load_commands()
                config_tip = ""
                if names: config_tip = f"\n\n▶ /setu <配置名>\n  快捷调用已保存的配置：\n    " + "\n    ".join(names)
                cmd_tip = ""
                if cmds: cmd_tip = f"\n\n▶ 复杂指令：\n  " + "\n  ".join(f"/setu {c['name']} ({'随机' if c['mode']=='random' else '分条' if c['mode']=='all' else '合并'} {len(c['presets'])}个配置)" for c in cmds)
                yield event.plain_result(
                    "📖 随机图片指令帮助\n\n"
                    "▶ /setu\n  默认 Lolicon 随机图\n\n"
                    "▶ /setu <标签>\n  Lolicon 按标签搜索\n  例：/setu 百合\n  例：/setu 百合,原神\n\n"
                    "▶ /setu <图源>\n  切换图源：\n  uapi / bing / imgapi / dmoe / loliapi / alcy\n\n"
                    "▶ /setu list\n  查看已保存的配置\n"
                    f"{config_tip}{cmd_tip}\n\n"
                    "▶ /setu help\n  显示本帮助"
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

            # 尝试加载自定义指令
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
                            msg_parts = []
                            temp_files = []
                            errors = []
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
                                            temp_files.append(tmp.name)
                                            file_path = tmp.name
                                        else:
                                            file_path = url

                                        msg_parts.append({"type": "image", "data": {"file": f"file://{file_path}"}})
                                        text = ""
                                        if title: text = f"📷 {title}"
                                        if author: text += f" 👤 {author}"
                                        if text:
                                            msg_parts.append({"type": "text", "data": {"text": f"\n[{preset_name}] {text}\n"}})
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

                # 尝试加载配置预设
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

            if cmd in ["uapi", "uapipro"]: source = "uapipro"
            elif cmd == "bing": source = "bing"
            elif cmd == "imgapi": source = "imgapi"
            elif cmd == "dmoe": source = "dmoe"
            elif cmd == "loliapi": source = "loliapi"
            elif cmd == "alcy": source = "alcy"
            else:
                tag_str = " ".join(parts[1:])
                tags = [t.strip() for t in tag_str.replace("，", ",").split(",") if t.strip()]

        yield event.plain_result("正在获取图片，请稍候...")
        try:
            params = {"source": source, "num": 1, "r18": 0, "tag": tags}
            data = await self._fetch(source, params)
            if not data:
                yield event.plain_result("没有找到图片 😢")
                return
            await self._do_send_image(event, data[0], source)
        except Exception as e:
            logger.error(f"setu command failed: {e}")
            yield event.plain_result(f"获取图片失败: {str(e)}")