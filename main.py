import asyncio
import json
import os
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import requests

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.api.provider import Provider


class Config:
    def __init__(
        self,
        xf_url: str = "",
        xf_api_key: str = "",
        threads_limit: int = 5,
        request_timeout: int = 10,
        require_slash: bool = True,
    ):
        self.xf_url = xf_url
        self.xf_api_key = xf_api_key
        self.threads_limit = threads_limit
        self.request_timeout = request_timeout
        self.require_slash = require_slash

@register("xenforo_astrbot", "HuoNiu", "XenForo 论坛集成插件", "1.0.2")
class Main(Star):
    def __init__(self, context: Context):
        super().__init__(context)

        self._cfg_path = self._resolve_config_path("config.json")
        self.cfg = self._safe_load_config(self._cfg_path)
        self._apply_cfg()

        logger.info("[XenForo] 插件已初始化")
        
        # 注册HTTP路由接收XenForo通知
        self._register_http_routes()

    def _register_http_routes(self):
        """注册HTTP路由"""
        try:
            provider: Provider = self.context.get_provider()
            if provider and hasattr(provider, 'register_http_route'):
                # 注册通知接收端点
                provider.register_http_route(
                    path='/xenforo/notify',
                    methods=['POST'],
                    handler=self._handle_xenforo_notification
                )
                # 注册测试端点
                provider.register_http_route(
                    path='/xenforo/test',
                    methods=['GET', 'POST'],
                    handler=self._handle_test
                )
                logger.info("[XenForo] HTTP路由已注册: /xenforo/notify, /xenforo/test")
            else:
                logger.warning("[XenForo] 当前AstrBot版本不支持HTTP路由注册")
        except Exception as e:
            logger.error(f"[XenForo] HTTP路由注册失败: {e}")
    
    async def _handle_xenforo_notification(self, request):
        """处理来自XenForo的通知"""
        try:
            # 获取JSON数据
            if hasattr(request, 'json'):
                data = await request.json()
            else:
                import json
                body = await request.body()
                data = json.loads(body)
            
            group_id = str(data.get('group_id', ''))
            message = data.get('message', '')
            event_type = data.get('event_type', '')
            
            if not group_id or not message:
                logger.warning(f"[XenForo] 收到无效通知数据: {data}")
                return {'error': '缺少必要参数'}, 400
            
            logger.info(f"[XenForo] 收到通知 {event_type} -> 群 {group_id}")
            
            # 发送到QQ群
            try:
                await self.context.send_message(
                    message_type="group",
                    target_id=group_id,
                    message=message
                )
                logger.info(f"[XenForo] 通知已发送到群 {group_id}")
                return {'status': 'success'}, 200
            except Exception as e:
                logger.error(f"[XenForo] 发送消息到群 {group_id} 失败: {e}")
                return {'error': f'发送失败: {str(e)}'}, 500
                
        except Exception as e:
            logger.error(f"[XenForo] 处理通知失败: {e}")
            return {'error': str(e)}, 500
    
    async def _handle_test(self, request):
        """测试端点"""
        return {
            'status': 'ok',
            'message': 'AstrBot XenForo插件运行正常',
            'version': '1.0.2'
        }, 200

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

    def _format_timestamp(self, timestamp) -> str:
        """将Unix时间戳转换为可读的日期时间格式"""
        try:
            if timestamp is None:
                return "未知"
            dt = datetime.fromtimestamp(int(timestamp))
            return dt.strftime("%Y年%m月%d日 %H:%M:%S")
        except Exception as e:
            logger.warning(f"[XenForo] 时间戳转换失败: {timestamp}, 错误: {e}")
            return str(timestamp)

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

    def _fetch_thread_detail_text(self, thread_id: str) -> str:
        """获取主题详情"""
        try:
            response = requests.get(
                f"{self.xf_url}/api/threads/{thread_id}",
                headers=self._headers(),
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

        thread = data.get("thread", {})
        if not thread:
            return f"未找到主题 ID: {thread_id}"

        msg = "📄 主题详情\n\n"
        msg += f"标题: {thread.get('title', '无标题')}\n"
        msg += f"作者: {thread.get('username', '未知')}\n"
        msg += f"回复数: {thread.get('reply_count', 0)}\n"
        msg += f"浏览数: {thread.get('view_count', 0)}\n"
        
        post_date = thread.get('post_date')
        if post_date:
            msg += f"发布时间: {self._format_timestamp(post_date)}\n"
        
        msg += f"\n{self.xf_url}/threads/{thread_id}/\n"
        
        return msg

    def _fetch_latest_posts_text(self, limit: int = 5) -> str:
        """获取最新回复"""
        try:
            response = requests.get(
                f"{self.xf_url}/api/posts",
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

        posts = data.get("posts", [])
        if not posts:
            return "暂无回复"

        msg = "💬 最新回复：\n\n"
        for p in posts[:limit]:
            thread_id = p.get("thread_id", "")
            post_id = p.get("post_id", "")
            msg += f"• 主题: {p.get('Thread', {}).get('title', '无标题')}\n"
            msg += f"  回复者: {p.get('username', '未知')}\n"
            if thread_id:
                msg += f"  {self.xf_url}/threads/{thread_id}/#post-{post_id}\n\n"
            else:
                msg += "\n"
        return msg

    def _fetch_forum_stats_text(self) -> str:
        """获取论坛统计信息"""
        try:
            response = requests.get(
                f"{self.xf_url}/api/index",
                headers=self._headers(),
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

        msg = "📊 论坛统计\n\n"
        
        # 从返回数据中提取统计信息
        if "boardStats" in data:
            stats = data["boardStats"]
            msg += f"总主题数: {stats.get('messages', 0):,}\n"
            msg += f"总用户数: {stats.get('members', 0):,}\n"
            if "latestMember" in stats:
                msg += f"最新用户: {stats['latestMember'].get('username', '未知')}\n"
        elif "statistics" in data:
            stats = data["statistics"]
            msg += f"总主题数: {stats.get('threads', 0):,}\n"
            msg += f"总回复数: {stats.get('messages', 0):,}\n"
            msg += f"总用户数: {stats.get('users', 0):,}\n"
        else:
            msg += "统计信息不可用"
        
        return msg

    def _fetch_forums_list_text(self) -> str:
        """获取板块列表"""
        try:
            response = requests.get(
                f"{self.xf_url}/api/forums",
                headers=self._headers(),
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

        forums = data.get("forums", [])
        if not forums:
            return "暂无板块"

        msg = "📁 板块列表：\n\n"
        for f in forums:
            forum_id = f.get("node_id", "")
            msg += f"• {f.get('title', '无标题')}\n"
            msg += f"  ID: {forum_id}\n"
            msg += f"  主题数: {f.get('discussion_count', 0)}\n"
            msg += f"  {self.xf_url}/forums/{forum_id}/\n\n"
        return msg

    def _fetch_hot_threads_text(self, limit: int = 5) -> str:
        """获取热门主题"""
        try:
            response = requests.get(
                f"{self.xf_url}/api/threads",
                headers=self._headers(),
                params={
                    "limit": limit * 2,  # 获取更多再筛选
                    "order": "reply_count"
                },
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
            return "暂无热门主题"

        # 按回复数排序
        sorted_threads = sorted(
            threads, 
            key=lambda x: x.get('reply_count', 0), 
            reverse=True
        )

        msg = "🔥 热门主题：\n\n"
        for t in sorted_threads[:limit]:
            thread_id = t.get("thread_id", "")
            msg += f"• {t.get('title', '无标题')}\n"
            msg += f"  作者: {t.get('username', '未知')}\n"
            msg += f"  回复: {t.get('reply_count', 0)} | 浏览: {t.get('view_count', 0)}\n"
            msg += f"  {self.xf_url}/threads/{thread_id}/\n\n"
        return msg

    def _get_help_text(self) -> str:
        """获取帮助信息"""
        msg = "🤖 XenForo 插件命令列表\n\n"
        msg += "📌 基础功能：\n"
        msg += "/论坛 - 获取最新主题列表\n"
        msg += "/用户 [用户名] - 查询用户信息\n"
        msg += "/主题 [ID] - 查看指定主题详情\n"
        msg += "/回复 - 获取最新回复列表\n"
        msg += "/热门 - 查看热门主题\n"
        msg += "/板块 - 查看所有板块列表\n"
        msg += "/统计 - 查看论坛统计数据\n"
        msg += "/帮助 - 显示此帮助信息\n\n"
        msg += "💡 提示：所有命令也可以使用 /xf 前缀\n"
        msg += "例如：/xf 论坛、/xf 用户 张三\n"
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
            msg += f"注册时间: {self._format_timestamp(user.get('register_date'))}\n"
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
    
    @filter.command("主题")
    async def thread_cmd(self, event: AstrMessageEvent, thread_id: str = ""):
        """查看主题详情（/主题 ID）"""
        err = self._ensure_ready()
        if err:
            yield event.plain_result(err)
            return

        thread_id = (thread_id or "").strip()
        if not thread_id:
            raw = self._normalize_text(event.message_str)
            if raw.startswith("主题"):
                thread_id = raw[len("主题") :].strip()

        if not thread_id:
            yield event.plain_result("请输入主题ID，例如：/主题 123")
            return

        try:
            text = await asyncio.to_thread(self._fetch_thread_detail_text, thread_id)
            yield event.plain_result(text)
        except Exception as e:
            logger.error(f"[XenForo] 获取主题失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")

    @filter.command("回复")
    async def posts_cmd(self, event: AstrMessageEvent):
        """获取最新回复（/回复）"""
        err = self._ensure_ready()
        if err:
            yield event.plain_result(err)
            return

        try:
            text = await asyncio.to_thread(
                self._fetch_latest_posts_text,
                limit=5,
            )
            yield event.plain_result(text)
        except Exception as e:
            logger.error(f"[XenForo] 获取回复失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")

    @filter.command("统计")
    async def stats_cmd(self, event: AstrMessageEvent):
        """获取论坛统计（/统计）"""
        err = self._ensure_ready()
        if err:
            yield event.plain_result(err)
            return

        try:
            text = await asyncio.to_thread(self._fetch_forum_stats_text)
            yield event.plain_result(text)
        except Exception as e:
            logger.error(f"[XenForo] 获取统计失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")

    @filter.command("板块")
    async def forums_cmd(self, event: AstrMessageEvent):
        """获取板块列表（/板块）"""
        err = self._ensure_ready()
        if err:
            yield event.plain_result(err)
            return

        try:
            text = await asyncio.to_thread(self._fetch_forums_list_text)
            yield event.plain_result(text)
        except Exception as e:
            logger.error(f"[XenForo] 获取板块失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")

    @filter.command("热门")
    async def hot_cmd(self, event: AstrMessageEvent):
        """获取热门主题（/热门）"""
        err = self._ensure_ready()
        if err:
            yield event.plain_result(err)
            return

        try:
            text = await asyncio.to_thread(
                self._fetch_hot_threads_text,
                limit=5,
            )
            yield event.plain_result(text)
        except Exception as e:
            logger.error(f"[XenForo] 获取热门主题失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")
    
    @filter.command("帮助")
    async def help_cmd(self, event: AstrMessageEvent):
        """显示帮助信息（/帮助）"""
        try:
            text = self._get_help_text()
            yield event.plain_result(text)
        except Exception as e:
            logger.error(f"[XenForo] 获取帮助失败: {e}")
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

    @xf.command("主题")
    async def thread(self, event: AstrMessageEvent, thread_id: str = ""):
        """查看主题详情: xf 主题 ID"""
        err = self._ensure_ready()
        if err:
            yield event.plain_result(err)
            return

        thread_id = (thread_id or "").strip()
        if not thread_id:
            raw = self._normalize_text(event.message_str)
            if raw.startswith("xf 主题"):
                thread_id = raw[len("xf 主题") :].strip()
            elif raw.startswith("xf主题"):
                thread_id = raw[len("xf主题") :].strip()
            elif raw.startswith("主题"):
                thread_id = raw[len("主题") :].strip()

        if not thread_id:
            yield event.plain_result("请输入主题ID，例如：/主题 123")
            return

        try:
            text = await asyncio.to_thread(self._fetch_thread_detail_text, thread_id)
            yield event.plain_result(text)
        except Exception as e:
            logger.error(f"[XenForo] 获取主题失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")

    @xf.command("回复")
    async def posts(self, event: AstrMessageEvent):
        """获取最新回复: xf 回复"""
        err = self._ensure_ready()
        if err:
            yield event.plain_result(err)
            return

        try:
            text = await asyncio.to_thread(
                self._fetch_latest_posts_text,
                limit=5,
            )
            yield event.plain_result(text)
        except Exception as e:
            logger.error(f"[XenForo] 获取回复失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")

    @xf.command("统计")
    async def stats(self, event: AstrMessageEvent):
        """获取论坛统计: xf 统计"""
        err = self._ensure_ready()
        if err:
            yield event.plain_result(err)
            return

        try:
            text = await asyncio.to_thread(self._fetch_forum_stats_text)
            yield event.plain_result(text)
        except Exception as e:
            logger.error(f"[XenForo] 获取统计失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")

    @xf.command("板块")
    async def forums(self, event: AstrMessageEvent):
        """获取板块列表: xf 板块"""
        err = self._ensure_ready()
        if err:
            yield event.plain_result(err)
            return

        try:
            text = await asyncio.to_thread(self._fetch_forums_list_text)
            yield event.plain_result(text)
        except Exception as e:
            logger.error(f"[XenForo] 获取板块失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")

    @xf.command("热门")
    async def hot(self, event: AstrMessageEvent):
        """获取热门主题: xf 热门"""
        err = self._ensure_ready()
        if err:
            yield event.plain_result(err)
            return

        try:
            text = await asyncio.to_thread(
                self._fetch_hot_threads_text,
                limit=5,
            )
            yield event.plain_result(text)
        except Exception as e:
            logger.error(f"[XenForo] 获取热门主题失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")

    @xf.command("帮助")
    async def help(self, event: AstrMessageEvent):
        """显示帮助信息: xf 帮助"""
        try:
            text = self._get_help_text()
            yield event.plain_result(text)
        except Exception as e:
            logger.error(f"[XenForo] 获取帮助失败: {e}")
            yield event.plain_result(f"出错了: {str(e)}")
