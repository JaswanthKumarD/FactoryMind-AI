// ============================================================
// FactoryMind AI - Frontend Application
// ============================================================

const $ = (id) => document.getElementById(id);

let base = null;
let lastSimulation = null;


// ============================================================
// API HELPER
// ============================================================

async function api(url, options = {}) {

    const response = await fetch(url, {
        headers: {
            "Content-Type": "application/json"
        },
        ...options,
    });

    if (!response.ok) {

        let message = "Request failed";

        try {

            const body = await response.json();

            message =
                body.detail ||
                body.message ||
                message;

        } catch (_) {}

        throw new Error(message);
    }

    return response.json();
}


// ============================================================
// AUTHENTICATION
// ============================================================

async function login() {

    try {

        const username =
            $("user").value.trim();

        const password =
            $("pass").value;

        await api("/api/login", {

            method: "POST",

            body: JSON.stringify({
                username,
                password
            }),

        });

        $("login").classList.add("hidden");

        $("side").classList.remove("hidden");

        $("app").classList.remove("hidden");

        await loadDashboard();

    } catch (error) {

        alert(
            error.message ||
            "Invalid username or password."
        );
    }
}


// ============================================================
// NAVIGATION
// ============================================================

document.querySelectorAll(".nav").forEach((button) => {

    button.onclick = async () => {

        document
            .querySelectorAll(".nav")
            .forEach((item) =>
                item.classList.remove("active")
            );

        button.classList.add("active");


        document
            .querySelectorAll(".page")
            .forEach((page) =>
                page.classList.remove("active")
            );


        const pageName =
            button.dataset.page;

        $(pageName)?.classList.add("active");


        const titles = {

            dashboard:
                "Dashboard",

            gantt:
                "Gantt Planner",

            twin:
                "Digital Twin",

            ml:
                "Predictive Machine Learning",

            agents:
                "Multi-Agent AI",

            orders:
                "Orders",

            machines:
                "Machines",

            inventory:
                "Inventory",

            simulation:
                "What-If Simulation",

            assistant:
                "AI Assistant",
        };


        if ($("title")) {

            $("title").textContent =
                titles[pageName] ||
                "FactoryMind AI";
        }


        try {

            if (pageName === "dashboard")
                await loadDashboard();

            if (pageName === "gantt")
                await gantt();

            if (pageName === "twin")
                await twin();

            if (pageName === "ml")
                await ml();

            if (pageName === "agents")
                await agents();

            if (pageName === "orders")
                await orders();

            if (pageName === "machines")
                await machines();

            if (pageName === "inventory")
                await inventory();

            if (pageName === "simulation")
                await options();

        } catch (error) {

            console.error(
                `Error loading ${pageName}:`,
                error
            );
        }
    };
});


// ============================================================
// DASHBOARD
// ============================================================

