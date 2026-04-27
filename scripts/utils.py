#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aaron-pic-sorting 公共工具函数
负责：配置读写、路径展开、日期提取、MD5计算、SQLite去重、日志记录等
"""

import os
import sys
import re
import hashlib
import sqlite3
import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple

# 尝试导入 Pillow 用于 EXIF 读取
ty_pl = None
try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    ty_pl = True
except ImportError:
    ty_pl = False


def expand_path(path_str: str, context: Optional[Dict[str, str]] = None) -> str:
    """
    展开路径：支持 ~ 和 {variable} 占位符
    """
    if not path_str:
        return ""
    # 展开家目录
    path_str = os.path.expanduser(path_str)
    # 替换上下文变量
    if context:
        for key, value in context.items():
            path_str = path_str.replace(f"{{{key}}}", value)
    # 展开环境变量
    path_str = os.path.expandvars(path_str)
    return os.path.abspath(path_str)


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载配置文件，支持环境变量覆盖
    优先级：环境变量 > 用户配置 > 内置默认值
    """
    import yaml

    # 1. 加载内置默认值
    skill_dir = Path(__file__).parent.parent
    default_path = skill_dir / "config" / "config.default.yaml"
    with open(default_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    # 2. 加载用户配置
    if config_path is None:
        config_path = os.path.expanduser("~/.config/aaron-pic-sorting/config.yaml")
    else:
        config_path = os.path.expanduser(config_path)

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
        _deep_merge(config, user_config)

    # 3. 环境变量覆盖
    if os.environ.get("AARON_PIC_SORTING_SOURCE"):
        config.setdefault("paths", {})["source_root"] = os.environ["AARON_PIC_SORTING_SOURCE"]
    if os.environ.get("AARON_PIC_SORTING_TARGET"):
        config.setdefault("paths", {})["target_root"] = os.environ["AARON_PIC_SORTING_TARGET"]
    if os.environ.get("AARON_PIC_SORTING_CRON"):
        config.setdefault("schedule", {})["cron"] = os.environ["AARON_PIC_SORTING_CRON"]
    if os.environ.get("AARON_PIC_SORTING_CONFIG"):
        # 如果指定了配置文件，已在参数中处理
        pass

    # 展开路径变量（仅对 paths 下的实际路径字段展开，避免误伤 naming_template 等模板）
    src = config.get("paths", {}).get("source_root", "")
    context = {"source_root": src}
    for key in config.get("paths", {}):
        if isinstance(config["paths"][key], str) and ("{" in config["paths"][key] or "~" in config["paths"][key]):
            config["paths"][key] = expand_path(config["paths"][key], context)

    return config


def _deep_merge(base: Dict, override: Dict) -> None:
    """
    深度合并字典，override 优先
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def ensure_dir(path: str) -> None:
    """确保目录存在"""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def compute_md5(file_path: str) -> str:
    """计算文件 MD5"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def init_db(db_path: str) -> sqlite3.Connection:
    """
    初始化 SQLite 去重数据库
    """
    ensure_dir(os.path.dirname(db_path))
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS processed (
            md5 TEXT PRIMARY KEY,
            source_path TEXT,
            target_path TEXT,
            processed_at TEXT
        )
    """)
    conn.commit()
    return conn


def is_processed(conn: sqlite3.Connection, md5: str) -> bool:
    """检查 MD5 是否已处理"""
    cursor = conn.execute("SELECT 1 FROM processed WHERE md5 = ?", (md5,))
    return cursor.fetchone() is not None


def mark_processed(conn: sqlite3.Connection, md5: str, source_path: str, target_path: str) -> None:
    """标记文件已处理"""
    now = datetime.datetime.now().isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO processed (md5, source_path, target_path, processed_at) VALUES (?, ?, ?, ?)",
        (md5, source_path, target_path, now)
    )
    conn.commit()


def get_date_candidates(file_path: str) -> Dict[str, Optional[str]]:
    """
    获取日期候选：EXIF 拍摄日期、文件修改时间
    返回格式：{"exif": "YYYY:MM:DD" 或 None, "mtime": "YYYY-MM-DD" 或 None}
    """
    result = {"exif": None, "mtime": None}

    # EXIF 日期
    if ty_pl:
        try:
            with Image.open(file_path) as img:
                exif = img._getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        if tag == "DateTimeOriginal":
                            # 格式: "2026:04:05 10:00:00"
                            result["exif"] = value.split(" ")[0]
                            break
        except Exception:
            pass

    # 文件修改时间
    try:
        mtime = os.path.getmtime(file_path)
        result["mtime"] = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
    except Exception:
        pass

    return result


def resolve_date(date_candidates: Dict[str, Optional[str]], priority: List[str]) -> str:
    """
    按优先级解析日期，返回 YYYYMMDD
    """
    for source in priority:
        val = date_candidates.get(source)
        if val:
            # 统一格式化为 YYYYMMDD
            val = val.replace(":", "-").replace("/", "-")
            try:
                dt = datetime.datetime.strptime(val, "%Y-%m-%d")
                return dt.strftime("%Y%m%d")
            except ValueError:
                continue
    # 默认当天
    return datetime.datetime.now().strftime("%Y%m%d")


def sanitize_filename(text: str, separator: str = "-") -> str:
    """
    清理文件名中的非法字符
    """
    if not text:
        return "unknown"
    # 替换文件系统非法字符
    illegal = r'[\\/:*?"<>|]'
    text = re.sub(illegal, separator, text)
    # 去除多余空格
    text = re.sub(r'\s+', separator, text).strip(separator)
    # 限制长度
    if len(text) > 50:
        text = text[:50]
    return text


def get_supported_files(source_root: str, supported_formats: List[str]) -> List[str]:
    """
    扫描目录，获取所有支持格式的图片文件（排除已处理目录）
    """
    files = []
    if not os.path.exists(source_root):
        return files

    for entry in os.listdir(source_root):
        full_path = os.path.join(source_root, entry)
        if os.path.isdir(full_path):
            # 跳过已处理目录（匹配 *-已处理 或 *-processed）
            if entry.endswith("-已处理") or entry.endswith("-processed"):
                continue
            continue
        # 检查扩展名
        _, ext = os.path.splitext(entry)
        ext_clean = ext.lower().lstrip(".")
        if ext_clean in supported_formats:
            files.append(full_path)

    return sorted(files)


def write_log(log_file: str, status: str, filename: str, detail: str = "") -> None:
    """
    写入日志
    """
    ensure_dir(os.path.dirname(log_file))
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {status} | {filename} | {detail}\n"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line)


def cleanup_old_processed_dirs(source_root: str, retention_days: int, log_file: str) -> int:
    """
    清理超过保留天数的已处理目录
    返回删除的目录数量
    """
    if not os.path.exists(source_root):
        return 0

    cleaned = 0
    now = datetime.datetime.now()
    for entry in os.listdir(source_root):
        if not (entry.endswith("-已处理") or entry.endswith("-processed")):
            continue
        full_path = os.path.join(source_root, entry)
        if not os.path.isdir(full_path):
            continue

        try:
            # 提取目录前面的日期部分，如 "20260405-已处理"
            date_part = entry.split("-")[0]
            dir_date = datetime.datetime.strptime(date_part, "%Y%m%d")
            if (now - dir_date).days > retention_days:
                import shutil
                shutil.rmtree(full_path)
                cleaned += 1
                if log_file:
                    write_log(log_file, "CLEAN", entry, f"删除 {retention_days} 天以上已处理目录")
        except (ValueError, OSError):
            continue

    return cleaned


def build_target_filename(
    date_str: str,
    tag1: str,
    tag2: str,
    ext: str,
    naming_template: str = "{date}-{tag1}-{tag2}.{ext}"
) -> str:
    """
    根据模板构建目标文件名
    """
    return naming_template.format(date=date_str, tag1=tag1, tag2=tag2, ext=ext.lstrip("."))


def check_config_exists(config_path: Optional[str] = None) -> bool:
    """
    检查用户配置文件是否存在
    """
    if config_path is None:
        config_path = os.path.expanduser("~/.config/aaron-pic-sorting/config.yaml")
    else:
        config_path = os.path.expanduser(config_path)
    return os.path.exists(config_path)
