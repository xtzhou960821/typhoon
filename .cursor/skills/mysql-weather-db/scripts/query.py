"""对气象监测数据库执行只读 SQL 查询的命令行小工具。

连接参数从环境变量读取,密码不硬编码在文件中:

- ``MYSQL_HOST``(默认 ``47.104.235.238``)
- ``MYSQL_PORT``(默认 ``3306``)
- ``MYSQL_USER``(默认 ``root``)
- ``MYSQL_PASS``(必填,数据库密码)
- ``MYSQL_DB``(默认 ``tess_yangchen_ms``)

用法::

    export MYSQL_PASS='<密码>'
    python query.py "SELECT COUNT(*) FROM yangchen_record"

依赖 ``pymysql``(见仓库虚拟环境 ``.venv``)。
"""

from __future__ import annotations

import json
import os
import sys

import pymysql


def run(sql: str) -> list[dict]:
    """执行一条 SQL 查询并以字典列表返回结果。

    :param sql: 要执行的 SQL 语句。
    :returns: 每行一个字典的查询结果。
    :raises SystemExit: 当缺少 ``MYSQL_PASS`` 环境变量时退出。
    """
    password = os.environ.get("MYSQL_PASS")
    if not password:
        raise SystemExit("缺少环境变量 MYSQL_PASS(数据库密码)。")

    conn = pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "47.104.235.238"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=password,
        database=os.environ.get("MYSQL_DB", "tess_yangchen_ms"),
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return list(cur.fetchall())
    finally:
        conn.close()


def main() -> None:
    """命令行入口:执行传入的 SQL 并以 JSON 打印结果。"""
    if len(sys.argv) < 2:
        raise SystemExit('用法: python query.py "<SQL>"')
    rows = run(sys.argv[1])
    print(json.dumps(rows, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