async function loadDashboard() {

    base =
        await api("/api/dashboard");

    const k =
        base.kpis;


    $("kpis").innerHTML = [

        [
            "Orders",
            k.total_orders
        ],

        [
            "Efficiency",
            `${k.efficiency}%`
        ],

        [
            "Utilization",
            `${k.average_utilization}%`
        ],

        [
            "Delay Risk",
            `${k.delay_risk}%`
        ],

    ]
        .map(([label, value]) => `

            <div class="card">

                <div class="label">
                    ${label}
                </div>

                <div class="value">
                    ${value}
                </div>

            </div>

        `)
        .join("");


    $("util").innerHTML =
        base.machine_utilization
            .map((m) => `

                <div class="util">

                    <div class="ut">

                        <span>
                            ${m.machine} · ${m.name}
                        </span>

                        <span>
                            ${m.utilization}%
                        </span>

                    </div>


                    <div class="bar">

                        <i
                            style="
                                width:${Math.min(
                                    100,
                                    m.utilization
                                )}%
                            "
                        ></i>

                    </div>

                </div>

            `)
            .join("");


    const bottleneck =
        [...base.machine_utilization]
            .sort(
                (a, b) =>
                    b.utilization -
                    a.utilization
            )[0];


    $("insights").innerHTML = `

        <div class="insight">

            <b>OR-Tools</b><br>

            CP-SAT schedule optimized
            for priorities and deadlines.

        </div>


        <div class="insight">

            <b>Bottleneck</b><br>

            ${bottleneck.machine}
            is using
            ${bottleneck.utilization}%
            capacity.

        </div>


        <div class="insight">

            <b>Overtime</b><br>

            ${k.overtime_hours}
            hours scheduled beyond
            normal capacity.

        </div>

    `;


    $("plan").innerHTML = `

        <tr>

            <th>Order</th>
            <th>Product</th>
            <th>Machine</th>
            <th>Step</th>
            <th>Start</th>
            <th>End</th>
            <th>Status</th>

        </tr>


        ${base.plan
            .map((p) => `

                <tr>

                    <td>
                        ${p.order_code}
                    </td>

                    <td>
                        ${p.product}
                    </td>

                    <td>
                        ${p.machine}
                    </td>

                    <td>
                        ${p.step}
                    </td>

                    <td>
                        ${p.start_hour}h
                    </td>

                    <td>
                        ${p.end_hour}h
                    </td>

                    <td>

                        ${
                            p.feasible
                                ? "ON TIME"
                                : "DELAY RISK"
                        }

                    </td>

                </tr>

            `)
            .join("")}

    `;
}


// ============================================================
// GANTT
// ============================================================

async function gantt() {

    if (!base)
        await loadDashboard();


    const by = {};


    base.plan.forEach((p) => {

        (by[p.machine] ??= [])
            .push(p);

    });


    const max =
        Math.max(
            ...base.plan.map(
                (p) => p.end_hour
            ),
            1
        );


    $("ganttChart").innerHTML =

        Object.entries(by)
            .map(([machine, tasks]) => `

                <div class="grow">

                    <div class="glabel">
                        ${machine}
                    </div>


                    <div class="timeline">

                        ${tasks
                            .map((p) => `

                                <div
                                    class="task"
                                    style="
                                        left:
                                        ${
                                            p.start_hour /
                                            max *
                                            100
                                        }%;

                                        width:
                                        ${Math.max(
                                            2,
                                            (
                                                (
                                                    p.end_hour -
                                                    p.start_hour
                                                )
                                                /
                                                max
                                            ) *
                                            100
                                        )}%
                                    "
                                >

                                    ${p.order_code}
                                    ${p.product}

                                </div>

                            `)
                            .join("")}

                    </div>

                </div>

            `)
            .join("");
}


// ============================================================
// DIGITAL TWIN
// ============================================================

async function twin() {

    if (!base)
        await loadDashboard();


    $("twinView").innerHTML =

        base.machine_utilization
            .map((m) => `

                <div
                    class="station
                    ${
                        m.utilization > 85
                            ? "busy"
                            : ""
                    }"
                >

                    <i></i>

                    <b>
                        ${m.machine}
                    </b>

                    <h3>
                        ${m.name}
                    </h3>


                    <div class="meta">

                        Utilization:
                        ${m.utilization}%

                        <br>

                        Used:
                        ${m.used_hours}h /
                        ${m.available_hours}h

                        <br>

                        Status:
                        ${m.status}

                    </div>

                </div>

            `)
            .join("");
}


// ============================================================
// ML
// ============================================================

async function ml() {

    const metrics =
        await api("/api/ml/metrics");


    $("mlMetrics").innerHTML = [

        [
            "Model",
            "Random Forest"
        ],

        [
            "Rows",
            metrics.training_rows
        ],

        [
            "Cycle MAE",
            `${metrics.cycle_mae_minutes} min`
        ],

        [
            "Accuracy",
            `${metrics.failure_accuracy}%`
        ],

    ]
        .map(([label, value]) => `

            <div class="card">

                <div class="label">
                    ${label}
                </div>

                <div class="value">
                    ${value}
                </div>

            </div>

        `)
        .join("");
}


