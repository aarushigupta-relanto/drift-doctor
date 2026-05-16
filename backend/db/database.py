import aiosqlite, json, sys, os
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = "drift_doctor.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS drift_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
            severity TEXT NOT NULL, drift_share REAL NOT NULL,
            report_json TEXT NOT NULL, diagnosis_json TEXT)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS retrain_tasks (
            task_id TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'queued',
            strategy TEXT NOT NULL DEFAULT 'full', requested_by TEXT NOT NULL DEFAULT 'auto',
            created_at TEXT NOT NULL, result_json TEXT)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
            user_message TEXT NOT NULL, intent TEXT NOT NULL,
            response_time_ms REAL NOT NULL, confidence REAL NOT NULL, session_id TEXT NOT NULL)""")
        await db.commit()

async def save_drift_event(severity, drift_share, report, diagnosis=None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO drift_events (timestamp, severity, drift_share, report_json, diagnosis_json) VALUES (?,?,?,?,?)",
            (datetime.utcnow().isoformat(), severity, drift_share, json.dumps(report), json.dumps(diagnosis) if diagnosis else None))
        await db.commit()
        return cursor.lastrowid

async def get_drift_history(limit=50) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, timestamp, severity, drift_share FROM drift_events ORDER BY id DESC LIMIT ?", (limit,)) as cursor:
            return [dict(r) for r in await cursor.fetchall()]

async def get_latest_drift() -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM drift_events ORDER BY id DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if not row: return None
            r = dict(row)
            r["report"] = json.loads(r.pop("report_json"))
            r["diagnosis"] = json.loads(r["diagnosis_json"]) if r.get("diagnosis_json") else None
            r.pop("diagnosis_json", None)
            return r

async def save_retrain_task(task_id, strategy, requested_by):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO retrain_tasks (task_id, status, strategy, requested_by, created_at) VALUES (?,?,?,?,?)",
            (task_id, "queued", strategy, requested_by, datetime.utcnow().isoformat()))
        await db.commit()

async def update_retrain_task(task_id, status, result=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE retrain_tasks SET status=?, result_json=? WHERE task_id=?",
            (status, json.dumps(result) if result else None, task_id))
        await db.commit()

async def get_retrain_task(task_id) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM retrain_tasks WHERE task_id=?", (task_id,)) as cursor:
            row = await cursor.fetchone()
            if not row: return None
            r = dict(row)
            r["result"] = json.loads(r["result_json"]) if r.get("result_json") else None
            r.pop("result_json", None)
            return r

async def save_chat_log(log: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO chat_logs (timestamp, user_message, intent, response_time_ms, confidence, session_id) VALUES (?,?,?,?,?,?)",
            (log.get("timestamp", datetime.utcnow().isoformat()), log["user_message"], log["intent"], log["response_time_ms"], log["confidence"], log["session_id"]))
        await db.commit()
