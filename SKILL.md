---
name: aaron-pic-sorting
description: "🗂️ 个人IP素材智能整理助手。自动识别图片内容，按「工作/生活/2026」分类归档，规范命名。支持定时整理和聊天即时整理。说'整理素材'开始使用，'配置素材管理'修改设置。"
triggers:
  - "整理素材"
  - "整理我的素材"
  - "清华张民素材"
  - "素材整理"
  - "图片分类"
  - "aaron-pic-sorting"
  - "我的IP素材"
  - "设置图片整理"
  - "配置素材管理"
  - "配置素材整理"
  - "aaron-pic-sorting 配置"
  - "aaron-pic-sorting 初始化"
  - "重置素材整理配置"
  - "aaron-pic-sorting help"
  - "素材整理怎么用"
  - "这个技能是干嘛的"
cron_schedule: "0 22 * * *"
---

# aaron-pic-sorting Skill 工作流文档

## 1. 概述

本 Skill 帮助用户自动整理个人 IP 图片素材，通过 AI Vision 分析图片内容，按「工作 / 生活 / 2026（兜底）」分类归档，并规范重命名。

## 2. 配置检测与分支

每次被触发时，首先检查用户配置文件是否存在：
- **路径**：`~/.config/aaron-pic-sorting/config.yaml`
- **检测方式**：调用 `python3 ~/.hermes/skills/aaron-pic-sorting/scripts/init_config.py`
- **不存在** → 进入「首次引导流程」
- **存在** → 根据触发词进入对应功能

## 3. 首次引导流程（Onboarding）

当用户说以下任意触发词且配置不存在时：
> "整理素材"、"整理我的素材"、"配置素材管理"、"aaron-pic-sorting"

### Step 1: 欢迎说明
AI 发送：
```
👋 欢迎使用 aaron-pic-sorting 素材整理助手！

━━━━━━━━━━━━━━━━━━━━
🎯 我能帮你做什么？
━━━━━━━━━━━━━━━━━━━━

📸 智能分类：自动识别图片内容，按「工作 / 生活 / 2026(兜底)」归档
🏷️ 规范命名：提取中文标签，统一重命名（如：20260405-讲课-清华.jpg）
⏰ 双模触发：每天定时整理 + 聊天发图即时整理
🗂️ 自动归档：处理后的图片有序存放，旧目录自动清理

━━━━━━━━━━━━━━━━━━━━
📖 两种使用方式
━━━━━━━━━━━━━━━━━━━━

方式 A — 定时整理（省心）：
  把图片放到素材目录，每天自动扫描整理

方式 B — 即时整理（灵活）：
  在聊天中发图 + 说"整理素材"，确认后立即处理

━━━━━━━━━━━━━━━━━━━━

首次使用，我需要确认 4 个配置项 👇
```

### Step 2: 确认素材来源目录（source_root）
AI 发送：
```
📁 步骤 1/4：素材来源目录

这是存放「待整理图片」的地方。
你可以直接往这里放图片，也可以让我把聊天里的图片转存到这里。

默认值：
/Users/mac/Downloads/IP素材/

请回复：
• 「确认」使用默认路径
• 或输入新的绝对路径（如 /Volumes/SSD/我的素材/）
```

- 用户说"确认"/"默认" → 记录默认值，验证目录（不存在则询问是否创建）
- 用户输入路径 → 验证路径合法性，记录

### Step 3: 确认整理目标目录（target_root）
AI 发送：
```
📁 步骤 2/4：整理目标目录

整理后的图片会按「工作 / 生活 / 2026」分类存放在这里。

默认值：
/Users/mac/Documents/我的个人IP_2026/清华张民IP音频视频图片素材/

请回复：
• 「确认」使用默认路径
• 或输入新的绝对路径
```

### Step 4: 确认定时触发（schedule）
AI 发送：
```
⏰ 步骤 3/4：定时整理设置

整理助手可以每天自动扫描你的素材目录，无需手动触发。
你希望安排在什么时候？

请直接回复选项编号：

[1] 每天晚上 22:00（推荐，整理当天素材后睡觉）
[2] 每天早上 09:00（起床后查看昨晚的整理结果）
[3] 关闭自动整理（只在我手动说"整理素材"时才处理）
[4] 其他时间（告诉我，如：每天下午3点、每周日晚上8点等）
```