async function predictML() {

    try {

        const features = {

            machine_age_years:
                +$("age").value,

            load_percent:
                +$("load").value,

            temperature_c:
                +$("temp").value,

            vibration_mm_s:
                +$("vib").value,

            hours_since_maintenance:
                +$("maint").value,

            batch_size:
                +$("batch").value,

            operator_experience_years:
                +$("opx").value,

            tool_wear_percent:
                +$("wear").value,

            material_hardness:
                +$("hard").value,
        };


        const result =
            await api(
                "/api/ml/predict",
                {
                    method: "POST",

                    body:
                        JSON.stringify(
                            features
                        ),
                }
            );


        $("mlResult").innerHTML = `

            <strong>
                Predicted Cycle Time:
            </strong>

            ${result.predicted_cycle_time_minutes}
            min

            <br>

            <strong>
                Failure Probability:
            </strong>

            ${result.failure_probability}%

            <br>

            <strong>
                Risk:
            </strong>

            ${result.risk_level}

        `;

    } catch (error) {

        $("mlResult").innerHTML = `

            <b>
                Prediction failed:
            </b>

            ${error.message}

        `;
    }
}


// ============================================================
// MULTI-AGENT
// ============================================================

async function agents() {

    const features = {

        machine_age_years: 7,
        load_percent: 82,
        temperature_c: 76,
        vibration_mm_s: 4.2,
        hours_since_maintenance: 420,
        batch_size: 500,
        operator_experience_years: 4,
        tool_wear_percent: 58,
        material_hardness: 190,

    };


    const r =
        await api(
            "/api/multi-agent",
            {
                method: "POST",

                body:
                    JSON.stringify({
                        features
                    }),
            }
        );


    $("agentGrid").innerHTML =

        r.agents
            .map((a) => `

                <div class="agent">

                    <b>
                        ✦ ${a.name}
                    </b>

                    <p class="meta">
                        ${a.status}
                    </p>

                    <p>
                        ${formatAgentOutput(
                            a.output
                        )}
                    </p>

                </div>

            `)
            .join("");


    $("decision").innerHTML = `

        <b>
            Supervisor Decision:
        </b>

        <br>

        ${r.decision}

    `;
}


function formatAgentOutput(output) {

    if (
        typeof output === "object" &&
        output !== null
    ) {

        return `

            <strong>
                Predicted Cycle Time:
            </strong>

            ${
                output.predicted_cycle_time_minutes
                ?? "N/A"
            }

            min

            <br>

            <strong>
                Failure Probability:
            </strong>

            ${
                output.failure_probability
                ?? "N/A"
            }%

            <br>

            <strong>
                Risk Level:
            </strong>

            ${
                output.risk_level
                ?? "UNKNOWN"
            }

        `;
    }


    return String(
        output ??
        "Agent completed successfully."
    );
}


// ============================================================
// ORDERS
// ============================================================

async function orders() {

    const rows =
        await api("/api/orders");


    $("ordersTable").innerHTML = `

        <tr>

            <th>Order</th>
            <th>Product</th>
            <th>Quantity</th>
            <th>Priority</th>
            <th>Deadline</th>

        </tr>


        ${rows
            .map((o) => `

                <tr>

                    <td>
                        ${o.order_code}
                    </td>

                    <td>
                        ${o.product}
                    </td>

                    <td>
                        ${o.quantity}
                    </td>

                    <td>
                        ${o.priority}
                    </td>

                    <td>
                        ${o.deadline_hours}h
                    </td>

                </tr>

            `)
            .join("")}

    `;
}


// ============================================================
// MACHINES
// ============================================================

async function machines() {

    const rows =
        await api("/api/machines");


    $("machinesGrid").innerHTML =

        rows
            .map((m) => `

                <div class="machine">

                    <b>
                        ${m.code}
                    </b>

                    ${m.name}

                    <div class="meta">

                        Type:
                        ${m.machine_type}

                        <br>

                        Capacity:
                        ${m.capacity_per_hour}/hr

                        <br>

                        Cost:
                        ₹${m.cost_per_hour}/hr

                    </div>

                </div>

            `)
            .join("");
}


