import asyncio
import json
import os
from typing import Optional
from urllib.parse import urljoin

import requests

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register


class Config:
    def __init__(
        self,
        xf_url: str = "",
        xf_api_key: str = "",
        threads_limit: int = 5,
        search_limit: int = 5,
        request_timeout: int = 10,
        require_slash: bool = True,
    ):
        self.xf_url = xf_url
        self.xf_api_key = xf_api_key
        self.threads_limit = threads_limit
        self.search_limit = search_limit
        self.request_timeout = request_timeout
        self.require_slash = require_slash

@register("xenforo_astrbot", "HuoNiu", "XenForo 论坛集成插件", "1.0.1")
class Main(Star):
    def __init__(self, context: Context):
        super().__init__(context)

        self._cfg_path = self._resolve_config_path("config.json")
        self.cfg = self._safe_load_config(self._cfg_path)
        self._apply_cfg()

        logger.info("[XenForo] 插件已初始化")

    def _resolve_config_path(self, filename: str) -> str:
        get_config_path = getattr(self.context, "get_config_path", None)
        if callable(get_config_path):
            try:
                return get_config_path(filename)
            except Exception as e:
                logger.warning(f"[XenForo] get_config_path 调用失败，将回退到插件目录: {e}")

        # 兼容旧版：配置文件放在插件目录同级（例如 /root/AstrBot/data/plugins/xenforo_astrbot/config.json）
        return os.path.join(os.path.dirname(__file__), filename)

    def _safe_load_config(self, cfg_path: str) -> Config:
        cfg = Config()
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                raw = json.load(f) or {}
        except FileNotFoundError:
            logger.warning(f"[XenForo] 未找到配置文件: {cfg_path}（将使用默认配置）")
            return cfg
        except Exception as e:
            logger.error(f"[XenForo] 读取配置失败，将使用默认配置: {e}")
            return cfg

        try:
            cfg.xf_url = str(raw.get("xf_url", cfg.xf_url) or "")
            cfg.xf_api_key = str(raw.get("xf_api_key", cfg.xf_api_key) or "")
            cfg.threads_limit = int(raw.get("threads_limit", cfg.threads_limit) or cfg.threads_limit)
            cfg.search_limit = int(raw.get("search_limit", cfg.search_limit) or cfg.search_limit)
            cfg.request_timeout = int(raw.get("request_timeout", cfg.request_timeout) or cfg.request_timeout)
            cfg.require_slash = bool(raw.get("require_slash", cfg.require_slash))
        except Exception as e:
            logger.error(f"[XenForo] 配置字段解析失败，将使用默认值: {e}")

        return cfg

    def _refresh_cfg(self) -> None:
        self.cfg = self._safe_load_config(self._cfg_path)
        self._apply_cfg()

    def _apply_cfg(self) -> None:
        self.xf_url = (self.cfg.xf_url or "").strip().rstrip("/")
        self.xf_api_key = (self.cfg.xf_api_key or "").strip()

    def _normalize_text(self, text: str) -> str:
        return text.lstrip("/").strip()

    def _is_slash_message(self, text: str) -> bool:
        text = (text or "").lstrip()
        return text.startswith("/") or text.startswith("／")

    def _ensure_ready(self) -> Optional[str]:
        self._refresh_cfg()
        if not self.xf_url:
            return f"请先配置 XenForo 站点地址：{self._cfg_path} 里的 xf_url"
        if not self.xf_api_key:
            return f"请先配置 XenForo API 密钥：{self._cfg_path} 里的 xf_api_key"
        return None

    def _headers(self) -> dict:
        return {
            "XF-Api-Key": self.xf_api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _abs_url(self, maybe_url: str) -> str:
        if not maybe_url:
            return ""
        if maybe_url.startswith("http://") or maybe_url.startswith("https://"):
            return maybe_url
        return urljoin(self.xf_url + "/", maybe_url.lstrip("/"))

    def _format_http_error(self, status_code: int) -> str:
        if status_code in (401, 403):
            return f"API鉴权失败({status_code})：请检查 XenForo API Key 权限"
        if status_code == 404:
            return "API地址不存在(404)：请确认站点地址是否正确、是否启用了 XenForo API"
        if status_code == 429:
            return "请求过于频繁(429)：请稍后再试"
        return f"API错误: {status_code}"

    def _fetch_latest_threads_text(self, limit: int = 5) -> str:
        try:
            response = requests.get(
                f"{self.xf_url}/api/threads",
                headers=self._headers(),
                params={"limit": limit},
                timeout=self.cfg.request_timeout,
            )
        except Exception as e:
            return f"请求失败: {e}"

        if response.status_code != 200:
            return self._format_http_error(response.status_code)

        try:
            data = response.json()
        except Exception as e:
            return f"解析返回失败: {e}"

        threads = data.get("threads", [])
        if not threads:
            return "暂无主题"

        msg = "📌 最新主题：\n\n"
        for t in threads[:limit]:
            thread_id = t.get("thread_id", "")
            msg += f"• {t.get('title', '无标题')}\n"
            msg += f"  作者: {t.get('username', '未知')}\n"
            msg += f"  {self.xf_url}/threads/{thread_id}/\n\n"
        return msg

    def _extract_search_keyword(self, raw_text: str) -> Optional[str]:
        text = self._normalize_text(raw_text)
        for prefix in ("xf搜索", "xf 搜索", "搜索"):
            if text.startswith(prefix):
                keyword = text[len(prefix):].strip()
                return keyword or None
        return None

    def _fetch_search_threads_text(self, keyword: str, limit: int = 5) -> str:
        # XenForo REST API (2.2+) search flow:
        # 1) POST /api/search   -> returns search_id
        # 2) GET  /api/search/{id} -> returns results
        try:
            create = requests.post(
                f"{self.xf_url}/api/search",
                headers=self._headers(),
                json={
                    "search_type": "thread",
                    "keywords": keyword,
                },
                timeout=self.cfg.request_timeout,
            )
        except Exception as e:
            return f"搜索请求失败: {e}"

        if create.status_code != 200:
            return f"搜索失败: {self._format_http_error(create.status_code)}"

        try:
            create_data = create.json()
        except Exception as e:
            return f"搜索解析失败: {e}"
        search_id = (
            (create_data.get("search") or {}).get("search_id")
            or create_data.get("search_id")
            or (create_data.get("search") or {}).get("id")
        )

        if not search_id:
            return "搜索失败: 未获取到 search_id"

        try:
            result = requests.get(
                f"{self.xf_url}/api/search/{search_id}",
                headers=self._headers(),
                params={"page": 1},
                timeout=self.cfg.request_timeout,
            )
        except Exception as e:
            return f"获取搜索结果失败: {e}"

        if result.status_code != 200:
            return f"搜索失败: {self._format_http_error(result.status_code)}"

        try:
            data = result.json()
        except Exception as e:
            return f"搜索结果解析失败: {e}"
        results = data.get("results", [])
        if not results:
            return f"未找到关于 '{keyword}' 的结果"

        msg = f"🔍 搜索结果：{keyword}\n\n"
        for r in results[:limit]:
            content = r.get("content") or {}
            title = (
                r.get("title")
                or content.get("title")
                or (content.get("Thread") or {}).get("title")
                or "无标题"
            )
            url = (
                r.get("view_url")
                or content.get("view_url")
                or (content.get("Thread") or {}).get("view_url")
            )

            if not url:
                thread_id = (
                    r.get("thread_id")
                    or content.get("thread_id")
                    or (content.get("Thread") or {}).get("thread_id")
                )
                if thread_id:
                    url = f"{self.xf_url}/threads/{thread_id}/"

            url = self._abs_url(url)

            msg += f"• {title}\n"
            if url:
                msg += f"  {url}\n\n"
            else:
                msg += "  (无链接)\n\n"

        return msg

    def _fetch_user_info_text(self, username: str) -> str:
        try:
            response = requests.get(
                f"{self.xf_url}/api/users/find-name",
                headers=self._headers(),
                params={"username": username},
                timeout=self.cfg.request_timeout,
            )
        except Exception as e:
            return f"请求失败: {e}"

        if response.status_code != 200:
            return self._format_http_error(response.status_code)

        try:
            data = response.json()
        except Exception as e:
            return f"解析返回失败: {e}"

        user = data.get("exact")
        if not user:
            return f"未找到用户: {username}"

        msg = "👤 用户信息\n\n"
        msg += f"用户名: {user.get('username', username)}\n"
        if user.get("user_id") is not None:
            msg += f"用户ID: {user.get('user_id')}\n"
        if user.get("register_date") is not None:
            msg += f"注册时间: {user.get('register_date')}\n"
        msg += f"帖子数: {user.get('message_count', 0)}\n"
        msg += f"反应分: {user.get('reaction_score', 0)}\n"

        profile_url = user.get("view_url") or user.get("Profile")
        profile_url = self._abs_url(profile_url) if isinstance(profile_url, str) else ""
        if profile_url:
            msg += f"\n{profile_url}\n"

        return msg

    @filter.command("论坛")
    async def forum_cmd(self, event: AstrMessageEvent):
        """获取最新帖子（兼容 /论坛）"""
        err = self._ensure_ready()
        if err:
            yield event.plain_result(err)
            return

        try:
            text = await asyncio.to_thread(
                self._fetch_latest_threads_text,
                limit=int(self.cfg.threads_limit or 5),
            )
            yield event.plain_result(text)
        except Exception as e:
            logger.error(f"[XenForo] 获取帖子失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")

    # @filter.command("搜索")
    # async def search_cmd(self, event: AstrMessageEvent, keyword: str = ""):
    #     """搜索帖子（兼容 /搜索 关键词）"""
        err = self._ensure_ready()
        if err:
            yield event.plain_result(err)
            return

        keyword = (keyword or "").strip() or (self._extract_search_keyword(event.message_str) or "").strip()
        if not keyword:
            yield event.plain_result("请输入搜索关键词，例如：/搜索 Python")
            return

        try:
            text = await asyncio.to_thread(
                self._fetch_search_threads_text,
                keyword,
                limit=int(self.cfg.search_limit or 5),
            )
            yield event.plain_result(text)
        except Exception as e:
            logger.error(f"[XenForo] 搜索失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")

    @filter.command("用户")
    async def user_cmd(self, event: AstrMessageEvent, username: str = ""):
        """查询用户信息（/用户 用户名）"""
        err = self._ensure_ready()
        if err:
            yield event.plain_result(err)
            return

        username = (username or "").strip()
        if not username:
            raw = self._normalize_text(event.message_str)
            if raw.startswith("用户"):
                username = raw[len("用户") :].strip()

        if not username:
            yield event.plain_result("请输入用户名，例如：/用户 张三")
            return

        try:
            text = await asyncio.to_thread(self._fetch_user_info_text, username)
            yield event.plain_result(text)
        except Exception as e:
            logger.error(f"[XenForo] 用户查询失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")
    
    @filter.command_group("xf")
    def xf(self):
        """XenForo 命令组"""
        pass
    
    @xf.command("论坛")
    async def forum(self, event: AstrMessageEvent):
        """获取最新帖子"""
        err = self._ensure_ready()
        if err:
            yield event.plain_result(err)
            return

        try:
            text = await asyncio.to_thread(
                self._fetch_latest_threads_text,
                limit=int(self.cfg.threads_limit or 5),
            )
            yield event.plain_result(text)
        except Exception as e:
            logger.error(f"[XenForo] 获取帖子失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")
    
    # @xf.command("搜索")
    # async def search(self, event: AstrMessageEvent, keyword: str = ""):
    #     """搜索帖子: xf 搜索 关键词"""
        err = self._ensure_ready()
        if err:
            yield event.plain_result(err)
            return

        keyword = (keyword or "").strip() or (self._extract_search_keyword(event.message_str) or "").strip()
        if not keyword:
            yield event.plain_result("请输入搜索关键词，例如：/搜索 Python")
            return
        
        try:
            text = await asyncio.to_thread(
                self._fetch_search_threads_text,
                keyword,
                limit=int(self.cfg.search_limit or 5),
            )
            yield event.plain_result(text)
        except Exception as e:
            logger.error(f"[XenForo] 搜索失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")

    @xf.command("用户")
    async def user(self, event: AstrMessageEvent, username: str = ""):
        """查询用户信息: xf 用户 用户名"""
        err = self._ensure_ready()
        if err:
            yield event.plain_result(err)
            return

        username = (username or "").strip()
        if not username:
            raw = self._normalize_text(event.message_str)
            if raw.startswith("xf 用户"):
                username = raw[len("xf 用户") :].strip()
            elif raw.startswith("xf用户"):
                username = raw[len("xf用户") :].strip()
            elif raw.startswith("用户"):
                username = raw[len("用户") :].strip()

        if not username:
            yield event.plain_result("请输入用户名，例如：/用户 张三")
            return

        try:
            text = await asyncio.to_thread(self._fetch_user_info_text, username)
            yield event.plain_result(text)
        except Exception as e:
            logger.error(f"[XenForo] 用户查询失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")
