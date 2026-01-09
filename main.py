import json
import os
import requests
from typing import Optional

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp

@register("xenforo_astrbot", "HuoNiu", "XenForo 论坛集成插件", "1.0.0")
class Main(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        
        # 配置
        self.xf_url = "https://oksgo.com"
        self.xf_api_key = "Kwcc3l7mDuLeCzuLJnibJklJjzhxd3l_"
        
        logger.info("[XenForo] 插件已初始化")

    def _normalize_text(self, text: str) -> str:
        return text.lstrip("/").strip()

    def _headers(self) -> dict:
        return {"XF-Api-Key": self.xf_api_key}

    def _fetch_latest_threads_text(self, limit: int = 5) -> str:
        response = requests.get(
            f"{self.xf_url}/api/threads",
            headers=self._headers(),
            params={"limit": limit},
            timeout=10,
        )

        if response.status_code != 200:
            return f"API错误: {response.status_code}"

        data = response.json()
        threads = data.get("threads", [])
        if not threads:
            return "暂无主题"

        msg = "📌 最新主题：\n\n"
        for t in threads[:limit]:
            msg += f"• {t.get('title', '无标题')}\n"
            msg += f"  作者: {t.get('username', '未知')}\n"
            msg += f"  {self.xf_url}/threads/{t.get('thread_id', '')}/\n\n"
        return msg

    def _extract_search_keyword(self, raw_text: str) -> Optional[str]:
        text = self._normalize_text(raw_text)
        for prefix in ("xf搜索", "xf 搜索", "搜索"):
            if text.startswith(prefix):
                keyword = text[len(prefix):].strip()
                return keyword or None
        return None

    def _fetch_search_threads_text(self, keyword: str, limit: int = 5) -> str:
        response = requests.get(
            f"{self.xf_url}/api/threads/search",
            headers=self._headers(),
            params={"q": keyword, "limit": limit},
            timeout=10,
        )

        if response.status_code != 200:
            return f"搜索失败: {response.status_code}"

        data = response.json()
        results = data.get("results", [])
        if not results:
            return f"未找到关于 '{keyword}' 的主题"

        msg = f"🔍 搜索结果：{keyword}\n\n"
        for r in results[:limit]:
            msg += f"• {r.get('title', '无标题')}\n"
            msg += f"  {self.xf_url}/threads/{r.get('thread_id', '')}/\n\n"
        return msg

    @filter.command("论坛")
    async def forum_cmd(self, event: AstrMessageEvent):
        """获取最新帖子（兼容 /论坛）"""
        try:
            yield event.plain_result(self._fetch_latest_threads_text(limit=5))
        except Exception as e:
            logger.error(f"[XenForo] 获取帖子失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")

    @filter.command("搜索")
    async def search_cmd(self, event: AstrMessageEvent):
        """搜索帖子（兼容 /搜索 关键词）"""
        keyword = self._extract_search_keyword(event.message_str)
        if not keyword:
            yield event.plain_result("请输入搜索关键词，例如：/搜索 Python")
            return

        try:
            yield event.plain_result(self._fetch_search_threads_text(keyword, limit=5))
        except Exception as e:
            logger.error(f"[XenForo] 搜索失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")
    
    @filter.command_group("xf")
    def xf(self):
        """XenForo 命令组"""
        pass
    
    @xf.command("论坛")
    async def forum(self, event: AstrMessageEvent):
        """获取最新帖子"""
        try:
            yield event.plain_result(self._fetch_latest_threads_text(limit=5))
        except Exception as e:
            logger.error(f"[XenForo] 获取帖子失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")
    
    @xf.command("搜索")
    async def search(self, event: AstrMessageEvent):
        """搜索帖子: xf搜索 关键词"""
        keyword = self._extract_search_keyword(event.message_str)
        if not keyword:
            yield event.plain_result("请输入搜索关键词，例如：xf搜索 Python")
            return
        
        try:
            yield event.plain_result(self._fetch_search_threads_text(keyword, limit=5))
        except Exception as e:
            logger.error(f"[XenForo] 搜索失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")