// ============================================================
// INVENTORY
// ============================================================

async function inventory() {

    const rows =
        await api("/api/inventory");


    $("inventoryGrid").innerHTML =

        rows
            .map((item) => `

                <div class="machine">

                    <b>
                        ${item.material}
                    </b>

                    <div class="meta">

                        Quantity:
                        ${item.quantity}
                        ${item.unit}

                    </div>

                </div>

            `)
            .join("");
}


// ============================================================
// WHAT-IF OPTIONS
// ============================================================

async function options() {

    const rows =
        await api("/api/machines");


    $("fm").innerHTML =

        rows
            .map((m) => `

                <option value="${m.code}">

                    ${m.code}
                    -
                    ${m.name}

                </option>

            `)
            .join("");
}


// ============================================================
// SCHEDULE CHANGE RENDERER
// ============================================================

function renderScheduleChanges(result) {

    const impact =
        result.impact || {};


    const changes =
        result.schedule_changes ||
        impact.schedule_changes ||
        [];


    const summary =
        result.change_summary ||
        impact.change_summary ||
        [];


    if (
        changes.length === 0 &&
        summary.length === 0
    ) {

        return `

            <div class="insight">

                <b>
                    Schedule Changes
                </b>

                <br>

                No machine reassignment
                or timing changes were required.

            </div>

        `;
    }


    let rows = "";


    changes.forEach((change) => {

        const beforeMachine =
            change.before_machine ??
            "N/A";

        const afterMachine =
            change.after_machine ??
            "N/A";

        const beforeStart =
            change.before_start_hour ??
            "N/A";

        const afterStart =
            change.after_start_hour ??
            "N/A";

        const status =
            change.status ??
            "Changed";


        rows += `

            <tr>

                <td>
                    ${change.order_code ?? "N/A"}
                </td>

                <td>
                    ${change.product ?? "N/A"}
                </td>

                <td>
                    ${change.step ?? "N/A"}
                </td>

                <td>
                    ${beforeMachine}
                </td>

                <td>
                    ${afterMachine}
                </td>

                <td>
                    ${beforeStart}h
                </td>

                <td>
                    ${afterStart}h
                </td>

                <td>
                    ${status}
                </td>

            </tr>

        `;
    });


    return `

        <div class="recovery-section">

            <h4>
                🔄 Schedule Changes
            </h4>


            <p class="meta">

                OR-Tools compared the baseline
                schedule with the recovery schedule.

            </p>


            ${
                changes.length
                    ? `

                        <div
                            style="
                                overflow-x:auto;
                                margin-top:12px;
                            "
                        >

                            <table
                                style="
                                    width:100%;
                                    border-collapse:collapse;
                                "
                            >

                                <thead>

                                    <tr>

                                        <th>
                                            Order
                                        </th>

                                        <th>
                                            Product
                                        </th>

                                        <th>
                                            Step
                                        </th>

                                        <th>
                                            Before
                                        </th>

                                        <th>
                                            After
                                        </th>

                                        <th>
                                            Old Start
                                        </th>

                                        <th>
                                            New Start
                                        </th>

                                        <th>
                                            Status
                                        </th>

                                    </tr>

                                </thead>


                                <tbody>

                                    ${rows}

                                </tbody>

                            </table>

                        </div>

                    `
                    : ""
            }


            ${
                summary.length
                    ? `

                        <h4>
                            Change Summary
                        </h4>

                        <ul>

                            ${summary
                                .map(
                                    (item) =>
                                        `<li>${item}</li>`
                                )
                                .join("")}

                        </ul>

                    `
                    : ""
            }

        </div>

    `;
}


// ============================================================
// RECOVERY PLAN RENDERER
// ============================================================