**处理规则**：
- "1"/"确认" → cron="0 22 * * *", enabled=true
- "2" → cron="0 9 * * *", enabled=true
- "3"/"关闭" → enabled=false
- "4"/"其他" → AI 追问具体时间，解析为 Cron 表达式

**追问话术（选"4"时）**：
```
请用日常语言告诉我，例如：
• "每天下午3点"
• "每周日晚上8点"
• "每天晚上11点半"

我会帮你自动转换成系统时间。
```

### Step 5: 确认分类映射（categories）
AI 发送：
```
📂 步骤 4/4：分类目录确认

图片会被智能分类到以下目录：

  工作场景  →  工作/
  生活场景  →  生活/
  我与ai场景 →  我与ai/
  无法判断  →  2026/

请回复：
• 「确认」使用默认分类
• 或输入修改（如："把2026改为其他" 或 "把工作改为商务"）
```

### Step 6: 提示只读信息 + 生成配置
收集完 4 项后，AI 调用脚本生成配置：
```bash
python3 ~/.hermes/skills/aaron-pic-sorting/scripts/init_config.py \
  --generate \
  --source_root "{确认的路径}" \
  --target_root "{确认的路径}" \
  --cron "{cron表达式}" \
  --enabled {true|false} \
  --work "工作" --life "生活" --default "2026"
```

然后 AI 发送：
```
✅ 配置确认完成！正在生成配置文件...

━━━━━━━━━━━━━━━━━━━━
📋 你的配置摘要
━━━━━━━━━━━━━━━━━━━━

素材来源：{source_root}
整理目标：{target_root}
定时整理：{schedule_human_readable}
分类目录：工作 / 生活 / 2026

━━━━━━━━━━━━━━━━━━━━
📝 以下默认设置已生效
━━━━━━━━━━━━━━━━━━━━

📄 日志文件：
   {log_file}
   （每次整理记录都会追加到这里）

🗑️ 已处理目录保留：
   30 天
   （超过 30 天的 "*-已处理" 目录会自动删除）

━━━━━━━━━━━━━━━━━━━━

⚙️ 配置文件已保存至：
   ~/.config/aaron-pic-sorting/config.yaml

如需修改以上设置，随时说"配置素材管理"即可调整，
或说"重置素材整理配置"重新引导。

🎉 现在可以开始使用啦！
   • 直接往素材目录放图片，等定时自动整理
   • 或现在发一张图 + 说"整理素材"试试效果
```

**后台动作**：
- 生成 `~/.config/aaron-pic-sorting/config.yaml`
- 初始化 SQLite 指纹数据库
- 如 enabled=true，创建 Cron Job：`cronjob create` 每天执行本 Skill 的定时工作流

## 4. 配置管理（随时重配）

当用户说以下触发词且配置**已存在**时：
> "配置素材管理"、"配置素材整理"、"aaron-pic-sorting 配置"

### 增量修改模式

AI 发送当前配置：
```
🛠️ 配置管理 — aaron-pic-sorting

当前配置：
  [1] 素材来源目录：{source_root}
  [2] 整理目标目录：{target_root}
  [3] 定时整理：{schedule_status}
  [4] 分类目录：{work} / {life} / {ai_me} / {default}

请回复编号修改对应项，或：
  • 「确认」退出配置管理
  • 「重置」删除配置并重新引导
  • 「查看」显示完整配置文件内容
```

**处理规则**：
- 用户说"1" → 询问新的 source_root，验证后调用 `init_config.py --generate` 更新
- 用户说"2" → 询问新的 target_root，更新
- 用户说"3" → 重新展示定时选项，更新
- 用户说"4" → 重新展示分类选项，更新
- "确认"/"退出" → 保存当前配置，退出
- "重置" → 调用 `init_config.py --reset`，提示用户说"整理素材"重新走首次引导
- "查看" → 用代码块展示 `~/.config/aaron-pic-sorting/config.yaml` 全文

**注意**：每次修改后调用 `init_config.py --generate` 重新生成完整配置文件，保留用户未修改项的当前值。

## 5. 日常整理工作流（手动触发）

用户说："整理素材"、"整理我的素材" 等日常触发词，且配置已存在。

### 5.1 扫描阶段
调用：
```bash
python3 ~/.hermes/skills/aaron-pic-sorting/scripts/process.py scan
```

