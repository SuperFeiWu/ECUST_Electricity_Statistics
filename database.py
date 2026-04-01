"""
数据库模块 - SQLite 数据存储
支持多宿舍电量记录管理
"""

import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "electricity.db"


def get_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """初始化数据库表结构"""
    conn = get_connection()
    cursor = conn.cursor()

    # 创建宿舍表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dormitories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            buildid INTEGER NOT NULL,
            roomid TEXT NOT NULL,
            warning_threshold REAL DEFAULT 10,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(buildid, roomid)
        )
    """)

    # 创建电量记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS electricity_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dormitory_id INTEGER NOT NULL,
            recorded_date DATE NOT NULL,
            kwh REAL NOT NULL,
            power REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dormitory_id) REFERENCES dormitories(id),
            UNIQUE(dormitory_id, recorded_date)
        )
    """)

    # 检查并添加 power 列
    cursor.execute("PRAGMA table_info(electricity_records)")
    columns = [col[1] for col in cursor.fetchall()]
    if "power" not in columns:
        cursor.execute("ALTER TABLE electricity_records ADD COLUMN power REAL")

    conn.commit()
    conn.close()


def add_dormitory(
    name: str,
    buildid: int,
    roomid: str,
    warning_threshold: float = 10.0,
    push_warning_only: bool = False
) -> int:
    """添加宿舍，返回宿舍ID"""
    conn = get_connection()
    cursor = conn.cursor()

    # 检查表是否有新列，没有则添加
    cursor.execute("PRAGMA table_info(dormitories)")
    columns = [col[1] for col in cursor.fetchall()]

    if "push_warning_only" not in columns:
        cursor.execute("ALTER TABLE dormitories ADD COLUMN push_warning_only INTEGER DEFAULT 0")

    try:
        cursor.execute(
            """
            INSERT INTO dormitories (name, buildid, roomid, warning_threshold, push_warning_only)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, buildid, roomid, warning_threshold, int(push_warning_only))
        )
        conn.commit()
        dormitory_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        # 已存在，获取现有ID
        cursor.execute(
            "SELECT id FROM dormitories WHERE buildid = ? AND roomid = ?",
            (buildid, roomid)
        )
        row = cursor.fetchone()
        dormitory_id = row["id"]
    finally:
        conn.close()

    return dormitory_id


def get_all_dormitories() -> list[dict]:
    """获取所有宿舍"""
    conn = get_connection()
    cursor = conn.cursor()

    # 检查表是否有新列
    cursor.execute("PRAGMA table_info(dormitories)")
    columns = [col[1] for col in cursor.fetchall()]

    # 动态构建 SELECT 语句
    select_columns = ["id", "name", "buildid", "roomid", "warning_threshold", "created_at"]
    if "push_warning_only" in columns:
        select_columns.append("push_warning_only")

    cursor.execute(f"""
        SELECT {', '.join(select_columns)}
        FROM dormitories
        ORDER BY id
    """)

    dormitories = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return dormitories


def get_dormitory_by_id(dormitory_id: int) -> Optional[dict]:
    """根据ID获取宿舍"""
    conn = get_connection()
    cursor = conn.cursor()

    # 检查表是否有新列
    cursor.execute("PRAGMA table_info(dormitories)")
    columns = [col[1] for col in cursor.fetchall()]

    # 动态构建 SELECT 语句
    select_columns = ["id", "name", "buildid", "roomid", "warning_threshold", "created_at"]
    if "push_warning_only" in columns:
        select_columns.append("push_warning_only")

    cursor.execute(
        f"""
        SELECT {', '.join(select_columns)}
        FROM dormitories WHERE id = ?
        """,
        (dormitory_id,)
    )

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def add_electricity_record(
    dormitory_id: int,
    recorded_date: str,
    kwh: float,
    power: float = None
) -> None:
    """添加或更新电量记录"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO electricity_records (dormitory_id, recorded_date, kwh, power)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(dormitory_id, recorded_date)
        DO UPDATE SET kwh = excluded.kwh, power = excluded.power
        """,
        (dormitory_id, recorded_date, kwh, power)
    )

    conn.commit()
    conn.close()


def get_electricity_records(
    dormitory_id: int,
    limit: int = 30
) -> list[dict]:
    """获取电量记录"""
    conn = get_connection()
    cursor = conn.cursor()

    # 检查是否有 power 列
    cursor.execute("PRAGMA table_info(electricity_records)")
    columns = [col[1] for col in cursor.fetchall()]
    has_power = "power" in columns

    if has_power:
        cursor.execute(
            """
            SELECT id, dormitory_id, recorded_date, kwh, power, created_at
            FROM electricity_records
            WHERE dormitory_id = ?
            ORDER BY recorded_date DESC
            LIMIT ?
            """,
            (dormitory_id, limit)
        )
    else:
        cursor.execute(
            """
            SELECT id, dormitory_id, recorded_date, kwh, created_at
            FROM electricity_records
            WHERE dormitory_id = ?
            ORDER BY recorded_date DESC
            LIMIT ?
            """,
            (dormitory_id, limit)
        )

    records = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return records


def get_latest_record(dormitory_id: int) -> Optional[dict]:
    """获取最新电量记录"""
    conn = get_connection()
    cursor = conn.cursor()

    # 检查是否有 power 列
    cursor.execute("PRAGMA table_info(electricity_records)")
    columns = [col[1] for col in cursor.fetchall()]
    has_power = "power" in columns

    if has_power:
        cursor.execute(
            """
            SELECT id, dormitory_id, recorded_date, kwh, power, created_at
            FROM electricity_records
            WHERE dormitory_id = ?
            ORDER BY recorded_date DESC
            LIMIT 1
            """,
            (dormitory_id,)
        )
    else:
        cursor.execute(
            """
            SELECT id, dormitory_id, recorded_date, kwh, created_at
            FROM electricity_records
            WHERE dormitory_id = ?
            ORDER BY recorded_date DESC
            LIMIT 1
            """,
            (dormitory_id,)
        )

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def export_to_json(output_path: Path, days_to_show: int = 30) -> None:
    """导出数据为 JSON 文件供前端使用"""
    conn = get_connection()
    cursor = conn.cursor()

    # 检查表是否有新列
    cursor.execute("PRAGMA table_info(dormitories)")
    columns = [col[1] for col in cursor.fetchall()]

    # 动态构建 SELECT 语句
    select_columns = ["id", "name", "buildid", "roomid", "warning_threshold"]
    if "push_warning_only" in columns:
        select_columns.append("push_warning_only")

    cursor.execute(f"""
        SELECT {', '.join(select_columns)}
        FROM dormitories
        ORDER BY id
    """)
    dormitories = [dict(row) for row in cursor.fetchall()]

    # 检查是否有 power 列
    cursor.execute("PRAGMA table_info(electricity_records)")
    record_columns = [col[1] for col in cursor.fetchall()]
    has_power = "power" in record_columns

    result = {
        "updated_at": date.today().isoformat(),
        "dormitories": []
    }

    for dorm in dormitories:
        # 获取每个宿舍的电量记录
        if has_power:
            cursor.execute(
                """
                SELECT recorded_date as time, kwh, power
                FROM electricity_records
                WHERE dormitory_id = ?
                ORDER BY recorded_date DESC
                LIMIT ?
                """,
                (dorm["id"], days_to_show)
            )
        else:
            cursor.execute(
                """
                SELECT recorded_date as time, kwh
                FROM electricity_records
                WHERE dormitory_id = ?
                ORDER BY recorded_date DESC
                LIMIT ?
                """,
                (dorm["id"], days_to_show)
            )
        records = [dict(row) for row in cursor.fetchall()]

        # 获取最新电量和功率
        latest_kwh = records[0]["kwh"] if records else None
        latest_power = records[0]["power"] if records and has_power else None

        dorm_data = {
            "id": dorm["id"],
            "name": dorm["name"],
            "buildid": dorm["buildid"],
            "roomid": dorm["roomid"],
            "warning_threshold": dorm["warning_threshold"],
            "latest_kwh": latest_kwh,
            "latest_power": latest_power,
            "records": list(reversed(records))  # 按时间升序
        }

        if "push_warning_only" in dorm:
            dorm_data["push_warning_only"] = bool(dorm["push_warning_only"])

        result["dormitories"].append(dorm_data)

    conn.close()

    # 确保 docs 目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 写入 JSON 文件
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# 初始化数据库
if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
