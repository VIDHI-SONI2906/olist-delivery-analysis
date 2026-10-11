"""Run a .sql file against the database and print every SELECT result.

Usage:  python scripts/run_sql.py sql/03_delivery_analysis.sql
A comment line starting with '-- Q' is used as the heading for the
result that follows it. Statements must end with a semicolon.
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

from config import DB_PATH

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)


def run_file(path: Path) -> None:
    text = path.read_text()
    con = sqlite3.connect(DB_PATH)
    heading = ""
    buffer = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("-- Q"):
            heading = stripped[3:].strip()
        buffer.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(buffer).strip()
            buffer = []
            body = "\n".join(l for l in statement.splitlines() if not l.strip().startswith("--")).strip()
            if not body:
                continue
            first_word = body.split()[0].upper()
            if first_word in ("SELECT", "WITH"):
                print(f"\n=== {heading} ===")
                print(pd.read_sql_query(statement, con).to_string(index=False))
                heading = ""
            else:
                con.executescript(statement)
    con.commit()
    con.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/run_sql.py <file.sql>")
    run_file(Path(sys.argv[1]))