**输出示例**：
```json
{
  "source_root": "/Users/mac/Downloads/IP素材",
  "files": [
    {
      "source_path": "/Users/mac/Downloads/IP素材/IMG_001.jpg",
      "rel_path": "IMG_001.jpg",
      "md5": "abc123...",
      "date_candidates": {
        "exif": "2026:04:05",
        "mtime": "2026-04-06"
      },
      "format": "jpg"
    }
  ],
  "skipped_duplicates": 0,
  "total_scanned": 1
}
```

### 5.2 Vision 分析阶段
对 `files` 中每个文件，按顺序执行：

1. **调用 `vision_analyze`** 分析图片内容
2. **确定日期**：根据 `date_candidates` 和配置优先级（exif → mtime → now）
3. **确定分类**：根据 Vision 结果映射到 `work`/`life`/`default`
4. **提取标签**：2 个中文标签，过滤非法字符

### 5.3 构建 batch JSON
将分析结果写入临时文件 `/tmp/aaron-pic-sorting-batch.json`：
```json
[
  {
    "source_path": "/Users/mac/Downloads/IP素材/IMG_001.jpg",
    "md5": "abc123...",
    "category": "work",
    "tags": ["讲课", "清华"],
    "date": "20260405"
  }
]
```

### 5.4 执行整理
调用：
```bash
python3 ~/.hermes/skills/aaron-pic-sorting/scripts/process.py organize \
  --batch /tmp/aaron-pic-sorting-batch.json
```

### 5.5 清理旧目录
调用：
```bash
python3 ~/.hermes/skills/aaron-pic-sorting/scripts/process.py cleanup
```

### 5.6 生成汇总
调用：
```bash
python3 ~/.hermes/skills/aaron-pic-sorting/scripts/process.py summary --today
```

读取 `templates/summary.template`，替换变量后发送给用户。

**汇总消息示例**：
```
🗂️ 素材整理完成（aaron-pic-sorting）
━━━━━━━━━━━━━━━━━━━━
📁 本次扫描：3 张
✅ 成功整理：2 张
   └─ 工作：1 张
   └─ 生活：1 张
   └─ 我与ai：0 张
   └─ 2026（兜底）：0 张
⏭️  跳过重复：1 张
❌ 处理失败：0 张（详见日志）
🗑️  已清理旧目录：0 个
━━━━━━━━━━━━━━━━━━━━
📍 日志查看：/Users/mac/Downloads/IP素材/aaron-pic-sorting.log
```

## 6. 聊天图片即时整理工作流

用户**发图 + 说触发词**（如"整理这张素材"）。

### 6.1 意图识别
AI 识别到"图片 + 触发关键词"，询问用户：
```
检测到素材图片，是否立即使用 aaron-pic-sorting skill 整理？

请回复：
• 「确认」立即整理
• 「仅保存」把图片放到素材目录，等定时任务处理
• 「取消」不处理
```

### 6.2 用户确认「立即整理」
1. **转存图片**：将聊天图片保存到 `source_root/`
2. **清理缓存**：如配置 `cleanup_cache=true`，清理通信软件缓存
3. **执行单张整理**：
   - 计算 MD5，检查是否已处理
   - 调用 `vision_analyze` 分析
   - 构建单条 batch JSON
   - 调用 `process.py organize --batch`
4. **发送汇总**：告知用户整理结果

### 6.3 用户选择「仅保存」
1. 转存图片到 `source_root/`
2. 清理缓存（如配置开启）
3. AI 回复："已保存到素材目录，将在定时任务中整理"

### 6.4 用户说「先放到素材目录」等 store_only_keywords
直接执行 6.3 流程，无需再次询问。

## 7. 定时整理工作流（Cron）

当 Cron 触发时（默认每天 22:00），AI 执行以下工作流：

1. **加载配置**
2. **调用 `process.py scan`** 获取待处理文件列表
3. **循环调用 `vision_analyze`** 分析每张图片
4. **构建 batch JSON**
5. **调用 `process.py organize`** 执行整理
6. **调用 `process.py cleanup`** 清理旧目录
7. **调用 `process.py summary --today`** 获取统计
8. **格式化汇总消息**，通过 cronjob deliver 发送给用户（如配置 `origin`）

**注意**：Cron 模式下如无新素材，汇总消息显示"本次无新素材"。

## 8. 帮助与发现

当用户说以下任意词时：
> "aaron-pic-sorting help"、"素材整理怎么用"、"这个技能是干嘛的"、"aaron-pic-sorting"

