"""FactoryMind production scheduling and failure-impact analysis.

Uses OR-Tools CP-SAT to:

- keep operations in route order
- prevent machine clashes
- model temporary machine outages
- reassign operations to compatible machines
- penalize deadline misses
- penalize overtime
- compare baseline and recovery schedules
- identify affected orders
- identify rescheduled operations
- quantify lost capacity
- calculate baseline and scenario KPIs
"""

from collections import defaultdict

from ortools.sat.python import cp_model

from .database import get_conn


PLANNING_HOURS = 72
PLANNING_MINUTES = PLANNING_HOURS * 60


# ============================================================
# LOAD FACTORY DATA
# ============================================================

def _load_factory_data():

    connection = get_conn()

    try:

        machines = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM machines ORDER BY code"
            ).fetchall()
        ]

        orders = [
            dict(row)
            for row in connection.execute(
                """
                SELECT *
                FROM orders
                ORDER BY priority, deadline_hours
                """
            ).fetchall()
        ]

        routes = [
            dict(row)
            for row in connection.execute(
                """
                SELECT *
                FROM routes
                ORDER BY product, sequence
                """
            ).fetchall()
        ]

    finally:

        connection.close()

    return machines, orders, routes


# ============================================================
# CALCULATE EFFICIENCY
# ============================================================

def _calculate_efficiency(
    utilization,
    delay_risk,
    overtime_hours
):

    if not utilization:

        return 0.0

    max_utilization = max(
        (
            float(item.get("utilization", 0))
            for item in utilization
        ),
        default=0.0
    )

    bottleneck_penalty = (
        max(
            0.0,
            max_utilization - 85.0
        )
        * 0.12
    )

    delay_penalty = (
        float(delay_risk)
        * 0.45
    )

    overtime_penalty = (
        float(overtime_hours)
        * 0.8
    )

    efficiency = (
        100.0
        - bottleneck_penalty
        - delay_penalty
        - overtime_penalty
    )

    return max(
        0.0,
        min(
            100.0,
            efficiency
        )
    )


# ============================================================
# GENERATE PLAN
# ============================================================

