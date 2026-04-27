#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aaron-pic-sorting 核心处理脚本

子命令：
  scan        扫描源目录，输出待处理文件 JSON
  organize    根据 AI 分析结果执行整理
  cleanup     清理超期已处理目录
  summary     读取日志生成汇总统计
  check       检查配置是否存在且有效

使用示例：
  python3 process.py scan --config ~/.config/aaron-pic-sorting/config.yaml
  python3 process.py organize --batch results.json
  python3 process.py cleanup
  python3 process.py summary
"""

import os
import sys
import json
import argparse
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Any

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from utils import (
    load_config,
    expand_path,
    ensure_dir,
    compute_md5,
    init_db,
    is_processed,
    mark_processed,
    get_date_candidates,
    resolve_date,
    sanitize_filename,
    get_supported_files,
    write_log,
    cleanup_old_processed_dirs,
    build_target_filename,
    check_config_exists,
)


def cmd_check(args) -> int:
    """检查配置状态"""
    exists = check_config_exists(args.config)
    if exists:
        try:
            cfg = load_config(args.config)
            src = cfg.get("paths", {}).get("source_root", "")
            tgt = cfg.get("paths", {}).get("target_root", "")
            print(f"CONFIG_OK")
            print(f"source_root:{src}")
            print(f"target_root:{tgt}")
            return 0
        except Exception as e:
            print(f"CONFIG_INVALID:{e}")
            return 1
    else:
        print("CONFIG_MISSING")
        return 1


def cmd_scan(args) -> int:
    """
    扫描源目录，输出待处理文件列表 JSON
    """
    if not check_config_exists(args.config):
        print(json.dumps({"error": "CONFIG_MISSING"}, ensure_ascii=False))
        return 1

    cfg = load_config(args.config)
    source_root = cfg.get("paths", {}).get("source_root", "")
    supported = cfg.get("processing", {}).get("supported_formats", [])
    db_path = cfg.get("paths", {}).get("fingerprint_db", "")

    if not os.path.exists(source_root):
        print(json.dumps({"error": "SOURCE_NOT_FOUND", "path": source_root}, ensure_ascii=False))
        return 1

    conn = init_db(db_path)
    files = get_supported_files(source_root, supported)

    pending = []
    skipped = 0
    for fpath in files:
        md5 = compute_md5(fpath)
        if is_processed(conn, md5):
            skipped += 1
            continue
        dates = get_date_candidates(fpath)
        pending.append({
            "source_path": fpath,
            "rel_path": os.path.basename(fpath),
            "md5": md5,
            "date_candidates": dates,
            "format": os.path.splitext(fpath)[1].lower().lstrip(".")
        })

    result = {
        "source_root": source_root,
        "files": pending,
        "skipped_duplicates": skipped,
        "total_scanned": len(files),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    conn.close()
    return 0


def cmd_organize(args) -> int:
    """
    根据 AI 分析结果执行整理
    batch.json 格式：
    [
      {
        "source_path": "...",
        "md5": "...",
        "category": "work|life|default",
        "tags": ["标签1", "标签2"],
        "date": "20260405"
      }
    ]
    """
    if not check_config_exists(args.config):
        print(json.dumps({"error": "CONFIG_MISSING"}, ensure_ascii=False))
        return 1

    cfg = load_config(args.config)
    source_root = cfg.get("paths", {}).get("source_root", "")
    target_root = cfg.get("paths", {}).get("target_root", "")
    db_path = cfg.get("paths", {}).get("fingerprint_db", "")
    log_file = cfg.get("paths", {}).get("log_file", "")
    naming_tpl = cfg.get("processing", {}).get("naming_template", "{date}-{tag1}-{tag2}.{ext}")
    conflict = cfg.get("processing", {}).get("conflict_strategy", "rename")
    sep = cfg.get("processing", {}).get("tags", {}).get("separator", "-")
    cat_map = cfg.get("categories", {}).get("mapping", {})
    processed_dir_tpl = cfg.get("processing", {}).get("processed_dir", {}).get("name_template", "{date}-已处理")

    # 读取 batch
    batch_path = args.batch
    if not batch_path or not os.path.exists(batch_path):
        print(json.dumps({"error": "BATCH_FILE_MISSING"}, ensure_ascii=False))
        return 1

    with open(batch_path, "r", encoding="utf-8") as f:
        batch = json.load(f)

    if not isinstance(batch, list):
        print(json.dumps({"error": "BATCH_MUST_BE_LIST"}, ensure_ascii=False))
        return 1

    conn = init_db(db_path)
    stats = {"success": 0, "skipped": 0, "failed": 0, "work": 0, "life": 0, "ai_me": 0, "default": 0}

    for item in batch:
        src = item.get("source_path", "")
        md5 = item.get("md5", "")
        category_key = item.get("category", "default")
        tags = item.get("tags", [])
        date_str = item.get("date", "")

        if not os.path.exists(src):
            write_log(log_file, "ERROR", os.path.basename(src), "源文件不存在")
            stats["failed"] += 1
            continue

        # 重新校验 MD5（防止并发处理）
        actual_md5 = compute_md5(src)
        if actual_md5 != md5 or is_processed(conn, actual_md5):
            write_log(log_file, "SKIP", os.path.basename(src), "MD5已存在或不匹配")
            stats["skipped"] += 1
            continue

        # 确定分类目录
        folder_name = cat_map.get(category_key, cat_map.get("default", "2026"))
        target_dir = os.path.join(target_root, folder_name)
        ensure_dir(target_dir)

        # 标签
        tag1 = sanitize_filename(tags[0] if len(tags) > 0 else "未知", sep)
        tag2 = sanitize_filename(tags[1] if len(tags) > 1 else "未知", sep)

        # 构建文件名
        ext = os.path.splitext(src)[1].lower()
        target_name = build_target_filename(date_str, tag1, tag2, ext, naming_tpl)
        target_path = os.path.join(target_dir, target_name)

        # 冲突处理
        if os.path.exists(target_path):
            if conflict == "skip":
                write_log(log_file, "SKIP", os.path.basename(src), f"目标已存在:{target_name}")
                stats["skipped"] += 1
                continue
            elif conflict == "rename":
                base, e = os.path.splitext(target_name)
                counter = 1
                new_target_path = target_path
                while os.path.exists(new_target_path):
                    new_name = f"{base}_{counter}{e}"
                    new_target_path = os.path.join(target_dir, new_name)
                    counter += 1
                target_path = new_target_path
                target_name = os.path.basename(target_path)
            elif conflict == "overwrite":
                pass  # 直接覆盖

        try:
            # 复制到目标
            shutil.copy2(src, target_path)
            # 移动原文件到已处理目录
            processed_dir_name = processed_dir_tpl.format(date=date_str)
            processed_dir = os.path.join(source_root, processed_dir_name)
            ensure_dir(processed_dir)
            shutil.move(src, os.path.join(processed_dir, os.path.basename(src)))
            # 记录去重
            mark_processed(conn, actual_md5, src, target_path)
            # 日志
            write_log(log_file, "SUCCESS", os.path.basename(src), f"分类:{folder_name} | 目标:{target_name}")
            stats["success"] += 1
            if category_key == "work":
                stats["work"] += 1
            elif category_key == "life":
                stats["life"] += 1
            elif category_key == "ai_me":
                stats["ai_me"] += 1
            else:
                stats["default"] += 1
        except Exception as e:
            write_log(log_file, "ERROR", os.path.basename(src), f"处理异常:{e}")
            stats["failed"] += 1

    conn.close()
    print(json.dumps({"status": "DONE", "stats": stats}, ensure_ascii=False))
    return 0


def cmd_cleanup(args) -> int:
    """清理超期已处理目录"""
    if not check_config_exists(args.config):
        print(json.dumps({"error": "CONFIG_MISSING"}, ensure_ascii=False))
        return 1

    cfg = load_config(args.config)
    source_root = cfg.get("paths", {}).get("source_root", "")
    log_file = cfg.get("paths", {}).get("log_file", "")
    retention = cfg.get("processing", {}).get("processed_dir", {}).get("retention_days", 30)

    cleaned = cleanup_old_processed_dirs(source_root, retention, log_file)
    print(json.dumps({"cleaned": cleaned}, ensure_ascii=False))
    return 0


def cmd_summary(args) -> int:
    """
    从日志文件解析当次/历史统计
    如果指定 --today ，只统计今天
    """
    if not check_config_exists(args.config):
        print(json.dumps({"error": "CONFIG_MISSING"}, ensure_ascii=False))
        return 1

    cfg = load_config(args.config)
    log_file = cfg.get("paths", {}).get("log_file", "")

    stats = {
        "total": 0,
        "success": 0,
        "skipped": 0,
        "failed": 0,
        "work": 0,
        "life": 0,
        "ai_me": 0,
        "default": 0,
        "cleaned": 0,
        "log_path": log_file,
    }

    if not os.path.exists(log_file):
        print(json.dumps(stats, ensure_ascii=False))
        return 0

    today_str = None
    if args.today:
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")

    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # 如果指定今天，过滤
            if today_str and not line.startswith(f"[{today_str}"):
                continue

            stats["total"] += 1
            if "SUCCESS" in line:
                stats["success"] += 1
                if "分类:工作" in line:
                    stats["work"] += 1
                elif "分类:生活" in line:
                    stats["life"] += 1
                elif "分类:我与ai" in line:
                    stats["ai_me"] += 1
                elif "分类:2026" in line:
                    stats["default"] += 1
            elif "SKIP" in line:
                stats["skipped"] += 1
            elif "ERROR" in line:
                stats["failed"] += 1
            elif "CLEAN" in line:
                stats["cleaned"] += 1

    print(json.dumps(stats, ensure_ascii=False))
    return 0


def main():
    parser = argparse.ArgumentParser(description="aaron-pic-sorting 处理脚本")
    parser.add_argument("--config", default=None, help="配置文件路径")
    sub = parser.add_subparsers(dest="command")

    p_check = sub.add_parser("check", help="检查配置")

    p_scan = sub.add_parser("scan", help="扫描源目录")

    p_org = sub.add_parser("organize", help="执行整理")
    p_org.add_argument("--batch", required=True, help="AI 分析结果 JSON 文件路径")

    p_clean = sub.add_parser("cleanup", help="清理旧目录")

    p_sum = sub.add_parser("summary", help="汇总统计")
    p_sum.add_argument("--today", action="store_true", help="只统计今天")

    args = parser.parse_args()

    if args.command == "check":
        return cmd_check(args)
    elif args.command == "scan":
        return cmd_scan(args)
    elif args.command == "organize":
        return cmd_organize(args)
    elif args.command == "cleanup":
        return cmd_cleanup(args)
    elif args.command == "summary":
        return cmd_summary(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