AI 发送帮助信息：
```
🗂️ aaron-pic-sorting 素材整理助手

━━━━━━━━━━━━━━━━━━━━
📖 功能简介
━━━━━━━━━━━━━━━━━━━━

自动识别图片内容，按「工作 / 生活 / 2026」分类归档，
并规范重命名为：20260405-讲课-清华.jpg

━━━━━━━━━━━━━━━━━━━━
🚀 使用方法
━━━━━━━━━━━━━━━━━━━━

【日常整理】
  • "整理素材" — 手动触发整理
  • 发一张图 + 说"整理这张" — 单张即时整理
  • "先放到素材目录" — 仅保存图片，等定时任务处理

【配置管理】
  • "配置素材管理" — 修改目录、时间、分类等设置
  • "重置素材整理配置" — 恢复默认，重新配置

【其他】
  • 每天定时自动整理（默认 22:00，可配置）

━━━━━━━━━━━━━━━━━━━━
📁 当前配置路径
━━━━━━━━━━━━━━━━━━━━
  素材来源：{source_root}
  整理目标：{target_root}
  定时整理：{schedule_status}
  配置文件：~/.config/aaron-pic-sorting/config.yaml
```

## 9. 故障排除

### 9.1 vision_analyze 连接失败（Connection error）

**现象**：调用 `vision_analyze` 时返回 `Error analyzing image: Connection error.`

**常见原因**：用户机器运行了代理软件（如 Clash/FlClash/V2Ray），但 AI 工具的 API 请求未走代理。

**诊断步骤**：
```bash
# 1. 测试直接访问国际站点（预期超时或失败）
curl -s https://www.google.com

# 2. 检查本地代理进程
ps aux | grep -i "clash\|v2ray\|surge"

# 3. 找到代理监听端口
lsof -p <PID> | grep LISTEN
# 常见端口：7890(Clash), 1080(SOCKS), 8080

# 4. 测试走代理是否成功
HTTPS_PROXY=http://127.0.0.1:7890 curl -s https://www.google.com
```

**解决方案**：
- **临时方案**：在执行整理前设置环境变量
  ```bash
  export HTTP_PROXY=http://127.0.0.1:7890
  export HTTPS_PROXY=http://127.0.0.1:7890
  ```
- **长期方案**：开启代理软件的「系统代理」或「TUN 模式」
- **Skill 增强**：在 `process.py` 中自动检测常见代理端口并设置环境变量

### 9.2 GitHub Push 失败（认证错误）

**现象**：`git push` 提示 `could not read Username for 'https://github.com'`

**原因**：未配置 GitHub 认证（无 Token 或 SSH Key 未添加）

**解决方案**：
```bash
# 方案 A：使用 SSH（推荐）
# 1. 检查现有密钥
ls ~/.ssh/id_*.pub

# 2. 复制公钥内容
cat ~/.ssh/id_ed25519.pub

# 3. 粘贴到 https://github.com/settings/keys → New SSH key

# 4. 切换远程地址为 SSH
git remote set-url origin git@github.com:<user>/<repo>.git

# 5. 推送
git push -u origin main
```

## 10. 错误处理

| 场景 | 处理方式 |
|------|----------|
| 配置不存在 | 进入首次引导流程 |
| 源目录不存在 | 提示用户创建目录，或询问是否使用新路径 |
| Vision 分析失败 | 跳过该图，记录 ERROR 日志，继续处理其余图片 |
| 目标目录不可写 | 报错并终止，提示检查权限 |
| 文件移动失败 | 记录 ERROR，跳过该文件 |
| batch JSON 格式错误 | 报错，不执行任何文件操作 |
| 无新素材可整理 | 正常结束，汇总显示"本次无新素材" |

## 10. 依赖

- Python 3.8+
- `pyyaml`（YAML 解析）
- `Pillow`（可选，用于 EXIF 日期提取）
- SQLite3（Python 内置）

## 11. 文件清单

```
~/.hermes/skills/aaron-pic-sorting/
├── SKILL.md                          # 本文档
├── README.md                         # 用户安装指南
├── config/
│   └── config.default.yaml           # 默认配置模板
├── scripts/
│   ├── init_config.py                # 配置初始化/重置
│   ├── process.py                    # 核心处理（scan/organize/cleanup/summary）
│   └── utils.py                      # 公共工具函数
└── templates/
    └── summary.template              # 汇总消息模板
```