def generate_plan(
    failed_machine=None,
    failure_hours=0
):

    """
    Generate baseline or recovery schedule.

    Baseline:

        generate_plan()

    Failure simulation:

        generate_plan(
            failed_machine="CNC-01",
            failure_hours=6
        )

    The failed machine is unavailable during:

        [0, failure_hours]

    After the outage the machine becomes available again.
    """

    machines, orders, routes = _load_factory_data()

    # --------------------------------------------------------
    # Normalize failure input
    # --------------------------------------------------------

    try:

        failure_hours = float(
            failure_hours or 0
        )

    except (
        TypeError,
        ValueError
    ):

        failure_hours = 0.0

    failure_hours = max(
        0.0,
        failure_hours
    )

    if not failed_machine:

        failure_hours = 0.0

    # --------------------------------------------------------
    # Machine lookup
    # --------------------------------------------------------

    machine_by_code = {
        machine["code"]: machine
        for machine in machines
    }

    if (
        failed_machine
        and failed_machine not in machine_by_code
    ):

        raise ValueError(
            f"Unknown machine: {failed_machine}"
        )

    # --------------------------------------------------------
    # Group routes by product
    # --------------------------------------------------------

    route_by_product = defaultdict(list)

    for route in routes:

        route_by_product[
            route["product"]
        ].append(route)

    for product in route_by_product:

        route_by_product[
            product
        ].sort(
            key=lambda item:
            item["sequence"]
        )

    # --------------------------------------------------------
    # Group machines by machine type
    # --------------------------------------------------------

    machines_by_type = defaultdict(list)

    for machine in machines:

        machines_by_type[
            machine["machine_type"]
        ].append(machine)

    # ========================================================
    # CP-SAT MODEL
    # ========================================================

    model = cp_model.CpModel()

    operations = []

    # ========================================================
    # CREATE OPERATION VARIABLES
    # ========================================================

    for order_index, order in enumerate(orders):

        steps = route_by_product.get(
            order["product"],
            []
        )

        for step in steps:

            candidates = machines_by_type.get(
                step["machine_type"],
                []
            )

            if not candidates:

                continue

            # ------------------------------------------------
            # Duration
            # ------------------------------------------------

            duration = int(
                round(
                    float(order["quantity"])
                    *
                    float(step["hours_per_unit"])
                    *
                    60
                )
            )

            duration = max(
                1,
                min(
                    PLANNING_MINUTES - 1,
                    duration
                )
            )

            # ------------------------------------------------
            # Start / End variables
            # ------------------------------------------------

            start = model.NewIntVar(
                0,
                PLANNING_MINUTES - duration,
                (
                    f"start_"
                    f"{order_index}_"
                    f"{step['sequence']}"
                )
            )

            end = model.NewIntVar(
                0,
                PLANNING_MINUTES,
                (
                    f"end_"
                    f"{order_index}_"
                    f"{step['sequence']}"
                )
            )

            model.Add(
                end == start + duration
            )

            choices = []

            # =================================================
            # MACHINE ASSIGNMENT
            # =================================================

            for candidate_index, machine in enumerate(
                candidates
            ):

                selected = model.NewBoolVar(
                    (
                        f"machine_"
                        f"{order_index}_"
                        f"{step['sequence']}_"
                        f"{candidate_index}"
                    )
                )

                choices.append(
                    (
                        selected,
                        machine
                    )
                )

                # ------------------------------------------------
                # FAILURE CONSTRAINT
                # ------------------------------------------------

                if (
                    failed_machine
                    and machine["code"]
                    == failed_machine
                    and failure_hours > 0
                ):

                    downtime_minutes = int(
                        round(
                            failure_hours * 60
                        )
                    )

                    # If this machine is selected,
                    # operation must start after outage.
                    model.Add(
                        start
                        >=
                        downtime_minutes
                        -
                        PLANNING_MINUTES
                        *
                        (
                            1 - selected
                        )
                    )

            # Exactly one machine
            model.Add(
                sum(
                    selected
                    for selected, _
                    in choices
                )
                == 1
            )

            operations.append(
                {
                    "order_index":
                        order_index,

                    "order":
                        order,

                    "step":
                        step,

                    "start":
                        start,

                    "end":
                        end,

                    "duration":
                        duration,

                    "choices":
                        choices,
                }
            )

    # ========================================================
    # ROUTE PRECEDENCE
    # ========================================================

    operations_by_order = defaultdict(list)

    for operation in operations:

        operations_by_order[
            operation["order_index"]
        ].append(operation)

    for order_operations in (
        operations_by_order.values()
    ):

        order_operations.sort(
            key=lambda item:
            item["step"]["sequence"]
        )

        for previous, current in zip(
            order_operations,
            order_operations[1:]
        ):

            model.Add(
                current["start"]
                >=
                previous["end"]
            )

    # ========================================================
    # MACHINE COLLISION CONSTRAINTS
    # ========================================================

    machine_intervals = defaultdict(list)

    for operation in operations:

        for selected, machine in (
            operation["choices"]
        ):

            interval = (
                model.NewOptionalIntervalVar(
                    operation["start"],
                    operation["duration"],
                    operation["end"],
                    selected,
                    (
                        f"interval_"
                        f"{machine['code']}_"
                        f"{operation['order_index']}_"
                        f"{operation['step']['sequence']}"
                    )
                )
            )

            machine_intervals[
                machine["code"]
            ].append(
                interval
            )

    for intervals in (
        machine_intervals.values()
    ):

        model.AddNoOverlap(
            intervals
        )

    # ========================================================
    # OBJECTIVE
    # ========================================================

    objective_terms = []

    final_end_by_order = {}

    for order_index, order_operations in (
        operations_by_order.items()
    ):

        if not order_operations:

            continue

        last_operation = max(
            order_operations,
            key=lambda item:
            item["step"]["sequence"]
        )

        final_end_by_order[
            order_index
        ] = last_operation["end"]

        deadline_minutes = int(
            round(
                float(
                    last_operation["order"][
                        "deadline_hours"
                    ]
                )
                * 60
            )
        )

        lateness = model.NewIntVar(
            0,
            PLANNING_MINUTES,
            f"lateness_{order_index}"
        )

        model.Add(
            lateness
            >=
            last_operation["end"]
            -
            deadline_minutes
        )

        model.Add(
            lateness >= 0
        )

        priority_weight = max(
            1,
            5 -
            int(order["priority"])
        )

        # Early completion preferred
        objective_terms.append(
            last_operation["end"]
            *
            priority_weight
        )

        # Strong deadline penalty
        objective_terms.append(
            lateness
            *
            2500
            *
            priority_weight
        )

    # ========================================================
    # MACHINE LOAD / OVERTIME
    # ========================================================

    overtime_vars = {}

    for machine in machines:

        terms = []

        for operation in operations:

            for selected, candidate in (
                operation["choices"]
            ):

                if (
                    candidate["code"]
                    ==
                    machine["code"]
                ):

                    terms.append(
                        operation["duration"]
                        *
                        selected
                    )

        used_expr = (
            sum(terms)
            if terms
            else 0
        )

        capacity_minutes = int(
            round(
                float(
                    machine[
                        "available_hours"
                    ]
                )
                * 60
            )
        )

        overtime = model.NewIntVar(
            0,
            PLANNING_MINUTES,
            (
                f"overtime_"
                f"{machine['code']}"
            )
        )

        model.Add(
            overtime
            >=
            used_expr
            -
            capacity_minutes
        )

        model.Add(
            overtime >= 0
        )

        overtime_vars[
            machine["code"]
        ] = overtime

        objective_terms.append(
            overtime * 20
        )

    # ========================================================
    # MINIMIZE
    # ========================================================

    if objective_terms:

        model.Minimize(
            sum(objective_terms)
        )

    # ========================================================
    # SOLVER
    # ========================================================

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = 5

    solver.parameters.num_search_workers = 8

    solver.parameters.random_seed = 42

    status = solver.Solve(
        model
    )

    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE
    ):

        raise RuntimeError(
            "OR-Tools could not produce "
            "a schedule: "
            f"{solver.StatusName(status)}"
        )

    # ========================================================
    # CONVERT SOLUTION
    # ========================================================

    planned_operations = []

    used_hours = defaultdict(float)

    order_completion_hours = {}

    for operation in operations:

        selected_machine = None

        for selected, machine in (
            operation["choices"]
        ):

            if solver.Value(
                selected
            ):

                selected_machine = machine

                break

        if selected_machine is None:

            continue

        start_hour = (
            solver.Value(
                operation["start"]
            )
            / 60
        )

        end_hour = (
            solver.Value(
                operation["end"]
            )
            / 60
        )

        hours = (
            operation["duration"]
            / 60
        )

        machine_code = (
            selected_machine[
                "code"
            ]
        )

        used_hours[
            machine_code
        ] += hours

        order_index = (
            operation[
                "order_index"
            ]
        )

        order_completion_hours[
            order_index
        ] = max(
            order_completion_hours.get(
                order_index,
                0
            ),
            end_hour
        )

        deadline = float(
            operation["order"][
                "deadline_hours"
            ]
        )

        planned_operations.append(
            {
                "order_code":
                    operation["order"][
                        "order_code"
                    ],

                "product":
                    operation["order"][
                        "product"
                    ],

                "machine":
                    machine_code,

                "machine_type":
                    selected_machine[
                        "machine_type"
                    ],

                "step":
                    operation["step"][
                        "sequence"
                    ],

                "start_hour":
                    round(
                        start_hour,
                        2
                    ),

                "end_hour":
                    round(
                        end_hour,
                        2
                    ),

                "hours":
                    round(
                        hours,
                        2
                    ),

                "deadline_hours":
                    deadline,

                "priority":
                    operation["order"][
                        "priority"
                    ],

                "feasible":
                    end_hour <= deadline,
            }
        )

    # ========================================================
    # BASELINE VS RECOVERY
    # ========================================================

    baseline_result = None

    baseline_plan = []

    baseline_kpis = {}

    schedule_changes = []

    affected_orders = []

    if (
        failed_machine
        and failure_hours > 0
    ):

        try:

            baseline_result = generate_plan()

            baseline_plan = (
                baseline_result.get(
                    "plan",
                    []
                )
            )

            baseline_kpis = (
                baseline_result.get(
                    "kpis",
                    {}
                )
            )

        except Exception:

            baseline_result = None

            baseline_plan = []

            baseline_kpis = {}

    # ========================================================
    # BASELINE MAP
    # ========================================================

    baseline_map = {}

    for item in baseline_plan:

        key = (
            item.get("order_code"),
            item.get("step", 0)
        )

        baseline_map[
            key
        ] = item

    # ========================================================
    # AFFECTED ORDERS
    #
    # IMPORTANT:
    # Use BASELINE schedule here.
    #
    # This identifies orders that were originally
    # dependent on the failed machine.
    # ========================================================

    if (
        failed_machine
        and baseline_plan
    ):

        affected_orders = sorted(
            {
                item["order_code"]
                for item in baseline_plan
                if item.get(
                    "machine"
                )
                ==
                failed_machine
            }
        )

    # ========================================================
    # COMPARE BASELINE / RECOVERY
    # ========================================================

    for item in planned_operations:

        key = (
            item.get("order_code"),
            item.get("step", 0)
        )

        baseline_item = (
            baseline_map.get(key)
        )

        if not baseline_item:

            continue

        old_machine = (
            baseline_item.get(
                "machine"
            )
        )

        new_machine = (
            item.get(
                "machine"
            )
        )

        old_start = (
            baseline_item.get(
                "start_hour"
            )
        )

        new_start = (
            item.get(
                "start_hour"
            )
        )

        old_end = (
            baseline_item.get(
                "end_hour"
            )
        )

        new_end = (
            item.get(
                "end_hour"
            )
        )

        # ----------------------------------------------------
        # Machine changed
        # ----------------------------------------------------

        if old_machine != new_machine:

            schedule_changes.append(
                {
                    "order_code":
                        item.get(
                            "order_code"
                        ),

                    "product":
                        item.get(
                            "product"
                        ),

                    "step":
                        item.get(
                            "step"
                        ),

                    "before_machine":
                        old_machine,

                    "after_machine":
                        new_machine,

                    "before_start_hour":
                        old_start,

                    "after_start_hour":
                        new_start,

                    "before_end_hour":
                        old_end,

                    "after_end_hour":
                        new_end,

                    "status":
                        "Reassigned"
                }
            )

        # ----------------------------------------------------
        # Same machine but timing changed
        # ----------------------------------------------------

        elif (
            old_start is not None
            and new_start is not None
            and abs(
                float(old_start)
                -
                float(new_start)
            ) > 0.01
        ):

            schedule_changes.append(
                {
                    "order_code":
                        item.get(
                            "order_code"
                        ),

                    "product":
                        item.get(
                            "product"
                        ),

                    "step":
                        item.get(
                            "step"
                        ),

                    "before_machine":
                        old_machine,

                    "after_machine":
                        new_machine,

                    "before_start_hour":
                        old_start,

                    "after_start_hour":
                        new_start,

                    "before_end_hour":
                        old_end,

                    "after_end_hour":
                        new_end,

                    "status":
                        "Rescheduled"
                }
            )

    # ========================================================
    # MACHINE UTILIZATION
    # ========================================================

    utilization = []

    estimated_cost = 0.0

    total_overtime = 0.0

    for machine in machines:

        base_available = float(
            machine[
                "available_hours"
            ]
        )

        lost_capacity = (
            min(
                base_available,
                failure_hours
            )
            if (
                failed_machine
                and machine["code"]
                ==
                failed_machine
            )
            else 0.0
        )

        effective_available = max(
            0.0,
            base_available
            -
            lost_capacity
        )

        used = used_hours[
            machine["code"]
        ]

        overtime = max(
            0.0,
            used
            -
            effective_available
        )

        utilization_percent = (
            100.0
            *
            used
            /
            effective_available
            if effective_available > 0
            else 0.0
        )

        utilization.append(
            {
                "machine":
                    machine["code"],

                "name":
                    machine["name"],

                "used_hours":
                    round(
                        used,
                        2
                    ),

                "available_hours":
                    round(
                        effective_available,
                        2
                    ),

                "base_available_hours":
                    round(
                        base_available,
                        2
                    ),

                "lost_capacity_hours":
                    round(
                        lost_capacity,
                        2
                    ),

                "overtime_hours":
                    round(
                        overtime,
                        2
                    ),

                "utilization":
                    round(
                        utilization_percent,
                        1
                    ),

                "status":
                    (
                        "Failure Simulated"
                        if (
                            failed_machine
                            and
                            machine["code"]
                            ==
                            failed_machine
                        )
                        else
                        machine["status"]
                    ),
            }
        )

        estimated_cost += (
            used
            *
            float(
                machine[
                    "cost_per_hour"
                ]
            )
        )

        total_overtime += overtime

    # ========================================================
    # ORDER DELAY ANALYSIS
    # ========================================================

    delayed_orders = []

    for index, order in enumerate(
        orders
    ):

        completion = (
            order_completion_hours.get(
                index
            )
        )

        if completion is None:

            delayed_orders.append(
                {
                    "order_code":
                        order[
                            "order_code"
                        ],

                    "deadline_hours":
                        order[
                            "deadline_hours"
                        ],

                    "completion_hours":
                        None,

                    "delay_hours":
                        None,
                }
            )

            continue

        deadline = float(
            order[
                "deadline_hours"
            ]
        )

        delay_hours = max(
            0.0,
            completion
            -
            deadline
        )

        if delay_hours > 0:

            delayed_orders.append(
                {
                    "order_code":
                        order[
                            "order_code"
                        ],

                    "deadline_hours":
                        deadline,

                    "completion_hours":
                        round(
                            completion,
                            2
                        ),

                    "delay_hours":
                        round(
                            delay_hours,
                            2
                        ),
                }
            )

    delayed_order_count = len(
        delayed_orders
    )

    total_orders = max(
        1,
        len(orders)
    )

    delay_risk = (
        100.0
        *
        delayed_order_count
        /
        total_orders
    )

    # ========================================================
    # UTILIZATION METRICS
    # ========================================================

    average_utilization = (

        sum(
            item["utilization"]
            for item in utilization
        )
        /
        len(utilization)

        if utilization

        else 0.0
    )

    # ========================================================
    # SCENARIO EFFICIENCY
    # ========================================================

    efficiency = _calculate_efficiency(
        utilization,
        delay_risk,
        total_overtime
    )

    # ========================================================
    # BASELINE EFFICIENCY
    # ========================================================

    baseline_efficiency = (
        float(
            baseline_kpis.get(
                "efficiency",
                efficiency
            )
        )
        if baseline_kpis
        else efficiency
    )

    # ========================================================
    # FAILURE CAPACITY
    # ========================================================

    failed_machine_record = (
        machine_by_code.get(
            failed_machine
        )
    )

    if (
        failed_machine_record
        and failed_machine
    ):

        lost_capacity_total = min(
            float(
                failed_machine_record[
                    "available_hours"
                ]
            ),
            failure_hours
        )

    else:

        lost_capacity_total = 0.0

    # ========================================================
    # CHANGE SUMMARY
    # ========================================================

    change_summary = []

    for change in schedule_changes:

        change_summary.append(
            (
                f"{change['order_code']} "
                f"({change.get('product', 'N/A')}) "
                f"Step "
                f"{change.get('step', 'N/A')}: "
                f"{change['before_machine']} "
                f"-> "
                f"{change['after_machine']} "
                f""
                f"({change['status']})"
            )
        )

    # ========================================================
    # RECOVERY ACTIONS
    # ========================================================

    if failed_machine:

        recovery_actions = [

            (
                f"Protect {failed_machine} "
                f"from new work during "
                f"the {failure_hours:g}-hour outage."
            ),

            (
                "Prioritize high-priority "
                "orders in the recovery schedule."
            ),

            (
                "Move compatible operations "
                "to parallel machines where "
                "capacity exists."
            ),

            (
                "Re-optimize the production "
                "schedule after the failure."
            ),

            (
                "Use controlled overtime "
                "when required to protect "
                "deadlines."
            ),
        ]

    else:

        recovery_actions = [

            "No failure scenario is active.",

            "Run the baseline "
            "OR-Tools schedule."
        ]

    # ========================================================
    # IMPACT STATUS
    # ========================================================

    if delayed_order_count > 0:

        impact_status = "CRITICAL"

    elif schedule_changes:

        impact_status = "RECOVERED"

    elif failed_machine:

        impact_status = "LOW IMPACT"

    else:

        impact_status = "BASELINE"

    # ========================================================
    # RETURN RESULT
    # ========================================================

    return {

        # ----------------------------------------------------
        # Production plan
        # ----------------------------------------------------

        "plan":
            sorted(
                planned_operations,
                key=lambda item:
                (
                    item["start_hour"],
                    item["machine"]
                )
            ),

        # ----------------------------------------------------
        # Machine utilization
        # ----------------------------------------------------

        "machine_utilization":
            utilization,

        # ----------------------------------------------------
        # KPIs
        # ----------------------------------------------------

        "kpis": {

            "total_orders":
                len(orders),

            "planned_operations":
                len(
                    planned_operations
                ),

            "estimated_cost":
                round(
                    estimated_cost,
                    2
                ),

            "estimated_hours":
                round(
                    sum(
                        item["hours"]
                        for item
                        in planned_operations
                    ),
                    2
                ),

            "average_utilization":
                round(
                    average_utilization,
                    1
                ),

            "efficiency":
                round(
                    efficiency,
                    1
                ),

            "delay_risk":
                round(
                    delay_risk,
                    1
                ),

            "delayed_operations":
                delayed_order_count,

            "delayed_orders":
                delayed_order_count,

            "overtime_hours":
                round(
                    total_overtime,
                    2
                ),
        },

        # ----------------------------------------------------
        # Baseline vs Scenario
        # ----------------------------------------------------

        "baseline": {

            "efficiency":
                round(
                    baseline_efficiency,
                    1
                ),

            "delay_risk":
                round(
                    float(
                        baseline_kpis.get(
                            "delay_risk",
                            0
                        )
                    ),
                    1
                ),

            "plan":
                baseline_plan,
        },

        "scenario": {

            "efficiency":
                round(
                    efficiency,
                    1
                ),

            "delay_risk":
                round(
                    delay_risk,
                    1
                ),

            "plan":
                sorted(
                    planned_operations,
                    key=lambda item:
                    (
                        item["start_hour"],
                        item["machine"]
                    )
                ),
        },

        # ----------------------------------------------------
        # Schedule changes
        # ----------------------------------------------------

        "schedule_changes":
            schedule_changes,

        "change_summary":
            change_summary,

        # ----------------------------------------------------
        # Failure impact
        # ----------------------------------------------------

        "impact": {

            "failed_machine":
                failed_machine,

            "failure_hours":
                round(
                    failure_hours,
                    2
                ),

            "baseline_efficiency":
                round(
                    baseline_efficiency,
                    1
                ),

            "scenario_efficiency":
                round(
                    efficiency,
                    1
                ),

            "efficiency_change":
                round(
                    efficiency
                    -
                    baseline_efficiency,
                    1
                ),

            "baseline_delay_risk":
                round(
                    float(
                        baseline_kpis.get(
                            "delay_risk",
                            0
                        )
                    ),
                    1
                ),

            "scenario_delay_risk":
                round(
                    delay_risk,
                    1
                ),

            "lost_capacity_hours":
                round(
                    lost_capacity_total,
                    2
                ),

            "affected_orders":
                affected_orders,

            "affected_order_count":
                len(
                    affected_orders
                ),

            "delayed_orders":
                delayed_orders,

            "delayed_order_count":
                delayed_order_count,

            "schedule_changes":
                schedule_changes,

            "change_count":
                len(
                    schedule_changes
                ),

            "impact_status":
                impact_status,

            "recovery_actions":
                recovery_actions,
        },

        # ----------------------------------------------------
        # Solver
        # ----------------------------------------------------

        "solver":
            "OR-Tools CP-SAT",

        "solver_status":
            solver.StatusName(
                status
            ),

        # ----------------------------------------------------
        # Scenario information
        # ----------------------------------------------------

        "failed_machine":
            failed_machine,

        "failure_hours":
            round(
                failure_hours,
                2
            ),
    }