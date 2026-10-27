import os
import sys
import json
import re
import signal
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

import pandas as pd
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI(title="StockAgent Web Dashboard", version="1.0.0")

BASE_DIR = Path(__file__).resolve().parent
RES_DIR = BASE_DIR / "res"
LOG_FILE = BASE_DIR / "log" / "test.txt"
STATIC_DIR = BASE_DIR / "static"

sim_process: Optional[subprocess.Popen] = None
sim_config: Dict[str, Any] = {
    "model": "openai/gpt-oss-120b",
    "agents": 10,
    "days": 2,
    "sessions": 2,
    "running": False,
    "pid": None,
}


class StartSimRequest(BaseModel):
    model: str = "openai/gpt-oss-120b"
    agents: int = 10
    days: int = 2
    sessions: int = 2


def parse_forum_messages() -> List[Dict[str, Any]]:
    posts = []
    if not LOG_FILE.exists():
        return posts
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Find messages like "Agent X says: ..."
        pattern = re.compile(
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+).*?Agent (\d+) says:\s*([\s\S]*?)(?=\n\d{4}-\d{2}-\d{2}|$)",
            re.MULTILINE
        )
        matches = pattern.findall(content)
        for ts, agent_id, msg in matches[-20:]:  # last 20 posts
            msg_clean = msg.strip()
            # Simple sentiment detection
            lower_msg = msg_clean.lower()
            if any(w in lower_msg for w in ["rally", "buy", "gain", "bull", "optimistic", "growth", "high"]):
                sentiment = "Bullish"
            elif any(w in lower_msg for w in ["drop", "sell", "bear", "down", "risk", "loss", "caution"]):
                sentiment = "Bearish"
            else:
                sentiment = "Neutral"

            posts.append({
                "timestamp": ts,
                "agent_id": int(agent_id),
                "message": msg_clean,
                "sentiment": sentiment
            })
    except Exception as e:
        print(f"Error parsing forum: {e}")
    return list(reversed(posts))


def parse_live_progress() -> Dict[str, Any]:
    progress = {"day": 1, "session": 1, "total_days": sim_config.get("days", 10), "total_sessions": sim_config.get("sessions", 3), "status": "Idle"}
    if not LOG_FILE.exists():
        return progress

    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[-150:]

        for line in reversed(lines):
            day_match = re.search(r"--------DAY (\d+)---------", line)
            if day_match and progress["day"] == 1:
                progress["day"] = int(day_match.group(1))

            session_match = re.search(r"SESSION (\d+)", line)
            if session_match and progress["session"] == 1:
                progress["session"] = int(session_match.group(1))

            if "Simulation finished!" in line:
                progress["status"] = "Completed"
                break
    except Exception as e:
        print(f"Error parsing progress: {e}")

    return progress


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
def get_status():
    global sim_process
    is_running = False
    if sim_process is not None:
        if sim_process.poll() is None:
            is_running = True
        else:
            sim_process = None

    # Also check if any external python main.py is running
    progress = parse_live_progress()
    status_str = "Running" if is_running else progress.get("status", "Idle")

    return {
        "running": is_running,
        "pid": sim_process.pid if is_running else None,
        "config": sim_config,
        "progress": progress,
        "status": status_str
    }


@app.get("/api/market")
def get_market():
    stocks_file = RES_DIR / "stocks.xlsx"
    points = []
    current_a = 26.78
    current_b = 42.22

    if stocks_file.exists():
        try:
            df = pd.read_excel(stocks_file)
            if not df.empty:
                # Support both English and legacy column headers
                for _, row in df.iterrows():
                    day = int(row.get("Trading Day", row.get("交易日", 1)))
                    session = int(row.get("Trading Session", row.get("第几个交易阶段", 1)))
                    p_a = float(row.get("Stock A Close Price", row.get("阶段结束后股票A价格", 0)))
                    p_b = float(row.get("Stock B Close Price", row.get("阶段结束后股票B价格", 0)))
                    points.append({
                        "label": f"D{day}-S{session}",
                        "day": day,
                        "session": session,
                        "stock_a": round(p_a, 2),
                        "stock_b": round(p_b, 2),
                    })
                if points:
                    current_a = points[-1]["stock_a"]
                    current_b = points[-1]["stock_b"]
        except Exception as e:
            print(f"Error reading stocks.xlsx: {e}")

    # Fallback points if empty
    if not points:
        points = [
            {"label": "D1-S1", "day": 1, "session": 1, "stock_a": 26.78, "stock_b": 42.22}
        ]

    # Calculate 24h/session change
    change_a = round(((current_a - 26.78) / 26.78) * 100, 2)
    change_b = round(((current_b - 42.22) / 42.22) * 100, 2)

    return {
        "current_stock_a": current_a,
        "current_stock_b": current_b,
        "change_a": change_a,
        "change_b": change_b,
        "history": points
    }


