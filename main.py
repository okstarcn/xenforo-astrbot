import json
import os
import requests

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
    
    @filter.command_group("xf")
    def xf(self):
        """XenForo 命令组"""
        pass
    
    @xf.command("论坛")
    async def forum(self, event: AstrMessageEvent):
        """获取最新帖子"""
        try:
            headers = {"XF-Api-Key": self.xf_api_key}
            response = requests.get(
                f"{self.xf_url}/api/threads",
                headers=headers,
                params={"limit": 5},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                threads = data.get('threads', [])
                
                if threads:
                    msg = "📌 最新主题：\n\n"
                    for t in threads[:5]:
                        msg += f"• {t.get('title', '无标题')}\n"
                        msg += f"  作者: {t.get('username', '未知')}\n"
                        msg += f"  {self.xf_url}/threads/{t.get('thread_id', '')}/\n\n"
                    
                    yield event.plain_result(msg)
                else:
                    yield event.plain_result("暂无主题")
            else:
                yield event.plain_result(f"API错误: {response.status_code}")
        except Exception as e:
            logger.error(f"[XenForo] 获取帖子失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")
    
    @xf.command("搜索")
    async def search(self, event: AstrMessageEvent):
        """搜索帖子: xf搜索 关键词"""
        keyword = event.message_str.replace("xf搜索", "").replace("搜索", "").strip()
        if not keyword:
            yield event.plain_result("请输入搜索关键词，例如：xf搜索 Python")
            return
        
        try:
            headers = {"XF-Api-Key": self.xf_api_key}
            response = requests.get(
                f"{self.xf_url}/api/threads/search",
                headers=headers,
                params={"q": keyword, "limit": 5},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if results:
                    msg = f"🔍 搜索结果：{keyword}\n\n"
                    for r in results[:5]:
                        msg += f"• {r.get('title', '无标题')}\n"
                        msg += f"  {self.xf_url}/threads/{r.get('thread_id', '')}/\n\n"
                    
                    yield event.plain_result(msg)
                else:
                    yield event.plain_result(f"未找到关于 '{keyword}' 的主题")
            else:
                yield event.plain_result(f"搜索失败: {response.status_code}")
        except Exception as e:
            logger.error(f"[XenForo] 搜索失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")
