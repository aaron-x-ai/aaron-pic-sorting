#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aaron-pic-sorting 配置初始化/重置脚本

使用方式：
  python3 init_config.py --generate \\
      --source_root "/Users/mac/Downloads/IP素材" \\
      --target_root "/Users/mac/Documents/..." \\
      --cron "0 22 * * *" \\
      --enabled true \\
      --work "工作" --life "生活" --default "2026"

  python3 init_config.py --reset    # 删除现有配置，下次进入首次引导
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional

# 确保可以导入 utils
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from utils import ensure_dir, expand_path


def generate_config(
    source_root: str,
    target_root: str,
    cron: str,
    enabled: bool,
    work: str,
    life: str,
    default: str,
    config_path: Optional[str] = None
) -> str:
    """
    生成用户配置文件
    返回生成的文件路径
    """
    if config_path is None:
        config_path = os.path.expanduser("~/.config/aaron-pic-sorting/config.yaml")
    else:
        config_path = os.path.expanduser(config_path)

    ensure_dir(os.path.dirname(config_path))

    enabled_str = "true" if enabled else "false"

    content = f"""# ============================================================
# aaron-pic-sorting 用户配置文件
# 由 init_config.py 生成
# 修改后立即生效，无需重启
# ============================================================

paths:
  source_root: "{source_root}"
  target_root: "{target_root}"
  log_file: "{{source_root}}/aaron-pic-sorting.log"
  fingerprint_db: "~/.config/aaron-pic-sorting/processed.db"

categories:
  mapping:
    work: "{work}"
    life: "{life}"
    default: "{default}"
  hints:
    work: "讲课、会议、商务、PPT、演讲、培训、办公、签约、发布会"
    life: "家庭、旅行、休闲、日常、聚餐、运动、登山、海边"

schedule:
  cron: "{cron}"
  enabled: {enabled_str}
  timezone: "Asia/Shanghai"

processing:
  supported_formats:
    - jpg
    - jpeg
    - png
    - webp
    - gif
    - heic
    - raw
    - tif
    - tiff
  date_priority:
    - exif
    - mtime
    - now
  naming_template: "{{date}}-{{tag1}}-{{tag2}}.{{ext}}"
  conflict_strategy: "rename"
  tags:
    language: "zh"
    max_length: 10
    separator: "-"
  processed_dir:
    name_template: "{{date}}-已处理"
    retention_days: 30

vision:
  model: "default"
  classification_prompt: |
    请分析这张图片，判断它属于以下哪个场景：
    - 工作：商务、讲课、会议、演讲、培训、办公相关
    - 生活：家庭、旅行、休闲、日常、非工作社交
    - 无法判断：内容模糊，无法明确归类
    
    请同时提取2个最贴切的中文标签（每个不超过10个字）。
    
    请以 JSON 格式输出：
    {{
      "category": "work|life|default",
      "tags": ["标签1", "标签2"],
      "confidence": 0.95
    }}

chat:
  trigger_keywords:
    - "整理素材"
    - "整理我的素材"
    - "清华张民素材"
    - "素材整理"
    - "图片分类"
    - "我的IP素材"
    - "设置图片整理"
  cleanup_cache: true
  store_only_keywords:
    - "先放到素材目录"
    - "仅保存不整理"

notification:
  enabled: true
  summary_template: |
    🗂️ 素材整理完成（aaron-pic-sorting）
    ━━━━━━━━━━━━━━━━━━━━
    📁 本次扫描：{{total}} 张
    ✅ 成功整理：{{success}} 张
       └─ 工作：{{work}} 张
       └─ 生活：{{life}} 张
       └─ 2026（兜底）：{{default}} 张
    ⏭️  跳过重复：{{skipped}} 张
    ❌ 处理失败：{{failed}} 张（详见日志）
    🗑️  已清理旧目录：{{cleaned}} 个
    ━━━━━━━━━━━━━━━━━━━━
    📍 日志查看：{{log_path}}
"""

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(content)

    return config_path


def reset_config(config_path: Optional[str] = None) -> bool:
    """
    删除现有配置文件和数据库，返回是否成功
    """
    if config_path is None:
        config_path = os.path.expanduser("~/.config/aaron-pic-sorting/config.yaml")
    else:
        config_path = os.path.expanduser(config_path)

    removed = False
    if os.path.exists(config_path):
        os.remove(config_path)
        removed = True

    # 同时清理数据库
    db_path = os.path.expanduser("~/.config/aaron-pic-sorting/processed.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    return removed


def main():
    parser = argparse.ArgumentParser(description="aaron-pic-sorting 配置管理")
    parser.add_argument("--generate", action="store_true", help="生成配置文件")
    parser.add_argument("--reset", action="store_true", help="删除配置文件，下次重新引导")
    parser.add_argument("--source_root", default="/Users/mac/Downloads/IP素材")
    parser.add_argument("--target_root", default="/Users/mac/Documents/我的个人IP_2026/清华张民IP音频视频图片素材")
    parser.add_argument("--cron", default="0 22 * * *")
    parser.add_argument("--enabled", default="true")
    parser.add_argument("--work", default="工作")
    parser.add_argument("--life", default="生活")
    parser.add_argument("--default", default="2026")
    parser.add_argument("--config", default=None, help="指定配置文件路径")

    args = parser.parse_args()

    if args.reset:
        ok = reset_config(args.config)
        if ok:
            print("RESET_OK")
        else:
            print("RESET_NO_CONFIG")
        return

    if args.generate:
        enabled_bool = args.enabled.lower() in ("true", "1", "yes", "on")
        path = generate_config(
            source_root=args.source_root,
            target_root=args.target_root,
            cron=args.cron,
            enabled=enabled_bool,
            work=args.work,
            life=args.life,
            default=args.default,
            config_path=args.config,
        )
        print(f"GENERATED:{path}")
        return

    # 默认：检查配置是否存在
    config_file = args.config or os.path.expanduser("~/.config/aaron-pic-sorting/config.yaml")
    if os.path.exists(config_file):
        print(f"EXISTS:{config_file}")
    else:
        print("MISSING")


if __name__ == "__main__":
    main()
