# XenForo-AstrBot 集成插件

将 XenForo 论坛与 QQ 群（通过 AstrBot + NapCat）无缝连接。

## 功能特性

### 🔔 自动通知（XenForo → QQ）
- ✅ 新主题发布通知
- ✅ 帖子回复通知  
- ✅ 用户注册通知
- ✅ 资源发布/更新通知（支持 XFRM）
- ✅ 主题删除通知

### 🤖 QQ 命令（QQ → XenForo）
- **/论坛** - 查看最新主题列表
- **/搜索 关键词** - 搜索论坛主题
- **/用户 用户名** - 查看用户详细信息

---

## 安装步骤

### 第一步：安装 XenForo 插件

1. 下载 `HuoNiu-QQNotif-1.0.0.zip`
2. 进入 XenForo 管理后台 → **添加ons** → **安装插件**
3. 上传 ZIP 文件并安装

### 第二步：安装 AstrBot 插件

1. 将 `xenforo` 文件夹上传到 AstrBot 插件目录：
   ```bash
   /你的AstrBot路径/data/plugins/xenforo/
   ```

2. 重启 AstrBot：
   ```bash
   pm2 restart AstrBot
   # 或
   systemctl restart astrbot
   ```

3. 在 AstrBot WebUI 中进入 **插件** 页面，找到 **XenForo**，点击配置

---

## 配置说明

### AstrBot 插件配置

在 AstrBot WebUI → 插件 → XenForo → 配置：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| **XenForo 站点地址** | 你的论坛完整 URL | `https://your-forum.com` |
| **XenForo API 密钥** | 从 XF 后台生成的 API 密钥 | `xf_api_xxx...` |
| **QQ 群号** | 接收通知的 QQ 群 | `123456789` |
| **NapCat API 地址** | NapCat HTTP API 地址 | `http://localhost:3001` |
| **AstrBot API 密钥** | XF 回调验证密钥 | `AstrBot1234567890` |

**获取 XenForo API 密钥：**
1. XF 管理后台 → **Setup** → **API keys**
2. 点击 **Add API key**
3. 选择 **Super User Key**
4. 勾选权限：`thread:read`, `thread:write`, `post:read`, `user:read`
5. 保存后复制生成的密钥

### XenForo 插件配置

在 XenForo 管理后台 → **HuoNiu QQ通知**：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| **AstrBot URL** | AstrBot HTTP 地址 | `http://127.0.0.1:6185` |
| **AstrBot API 密钥** | 与 AstrBot 插件配置中的密钥一致 | `AstrBot1234567890` |
| **目标 QQ 群号** | 同上 | `123456789` |
| **启用回复通知** | ☑️ | |
| **启用注册通知** | ☑️ | |
| **启用资源通知** | ☑️（需要安装 XFRM）| |
| **监听的版块 ID** | 逗号分隔，留空监听全部 | `1,2,3` |
| **通知日志保留天数** | 自动清理旧日志 | `30` |

---

## 测试验证

### 1. 测试 XenForo → QQ 通知

1. 点击 XF 配置页面的 **测试连接** 按钮
2. 在论坛发布一个测试帖子
3. 检查 QQ 群是否收到通知

### 2. 测试 QQ 命令

在 QQ 群发送：
```
/论坛
```

应该返回最新主题列表。

---

## 常见问题

### Q: 插件已加载但配置界面显示"这个插件没有配置"？
**A:** 检查 `main.py` 是否包含 `Config` 类定义，重启 AstrBot 后刷新页面。

### Q: XenForo 发帖后 QQ 群没有收到通知？
**A:** 检查：
1. XF 后台配置的 AstrBot URL 是否正确
2. AstrBot API 密钥是否一致
3. AstrBot 和 NapCat 是否正常运行
4. 查看 XF 通知日志（后台 → HuoNiu QQ通知 → 查看日志）

### Q: QQ 命令无响应？
**A:** 检查：
1. QQ 群号是否配置正确
2. NapCat 是否正常运行（`pm2 list` 查看状态）
3. XenForo API 密钥是否正确
4. AstrBot 日志中是否有错误

### Q: NapCat 端口是 3000 还是 3001？
**A:** 取决于你的 NapCat 启动参数，常见端口是 3001。使用 `netstat -tuln | grep 300` 查看实际端口。

---

## 系统要求

- **XenForo**: 2.2.0 或更高版本
- **AstrBot**: 4.11.0 或更高版本
- **NapCat**: 任意版本（支持 OneBot 11 协议）
- **PHP**: 8.0 或更高版本
- **Python**: 3.11 或更高版本

---

## 技术支持

- GitHub Issues: [项目地址]
- 论坛: [你的论坛地址]
- QQ 群: [支持群号]

---

## 更新日志

### v1.0.0 (2026-01-09)
- ✨ 首次发布
- ✅ XenForo → QQ 自动通知
- ✅ QQ 命令查询论坛数据
- ✅ XFRM 资源通知支持
- ✅ WebUI 配置界面

---

## 开源协议

MIT License

---

## 鸣谢

- [XenForo](https://xenforo.com/) - 强大的论坛系统
- [AstrBot](https://github.com/Soulter/AstrBot) - 优秀的 QQ 机器人框架
- [NapCat](https://github.com/NapNeko/NapCatQQ) - QQ OneBot 实现

---

**制作：HuoNiu Team**
