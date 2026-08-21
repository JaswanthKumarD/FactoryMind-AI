"""FastAPI entry point for FactoryMind AI."""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from .agents import run_multi_agent
from .ai_engine import answer
from .auth import login
from .database import get_conn, init_db
from .ml_model import ensure_models, predict, train_models
from .models import AssistantRequest, MachineFailure, MLPredictionRequest, OrderCreate
from .optimizer import generate_plan
from .report import build_report

BASE_DIR = Path(__file__).resolve().parent.parent
app = FastAPI(title="FactoryMind AI", version="1.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    ensure_models()


@app.get("/api/health")
def health():
    return {"status": "ok", "project": "FactoryMind AI"}


@app.post("/api/login")
def do_login(payload: dict):
    session = login(
        payload.get("username", ""),
        payload.get("password", ""),
    )
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )
    return session


@app.get("/api/dashboard")
def dashboard():
    return generate_plan()


@app.get("/api/ml/metrics")
def ml_metrics():
    metrics_path = Path(__file__).resolve().parent / "models" / "metrics.json"
    return json.loads(metrics_path.read_text())


@app.post("/api/ml/predict")
def ml_predict(payload: MLPredictionRequest):
    return predict(payload.model_dump())


@app.post("/api/ml/retrain")
def ml_retrain():
    return train_models()


@app.post("/api/multi-agent")
def multi_agent(payload: dict):
    return run_multi_agent(payload.get("features"))


@app.get("/api/machines")
def machines():
    connection = get_conn()
    try:
        rows = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM machines ORDER BY code"
            ).fetchall()
        ]
    finally:
        connection.close()
    return rows


@app.get("/api/orders")
def orders():
    connection = get_conn()
    try:
        rows = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM orders ORDER BY priority, deadline_hours"
            ).fetchall()
        ]
    finally:
        connection.close()
    return rows


@app.get("/api/inventory")
def inventory():
    connection = get_conn()
    try:
        rows = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM inventory ORDER BY material"
            ).fetchall()
        ]
    finally:
        connection.close()
    return rows


@app.post("/api/orders")
def add_order(order: OrderCreate):
    connection = get_conn()
    try:
        connection.execute(
            """INSERT INTO orders
            (order_code, product, quantity, priority, deadline_hours, material, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                order.order_code,
                order.product,
                order.quantity,
                order.priority,
                order.deadline_hours,
                order.material,
                "Pending",
            ),
        )
        connection.commit()
    except Exception as exc:
        connection.close()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        try:
            connection.close()
        except Exception:
            pass
    return {"message": "Order added"}


@app.post("/api/plan")
def plan():
    return generate_plan()


@app.post("/api/simulate-failure")
def simulate_failure(payload: MachineFailure):
    """Return the production impact of a hypothetical machine outage."""
    try:
        result = generate_plan(
            payload.machine_code,
            payload.failure_hours,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    result["mode"] = "simulation"
    return result


@app.post("/api/reoptimize")
def reoptimize(payload: MachineFailure):
    """Generate a recovery schedule after the hypothetical failure."""
    try:
        result = generate_plan(
            payload.machine_code,
            payload.failure_hours,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    result["mode"] = "reoptimized"
    result["recovery_summary"] = {
        "message": (
            f"OR-Tools generated a recovery schedule for "
            f"{payload.machine_code} after {payload.failure_hours:g} hours of downtime."
        ),
        "solver": result["solver"],
        "status": result["solver_status"],
    }
    return result


@app.get("/api/report")
def report():
    pdf = build_report(generate_plan())
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
            "attachment; filename=FactoryMind_Report.pdf"
        },
    )


@app.post("/api/assistant")
def assistant(payload: AssistantRequest):
    return answer(payload.question)


app.mount(
    "/",
    StaticFiles(directory=BASE_DIR / "frontend", html=True),
    name="frontend",
)