@app.get("/api/trades")
def get_trades(limit: int = 50):
    trades_file = RES_DIR / "trades.xlsx"
    trades = []
    if trades_file.exists():
        try:
            df = pd.read_excel(trades_file)
            if not df.empty:
                # Support both English and legacy column headers
                for _, row in df.iterrows():
                    qty = int(row.get("Trade Quantity", row.get("交易数量", 0)))
                    price = float(row.get("Trade Price", row.get("交易价格", 0.0)))
                    trades.append({
                        "day": int(row.get("Trading Day", row.get("交易日", 1))),
                        "session": int(row.get("Trading Session", row.get("交易阶段", 1))),
                        "stock": str(row.get("Stock Symbol", row.get("股票类型", "A"))),
                        "buyer": int(row.get("Buyer Trader ID", row.get("买入交易员", 0))),
                        "seller": int(row.get("Seller Trader ID", row.get("卖出交易员", 0))),
                        "quantity": qty,
                        "price": price,
                        "total_value": round(float(qty) * float(price), 2)
                    })
        except Exception as e:
            print(f"Error reading trades.xlsx: {e}")

    # Return latest first
    trades = list(reversed(trades))[:limit]
    total_volume = sum(t["quantity"] for t in trades)
    total_trades_count = len(trades)
    return {
        "total_trades": total_trades_count,
        "total_volume": total_volume,
        "trades": trades
    }


@app.get("/api/agents")
def get_agents():
    agent_session_file = RES_DIR / "agent_session_record.xlsx"
    agents_map: Dict[int, Dict[str, Any]] = {}

    if agent_session_file.exists():
        try:
            df = pd.read_excel(agent_session_file)
            if not df.empty:
                # Support both English and legacy column headers
                for _, row in df.iterrows():
                    agent_id = int(row.get("Trader ID", row.get("交易员", 0)))
                    agents_map[agent_id] = {
                        "agent_id": agent_id,
                        "day": int(row.get("Trading Day", row.get("交易日", 1))),
                        "session": int(row.get("Trading Session", row.get("交易阶段", 1))),
                        "total_proper": round(float(row.get("Total Assets Before Trading", row.get("交易前资产总额", 0.0))), 2),
                        "cash": round(float(row.get("Cash Before Trading", row.get("交易前持有现金", 0.0))), 2),
                        "stock_a_value": round(float(row.get("Stock A Value Before Trading", row.get("交易前持有的A股价值", 0.0))), 2),
                        "stock_b_value": round(float(row.get("Stock B Value Before Trading", row.get("交易前持有的B股价值", 0.0))), 2),
                        "last_action_type": str(row.get("Order Type", row.get("挂单类型", "-"))),
                        "last_stock": str(row.get("Order Stock Symbol", row.get("挂单股票类别", "-"))),
                        "last_amount": int(row.get("Order Quantity", row.get("挂单数量", 0))),
                        "last_price": float(row.get("Order Price", row.get("挂单价格", 0.0))),
                    }
        except Exception as e:
            print(f"Error reading agent_session_record: {e}")

    # Fallback personality styles for visual depth
    styles = ["Balanced", "Aggressive", "Conservative", "Growth-Oriented"]
    agents_list = []
    for agent_id, data in sorted(agents_map.items()):
        data["personality"] = styles[agent_id % len(styles)]
        agents_list.append(data)

    return {"count": len(agents_list), "agents": agents_list}


@app.get("/api/forum")
def get_forum():
    return {"posts": parse_forum_messages()}


@app.get("/api/logs")
def get_logs(lines: int = 60):
    log_lines = []
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()
                log_lines = [l.rstrip("\r\n") for l in all_lines[-lines:]]
        except Exception as e:
            log_lines = [f"Error reading log: {e}"]
    return {"lines": log_lines}


@app.post("/api/simulation/start")
def start_simulation(req: StartSimRequest):
    global sim_process, sim_config
    if sim_process is not None and sim_process.poll() is None:
        raise HTTPException(status_code=400, detail="Simulation is already running!")

    python_exe = sys.executable
    venv_python = BASE_DIR / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        python_exe = str(venv_python)

    cmd = [
        python_exe,
        "main.py",
        "--model", req.model,
        "--agents", str(req.agents),
        "--days", str(req.days),
        "--sessions", str(req.sessions)
    ]

    try:
        sim_process = subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        sim_config = {
            "model": req.model,
            "agents": req.agents,
            "days": req.days,
            "sessions": req.sessions,
            "running": True,
            "pid": sim_process.pid
        }
        return {"status": "started", "pid": sim_process.pid, "config": sim_config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start simulation: {e}")


@app.post("/api/simulation/stop")
def stop_simulation():
    global sim_process
    if sim_process is None or sim_process.poll() is not None:
        return {"status": "not_running"}

    try:
        sim_process.terminate()
        sim_process.wait(timeout=3)
    except Exception:
        sim_process.kill()

    sim_process = None
    return {"status": "stopped"}


@app.get("/api/download/{filename}")
def download_file(filename: str):
    allowed = ["trades.xlsx", "stocks.xlsx", "agent_day_record.xlsx", "agent_session_record.xlsx"]
    if filename not in allowed:
        raise HTTPException(status_code=400, detail="Invalid file requested")
    target = RES_DIR / filename
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not yet generated by simulation")
    
    # Ensure all column headers, values, and sheet names are converted to English
    try:
        from record import ensure_excel_english
        ensure_excel_english(str(target))
    except Exception as e:
        print(f"Error ensuring English export for {filename}: {e}")

    return FileResponse(target, filename=filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# Mount static assets
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
