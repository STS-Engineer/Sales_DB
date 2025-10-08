from typing import Any, Dict
from sqlalchemy import text
from app.db import engine
from app.config.columns import COLUMN_MAP

def _q(ident: str) -> str:
    return '"' + ident.replace('"', '""') + '"'

def _coerce(db_col: str, value: str | None) -> str | None:
    # Keep simple: insert text; Postgres will cast if compatible.
    return value or None

def build_row(item: Dict[str, Any]) -> Dict[str, Any]:
    cvs = {cv["id"]: cv for cv in (item.get("column_values") or [])}
    row: Dict[str, Any] = {}
    if "name" in COLUMN_MAP:
        row[COLUMN_MAP["name"]] = item.get("name")
    for monday_col_id, db_col in COLUMN_MAP.items():
        if monday_col_id == "name":
            continue
        row[db_col] = _coerce(db_col, cvs.get(monday_col_id, {}).get("text"))
    return row

def insert_row(row: Dict[str, Any]):
    cols = [ _q(c) for c in row.keys() ]
    params = { f"p{i}": v for i, v in enumerate(row.values()) }
    placeholders = ", ".join([ f":p{i}" for i in range(len(params)) ])
    sql = f'INSERT INTO public.monday_logger ({", ".join(cols)}) VALUES ({placeholders})'
    with engine.begin() as conn:
        conn.execute(text(sql), params)