function renderRecoveryPlan(result) {

    const plan =
        result.plan || [];


    if (!plan.length) {

        return `

            <div class="insight">

                <b>
                    Recovery Schedule
                </b>

                <br>

                No recovery operations
                were returned.

            </div>

        `;
    }


    return `

        <div class="recovery-section">

            <h4>
                📅 Recovery Production Schedule
            </h4>


            <p class="meta">

                Optimized schedule generated
                by OR-Tools CP-SAT.

            </p>


            <div
                style="
                    overflow-x:auto;
                    max-height:420px;
                    overflow-y:auto;
                "
            >

                <table
                    style="
                        width:100%;
                        border-collapse:collapse;
                    "
                >

                    <thead>

                        <tr>

                            <th>
                                Order
                            </th>

                            <th>
                                Product
                            </th>

                            <th>
                                Machine
                            </th>

                            <th>
                                Step
                            </th>

                            <th>
                                Start
                            </th>

                            <th>
                                End
                            </th>

                            <th>
                                Duration
                            </th>

                            <th>
                                Status
                            </th>

                        </tr>

                    </thead>


                    <tbody>

                        ${plan
                            .map((p) => `

                                <tr>

                                    <td>
                                        ${p.order_code}
                                    </td>

                                    <td>
                                        ${p.product}
                                    </td>

                                    <td>
                                        ${p.machine}
                                    </td>

                                    <td>
                                        ${p.step}
                                    </td>

                                    <td>
                                        ${p.start_hour}h
                                    </td>

                                    <td>
                                        ${p.end_hour}h
                                    </td>

                                    <td>
                                        ${p.hours}h
                                    </td>

                                    <td>

                                        ${
                                            p.feasible
                                                ? "ON TIME"
                                                : "DELAY"
                                        }

                                    </td>

                                </tr>

                            `)
                            .join("")}

                    </tbody>

                </table>

            </div>

        </div>

    `;
}


// ============================================================
// FAILURE RESULT
// ============================================================

function renderFailureResult(
    result,
    title = "Machine Failure Simulation"
) {

    lastSimulation =
        result;


    const k =
        result.kpis || {};


    const impact =
        result.impact || {};


    const baselineEfficiency =
        base?.kpis?.efficiency ??
        "N/A";


    const delayed =
        impact.delayed_orders ||
        [];


    const actions =
        impact.recovery_actions ||
        [];


    const affectedOrders =
        impact.affected_orders ||
        [];


    const scheduleChanges =
        result.schedule_changes ||
        impact.schedule_changes ||
        [];


    const recoveryPlan =
        result.plan ||
        [];


    $("sim").innerHTML = `

        <h3>
            ${title}
        </h3>


        <p>

            <b>
                Machine:
            </b>

            ${result.failed_machine}

        </p>


        <p>

            <b>
                Failure Duration:
            </b>

            ${result.failure_hours}
            hours

        </p>


        <hr>


        <p>

            <b>
                Baseline Efficiency:
            </b>

            ${baselineEfficiency}%

        </p>


        <p>

            <b>
                Scenario Efficiency:
            </b>

            ${k.efficiency ?? "N/A"}%

        </p>


        <p>

            <b>
                Delay Risk:
            </b>

            ${k.delay_risk ?? 0}%

        </p>


        <p>

            <b>
                Lost Capacity:
            </b>

            ${
                impact.lost_capacity_hours ??
                0
            }
            hours

        </p>


        <p>

            <b>
                Overtime:
            </b>

            ${k.overtime_hours ?? 0}
            hours

        </p>


        <h4>
            Impact Analysis
        </h4>


        <p>

            <b>
                Affected Orders:
            </b>

            ${
                affectedOrders.length
                    ? affectedOrders.join(", ")
                    : "None"
            }

        </p>


        <p>

            <b>
                Delayed Orders:
            </b>

            ${
                delayed.length
                    ? delayed
                        .map(
                            (d) =>
                                `${d.order_code} (+${d.delay_hours}h)`
                        )
                        .join(", ")
                    : "None"
            }

        </p>


        <h4>
            Recovery Actions
        </h4>


        <ul>

            ${
                actions.length
                    ? actions
                        .map(
                            (a) =>
                                `<li>${a}</li>`
                        )
                        .join("")
                    : "<li>No recovery actions returned.</li>"
            }

        </ul>


        <p class="meta">

            Solver:
            ${result.solver ?? "OR-Tools CP-SAT"}

            ·

            Status:
            ${result.solver_status ?? "UNKNOWN"}

        </p>


        <!-- =========================================
             SCHEDULE CHANGES
             ========================================= -->

        ${
            scheduleChanges.length ||
            result.change_summary?.length ||
            impact.change_summary?.length
                ? renderScheduleChanges(result)
                : `
                    <div class="insight">

                        <b>
                            Schedule Changes
                        </b>

                        <br>

                        No reassignment or
                        timing changes were required.

                    </div>
                `
        }


        <!-- =========================================
             RECOVERY PLAN
             ========================================= -->

        ${
            recoveryPlan.length
                ? renderRecoveryPlan(result)
                : ""
        }

    `;
}


