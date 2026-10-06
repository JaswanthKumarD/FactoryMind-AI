# FactoryMind AI —  Complete Demo

FactoryMind is a software-only smart manufacturing project. It is designed as a
realistic hackathon prototype for a small automotive component factory.

The project does **not** need Arduino, sensors, Raspberry Pi or other IoT hardware.
All factory conditions are entered or simulated in software, which makes the
demo easy to run on a normal laptop.

## What the system demonstrates

- Random Forest prediction for machine cycle time
- Random Forest prediction for machine failure risk
- OR-Tools CP-SAT production scheduling
- Gantt-style production planning
- Software Digital Twin of the factory floor
- Multi-agent decision making
- Machine-failure what-if simulation
- Automatic schedule re-optimization
- Orders, machines and inventory views
- AI assistant for common factory questions
- Admin login
- PDF production report

## Factory example

The sample factory makes shafts, gears, brackets and couplings using CNC
turning, milling, drilling, grinding and heat-treatment machines.

The ML demo uses synthetic historical-style data. This is intentional: the
application can run without confidential factory data or IoT devices. For a
real deployment, replace the demo dataset with historical production and
maintenance records.

## Run on Windows

### Option 1 — easiest

Double-click:

`run_windows.bat`

The script creates a virtual environment, installs the required packages,
loads the sample factory data and starts the FastAPI server.

### Option 2 — manual

```text
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python backend\seed.py
uvicorn backend.main:app --reload
```

Open:

`http://127.0.0.1:8000`

## Demo login

Username: `admin`

Password: `FactoryMind@123`

## Recommended hackathon demo flow

1. Show the dashboard and current production KPIs.
2. Open Predictive ML and enter machine conditions.
3. Show the predicted cycle time and failure probability.
4. Open Multi-Agent AI and show the five specialist agents.
5. Show the OR-Tools Gantt schedule.
6. Open Digital Twin and explain the virtual factory state.
7. Simulate a CNC machine failure for six hours.
8. Show the new delay risk and recovery schedule.
9. Generate the PDF production report.

## Code structure

```text
FactoryMind_AI_COMPLETE/
├── backend/
│   ├── agents.py          # Multi-agent factory reasoning
│   ├── ai_engine.py       # Simple factory assistant
│   ├── auth.py            # Demo administrator login
│   ├── database.py        # SQLite database connection/schema
│   ├── main.py            # FastAPI endpoints
│   ├── ml_model.py        # Training and ML prediction
│   ├── models.py          # API request models
│   ├── optimizer.py       # OR-Tools production scheduler
│   ├── report.py          # PDF report generation
│   └── seed.py            # Sample factory data
├── frontend/
│   ├── index.html         # Dashboard layout
│   ├── app.js             # Frontend logic and API calls
│   └── styles.css         # Dashboard styling
├── requirements.txt
└── run_windows.bat
```

## Important note

This is a hackathon-ready prototype, not a certified industrial control
system. The ML data is synthetic and the login is intentionally simple.
Production deployment should use real factory data, secure authentication,
role-based permissions and validated scheduling constraints.
