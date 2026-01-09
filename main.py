from astrbot.api import star
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.core.message.message_event_result import MessageEventResult, EventResultType
from astrbot.core.message.components import Plain
import requests
from typing import Dict, Any
import asyncio
from quart import request, jsonify
import json
import os


class Main(star.Star):
    def __init__(self, context: star.Context) -> None:
        self.context = context
        
        # 加载配置（使用基础方式）
        self.cfg = self.load_config()
        
        # 注册 HTTP 路由接收 XenForo 通知
        self.register_http_routes()
    
    def load_config(self):
        """加载配置文件"""
        config_path = self.context.get_config_path("config.json")
        default_config = {
            "xf_url": "https://oksgo.com",
            "xf_api_key": "Kwcc3l7mDuLeCzuLJnibJklJjzhxd3l_",
            "qq_group_id": 5977983,
            "napcat_url": "http://localhost:3001",
            "astrbot_token": "AstrBot1234567890"
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return type('Config', (), config)()
            else:
                # 创建默认配置文件
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                return type('Config', (), default_config)()
        except Exception as e:
            print(f"[XenForo] 配置加载失败: {e}")
            return type('Config', (), default_config)()
    
    def register_http_routes(self):
        """注册 HTTP 路由接收 XenForo 推送"""
        # 获取 AstrBot 的 dashboard app
        dashboard_app = self.context.get_dashboard_app()
        
        @dashboard_app.route("/xenforo/notify", methods=["POST"])
        async def handle_xenforo_notification():
            """接收 XenForo 发来的通知"""
            try:
                data = await request.get_json()
                
                # 验证 API 密钥
                api_key = request.headers.get("X-API-Key")
                
                if api_key != self.cfg.astrbot_token:
                    return jsonify({"success": False, "error": "Invalid API key"}), 401
                
                # 发送到 QQ 群
                message = data.get("message", "")
                if message:
                    await self.send_to_qq(message)
                
                return jsonify({"success": True}), 200
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
    
    async def send_to_qq(self, message: str):
        """发送消息到 QQ 群（通过 NapCat）"""
        try:
            url = f"{self.cfg.napcat_url}/send_group_msg"
            payload = {
                "group_id": self.cfg.qq_group_id,
                "message": message
            }
            response = requests.post(url, json=payload, timeout=5)
            print(f"[XenForo] 发送通知到QQ群: {response.status_code}")
        except Exception as e:
            print(f"[XenForo] 发送到 QQ 失败: {e}")
    
    @filter.command("论坛")
    async def forum(self, event: AstrMessageEvent):
        """查看最新论坛主题"""
        await self.get_latest_threads(event)
    
    @filter.command("搜索")
    async def search(self, event: AstrMessageEvent):
        """搜索论坛主题：搜索 关键词"""
        keyword = event.message_str.replace("搜索", "").strip()
        if keyword:
            await self.search_threads(event, keyword)
        else:
            await event.reply("请输入搜索关键词，例如：搜索 Python")
    
    @filter.command("用户")
    async def user(self, event: AstrMessageEvent):
        """查看用户信息：用户 用户名"""
        username = event.message_str.replace("用户", "").strip()
        if username:
            await self.get_user_info(event, username)
        else:
            await event.reply("请输入用户名，例如：用户 张三")
    
    async def get_latest_threads(self, event: AstrMessageEvent):
        """获取最新主题"""
        try:
            headers = {
                "XF-Api-Key": self.cfg.xf_api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.cfg.xf_url}/api/threads",
                headers=headers,
                params={"order": "post_date", "direction": "desc", "limit": 5},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                threads = data.get("threads", [])
                
                if not threads:
                    await event.reply("暂无主题")
                    return
                
                msg = "📌 最新主题：\n\n"
                for t in threads:
                    msg += f"• {t['title']}\n"
                    msg += f"  作者: {t.get('username', '未知')}\n"
                    msg += f"  链接: {self.cfg.xf_url}/threads/{t['thread_id']}/\n\n"
                
                await event.reply(msg)
            else:
                await event.reply(f"查询失败: {response.status_code}")
        except Exception as e:
            await event.reply(f"错误: {str(e)}")
    
    async def search_threads(self, event: AstrMessageEvent, keyword: str):
        """搜索主题"""
        try:
            headers = {
                "XF-Api-Key": self.cfg.xf_api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.cfg.xf_url}/api/threads/search",
                headers=headers,
                params={"q": keyword, "limit": 5},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                if not results:
                    await event.reply(f"未找到包含 '{keyword}' 的主题")
                    return
                
                msg = f"🔍 搜索结果：{keyword}\n\n"
                for r in results:
                    msg += f"• {r['title']}\n"
                    msg += f"  链接: {self.cfg.xf_url}/threads/{r['thread_id']}/\n\n"
                
                await event.reply(msg)
            else:
                await event.reply(f"搜索失败: {response.status_code}")
        except Exception as e:
            await event.reply(f"错误: {str(e)}")
    
    async def get_user_info(self, event: AstrMessageEvent, username: str):
        """获取用户信息"""
        try:
            headers = {
                "XF-Api-Key": self.cfg.xf_api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.cfg.xf_url}/api/users/find",
                headers=headers,
                params={"username": username},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                user = data.get("user")
                
                if not user:
                    await event.reply(f"未找到用户: {username}")
                    return
                
                msg = f"👤 用户信息：\n"
                msg += f"用户名: {user.get('username')}\n"
                msg += f"注册时间: {user.get('register_date', '未知')}\n"
                msg += f"帖子数: {user.get('message_count', 0)}\n"
                msg += f"反应分: {user.get('reaction_score', 0)}\n"
                
                await event.reply(msg)
            else:
                await event.reply(f"查询失败: {response.status_code}")
        except Exception as e:
            await event.reply(f"错误: {str(e)}")