// ============================================================
// SIMULATE FAILURE
// ============================================================

async function simulate() {

    try {

        const payload = {

            machine_code:
                $("fm").value,

            failure_hours:
                +$("fh").value,

        };


        const result =
            await api(
                "/api/simulate-failure",
                {

                    method: "POST",

                    body:
                        JSON.stringify(
                            payload
                        ),

                }
            );


        renderFailureResult(
            result,
            "Machine Failure Simulation"
        );

    } catch (error) {

        $("sim").innerHTML = `

            <b>
                Simulation failed:
            </b>

            ${error.message}

        `;
    }
}


// ============================================================
// RE-OPTIMIZE
// ============================================================

async function reoptimize() {

    try {

        const payload = {

            machine_code:
                $("fm").value,

            failure_hours:
                +$("fh").value,

        };


        const result =
            await api(
                "/api/reoptimize",
                {

                    method: "POST",

                    body:
                        JSON.stringify(
                            payload
                        ),

                }
            );


        renderFailureResult(
            result,
            "⚡ OR-Tools Recovery Schedule"
        );


        const recoveryMessage =
            result.recovery_summary?.message ||
            "OR-Tools generated a new recovery schedule after the machine failure.";


        $("sim").innerHTML += `

            <div
                class="insight"
                style="
                    margin-top:20px;
                "
            >

                <b>
                    ✅ Recovery Complete
                </b>

                <br>

                ${recoveryMessage}

            </div>

        `;

    } catch (error) {

        $("sim").innerHTML = `

            <b>
                Re-optimization failed:
            </b>

            ${error.message}

        `;
    }
}


// ============================================================
// AI ASSISTANT
// ============================================================

async function ask() {

    const question =
        $("q").value.trim();


    if (!question)
        return;


    $("chat").innerHTML += `

        <div class="bubble">

            <b>
                You:
            </b>

            ${question}

        </div>

    `;


    try {

        const response =
            await api(
                "/api/assistant",
                {

                    method: "POST",

                    body:
                        JSON.stringify({
                            question
                        }),

                }
            );


        const evidence =
            Array.isArray(
                response.evidence
            )
                ? response.evidence.join(
                    " • "
                )
                : "";


        $("chat").innerHTML += `

            <div class="bubble">

                <b>
                    FactoryMind AI:
                </b>

                <br>

                ${response.answer}

                ${
                    evidence
                        ? `
                            <br>

                            <small>
                                ${evidence}
                            </small>
                        `
                        : ""
                }

            </div>

        `;


        $("chat").scrollTop =
            $("chat").scrollHeight;


    } catch (error) {

        $("chat").innerHTML += `

            <div class="bubble">

                <b>
                    FactoryMind AI:
                </b>

                <br>

                ${error.message}

            </div>

        `;
    }


    $("q").value = "";
}


// ============================================================
// STARTUP MESSAGE
// ============================================================

console.log(
    "FactoryMind AI frontend loaded successfully."
);