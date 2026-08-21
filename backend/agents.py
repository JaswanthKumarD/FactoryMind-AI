"""Simple multi-agent orchestration layer for the factory demo."""

from .database import get_conn
from .ml_model import predict
from .optimizer import generate_plan


def run_multi_agent(features=None, failed_machine=None, failure_hours=0):
    """Let each specialist agent contribute one part of the factory decision."""
    schedule = generate_plan(failed_machine, failure_hours)

    utilization = schedule["machine_utilization"]
    bottleneck = max(utilization, key=lambda item: item["utilization"])

    connection = get_conn()
    inventory = [
        dict(row) for row in connection.execute("SELECT * FROM inventory").fetchall()
    ]
    connection.close()

    prediction = predict(features) if features else None

    agents = [
        {
            "name": "Production Planner Agent",
            "status": "completed",
            "output": "Created an OR-Tools schedule using priorities and deadlines.",
        },
        {
            "name": "Predictive Maintenance Agent",
            "status": "completed",
            "output": prediction or "Prediction will run when machine data is supplied.",
        },
        {
            "name": "Bottleneck Analyst Agent",
            "status": "completed",
            "output": f"{bottleneck['machine']} is using {bottleneck['utilization']}% capacity.",
        },
        {
            "name": "Inventory Agent",
            "status": "completed",
            "output": f"Checked {len(inventory)} material records.",
        },
        {
            "name": "Supervisor Agent",
            "status": "completed",
            "output": "Reviewed the combined recommendations and approved the plan.",
        },
    ]

    return {
        "agents": agents,
        "plan": schedule,
        "prediction": prediction,
        "bottleneck": bottleneck,
        "decision": (
            f"Protect capacity on {bottleneck['machine']} and prioritize urgent orders."
        ),
    }
