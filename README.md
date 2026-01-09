# XenForo-AstrBot 集成插件

将 XenForo 论坛与 QQ 群（通过 AstrBot + NapCat）无缝连接。

## 功能特性

### 🤖 QQ 命令（QQ → XenForo）
- **/论坛** - 查看最新主题列表
- **/用户 [用户名]** - 查看用户详细信息
- **/主题 [ID]** - 查看指定主题详情
- **/回复** - 查看最新回复列表
- **/热门** - 查看热门主题
- **/板块** - 查看所有板块列表
- **/统计** - 查看论坛统计数据
- **/帮助** - 显示所有可用命令

> 💡 所有命令也支持 `/xf` 前缀，例如：`/xf 论坛`、`/xf 用户 张三`

---

## 安装步骤

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

3. 编辑配置文件 `config.json`（见下方配置说明）

---

## 配置说明

### AstrBot 插件配置

**方式一：使用配置文件（推荐）**

编辑 `config.json` 文件：

```json
{
  "xf_url": "https://your-forum.com",
  "xf_api_key": "your_api_key_here",
  "threads_limit": 5,
  "request_timeout": 10,
  "require_slash": true
}
```

**配置项说明：**

| 配置项 | 必填 | 说明 | 示例 |
|--------|------|------|------|
| `xf_url` | ✅ | XenForo 站点地址（不要结尾斜杠） | `https://oksgo.com` |
| `xf_api_key` | ✅ | XenForo API 密钥 | `xf_api_xxx...` |
| `threads_limit` | ❌ | 获取主题列表的数量 | `5`（默认） |
| `request_timeout` | ❌ | API 请求超时时间（秒） | `10`（默认） |
| `require_slash` | ❌ | 是否要求命令以 / 开头 | `true`（默认） |

**方式二：使用 AstrBot WebUI**

在 AstrBot WebUI → 插件 → XenForo → 配置页面直接配置（如果支持）

**获取 XenForo API 密钥：**
1. 登录 XenForo 管理后台 → **设置** → **API 密钥** → 点击 **添加 API 密钥**。
2. 在“密钥类型”中选择 **游客密钥**，填写一个标题（例如 AstrBot）。
3. 在“允许 scopes”里勾选所需的数据访问（至少 `thread:read`, `post:read`, `forum:read`, `user:read`）。
4. 保存后复制生成的密钥（格式形如 `xf_api_xxx...`），并填入 `config.json` 的 `xf_api_key` 字段。

---

### 测试 QQ 命令

在 QQ 群发送：
```
/论坛
```

应该返回最新主题列表。

---

## 常见问题

### 测试 QQ 命令

在 QQ 群发送：
```
/帮助
```
应该会返回所有可用命令列表。

再测试其他命令：
```
/论坛
/统计
/热门
```

如果命令无响应，检查：
1. `config.json` 中的 `xf_url` 和 `xf_api_key` 是否配置正确
2. AstrBot 是否重启生效
3. AstrBot 日志中是否有错误信息

---

## 常见问题

### Q: 配置文件在哪里？
**A:** 配置文件位于插件目录下的 `config.json`，通常在：
- `/你的AstrBot路径/data/plugins/xenforo/config.json`

### Q: 修改配置后不生效？
**A:** 重启 AstrBot 使配置生效：
```bash
pm2 restart AstrBot
# 或
systemctl restart astrbot
```

### Q: QQ 命令无响应？
**A:** 检查：
1. `xf_url` 和 `xf_api_key` 是否配置正确
2. XenForo API 是否启用（访问 `https://你的论坛.com/api/` 测试）
3. 防火墙是否拦截了 API 请求
4. AstrBot 日志中是否有错误信息

---

## 系统要求

- **XenForo**: 2.3.0 或更高版本
- **AstrBot**: 4.11.0 或更高版本
- **Python**: 3.11 或更高版本

---

## 更新日志

### v1.0.2 (2026-01-09)
- 📝 添加配置文件模板，简化安装流程
- 📝 完善 README 文档说明

### v1.0.1 (2026-01-09)
- ✨ 新增功能：主题详情、最新回复、热门主题、板块列表、论坛统计
- ✨ 新增帮助命令，显示所有可用命令
- 🐛 修复用户注册时间显示为时间戳的问题
- 📝 优化配置文件说明

### v1.0.0 (2026-01-09)
- ✨ 首次发布
- 支持查询最新主题和用户信息
- ✅ XenForo → QQ 自动通知
- ✅ QQ 命令查询论坛数据
- ✅ XFRM 资源通知支持
- ✅ WebUI 配置界面

---

## 开源协议

MIT License

---

## 鸣谢

- [HuoNiu Team](https://oksgo.com/) - 本插件作者
- [XenForo](https://xenforo.com/) - 强大的论坛系统
- [AstrBot](https://github.com/Soulter/AstrBot) - 优秀的 QQ 机器人框架

---

**制作：HuoNiu Team | [访问论坛](https://oksgo.com/)**
