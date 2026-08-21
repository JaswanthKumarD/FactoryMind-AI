import re

from .database import get_conn
from .optimizer import generate_plan


def answer(question):
    """
    FactoryMind AI Assistant

    Supports:
    - Bottleneck analysis
    - Urgent orders
    - Delay analysis
    - Machine utilization
    - Factory efficiency
    - Machine failure / maintenance risk
    - Production orders
    - Factory status
    - What-if machine failure simulation
    """

    # =========================================================
    # 1. CLEAN QUESTION
    # =========================================================

    if question is None:
        question = ""

    q = str(question).lower().strip()

    # =========================================================
    # 2. LOAD CURRENT FACTORY PLAN
    # =========================================================

    try:
        base = generate_plan()
    except Exception as e:
        return {
            "answer": "Unable to load the current factory plan.",
            "evidence": [
                f"System error: {str(e)}"
            ]
        }

    if not isinstance(base, dict):
        return {
            "answer": "Factory planning data is not available.",
            "evidence": []
        }

    kpis = base.get("kpis", {})
    machines = base.get("machine_utilization", [])
    plan = base.get("plan", [])

    if not isinstance(kpis, dict):
        kpis = {}

    if not isinstance(machines, list):
        machines = []

    if not isinstance(plan, list):
        plan = []

    # =========================================================
    # HELPER FUNCTIONS
    # =========================================================

    def get_utilization(machine):
        try:
            return float(machine.get("utilization", 0))
        except (TypeError, ValueError):
            return 0.0

    def get_priority(operation):
        try:
            return int(operation.get("priority", 99))
        except (TypeError, ValueError):
            return 99

    def get_machine_name(machine):
        return (
            machine.get("machine")
            or machine.get("machine_code")
            or machine.get("name")
            or "Unknown Machine"
        )

    def get_order_code(operation):
        return (
            operation.get("order_code")
            or operation.get("order")
            or operation.get("order_id")
            or "Unknown Order"
        )

    def get_product(operation):
        return (
            operation.get("product")
            or operation.get("product_name")
            or "Unknown Product"
        )

    def to_float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def machine_matches(operation, machine_name):
        """
        Check whether an operation belongs to the selected machine.
        """

        op_machine = (
            operation.get("machine")
            or operation.get("machine_code")
            or operation.get("machine_name")
            or ""
        )

        return str(op_machine).strip().lower() == str(
            machine_name
        ).strip().lower()

    def extract_machine_from_question(question_text):
        """
        Detect machine code such as:
        GR-01
        CNC-01
        CNC-02
        HT-01
        """

        match = re.search(
            r"\b(?:cnc|gr|ht)[-_ ]?\d{1,3}\b",
            question_text,
            re.IGNORECASE
        )

        if match:
            raw = match.group(0).upper()
            raw = raw.replace(" ", "-")

            # Convert CNC01 -> CNC-01
            match2 = re.match(
                r"([A-Z]+)-?(\d+)",
                raw
            )

            if match2:
                return f"{match2.group(1)}-{match2.group(2).zfill(2)}"

            return raw

        return None

    def extract_failure_hours(question_text):
        """
        Detect:
        6 hours
        6 hour
        for 6h
        6h
        """

        patterns = [
            r"(\d+(?:\.\d+)?)\s*hours?",
            r"(\d+(?:\.\d+)?)\s*hrs?",
            r"(\d+(?:\.\d+)?)\s*h\b"
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                question_text,
                re.IGNORECASE
            )

            if match:
                return to_float(match.group(1), 1.0)

        # If user says "fails" but gives no duration
        return 1.0

    def find_machine(machine_code):
        """
        Find exact machine from current machine data.
        """

        if not machine_code:
            return None

        for machine in machines:

            name = get_machine_name(machine)

            if str(name).lower() == str(machine_code).lower():
                return machine

            code = str(
                machine.get("machine_code", "")
            ).lower()

            if code == str(machine_code).lower():
                return machine

        return None

    # =========================================================
    # 3. WHAT-IF MACHINE FAILURE
    #
    # IMPORTANT:
    # This section MUST appear BEFORE generic failure analysis.
    # =========================================================

    is_what_if = any(
        phrase in q
        for phrase in [
            "what if",
            "what happens if",
            "what will happen if",
            "if it fails",
            "fails for",
            "failure for",
            "shutdown for",
            "downtime for",
            "breaks down for",
            "breakdown for"
        ]
    )

    if is_what_if:

        # -----------------------------------------------------
        # Detect requested machine
        # -----------------------------------------------------

        requested_machine = extract_machine_from_question(q)

        # -----------------------------------------------------
        # Detect requested downtime
        # -----------------------------------------------------

        downtime_hours = extract_failure_hours(q)

        # -----------------------------------------------------
        # If no machine specified, use current bottleneck
        # -----------------------------------------------------

        if requested_machine:

            selected_machine = find_machine(
                requested_machine
            )

        else:

            if machines:
                selected_machine = max(
                    machines,
                    key=get_utilization
                )
                requested_machine = get_machine_name(
                    selected_machine
                )
            else:
                selected_machine = None

        # -----------------------------------------------------
        # Machine not found
        # -----------------------------------------------------

        if selected_machine is None:

            available = [
                get_machine_name(machine)
                for machine in machines
            ]

            return {
                "answer": (
                    f"I could not find machine "
                    f"{requested_machine or 'requested machine'} "
                    f"in the current factory data."
                ),

                "evidence": [
                    "Available machines: "
                    + ", ".join(available)
                ]
            }

        # -----------------------------------------------------
        # Selected machine information
        # -----------------------------------------------------

        machine_name = get_machine_name(
            selected_machine
        )

        utilization = get_utilization(
            selected_machine
        )

        # -----------------------------------------------------
        # Machine capacity information
        # -----------------------------------------------------

        capacity = to_float(
            selected_machine.get("capacity", 0),
            0
        )

        cost = to_float(
            selected_machine.get("cost", 0),
            0
        )

        # -----------------------------------------------------
        # Find operations assigned to this machine
        # -----------------------------------------------------

        affected_operations = [
            operation
            for operation in plan
            if machine_matches(
                operation,
                machine_name
            )
        ]

        # -----------------------------------------------------
        # Unique affected orders
        # -----------------------------------------------------

        affected_orders = {}

        for operation in affected_operations:

            order_code = get_order_code(
                operation
            )

            if order_code not in affected_orders:
                affected_orders[order_code] = operation

        # -----------------------------------------------------
        # Calculate lost production capacity
        # -----------------------------------------------------

        lost_capacity_hours = downtime_hours

        if capacity > 0:
            lost_units = capacity * downtime_hours
        else:
            lost_units = 0

        # -----------------------------------------------------
        # Calculate estimated capacity pressure
        #
        # 16-hour production day is used because the
        # FactoryMind dashboard currently shows 16h/day.
        # -----------------------------------------------------

        working_hours = 16.0

        utilization_loss = (
            downtime_hours / working_hours
        ) * 100

        remaining_utilization = max(
            0,
            utilization - utilization_loss
        )

        # -----------------------------------------------------
        # Estimate additional delay risk
        # -----------------------------------------------------

        delay_risk_before = to_float(
            kpis.get("delay_risk", 0),
            0
        )

        urgent_affected = []

        potentially_delayed = []

        for operation in affected_operations:

            priority = get_priority(
                operation
            )

            deadline = to_float(
                operation.get(
                    "deadline_hours",
                    999999
                ),
                999999
            )

            end_hour = to_float(
                operation.get(
                    "end_hour",
                    0
                ),
                0
            )

            # Approximate new completion time
            new_end = end_hour + downtime_hours

            if priority == 1:
                urgent_affected.append(
                    get_order_code(operation)
                )

            if new_end > deadline:

                potentially_delayed.append(
                    get_order_code(operation)
                )

        # Remove duplicate order codes
        urgent_affected = list(
            dict.fromkeys(urgent_affected)
        )

        potentially_delayed = list(
            dict.fromkeys(potentially_delayed)
        )

        # -----------------------------------------------------
        # Estimate efficiency impact
        # -----------------------------------------------------

        current_efficiency = to_float(
            kpis.get("efficiency", 0),
            0
        )

        estimated_efficiency = max(
            0,
            current_efficiency - utilization_loss
        )

        # -----------------------------------------------------
        # Risk classification
        # -----------------------------------------------------

        if downtime_hours >= 8 or utilization >= 90:
            risk = "CRITICAL"

        elif downtime_hours >= 4 or utilization >= 70:
            risk = "HIGH"

        elif downtime_hours >= 2:
            risk = "MEDIUM"

        else:
            risk = "LOW"

        # -----------------------------------------------------
        # Cost impact
        # -----------------------------------------------------

        estimated_cost_impact = (
            downtime_hours * cost
            if cost > 0
            else 0
        )

        # -----------------------------------------------------
        # Build affected order text
        # -----------------------------------------------------

        if affected_orders:

            affected_text = []

            for order_code, operation in affected_orders.items():

                product = get_product(
                    operation
                )

                affected_text.append(
                    f"{order_code} ({product})"
                )

        else:

            affected_text = []

        # -----------------------------------------------------
        # Build response
        # -----------------------------------------------------

        answer_text = (
            f"If {machine_name} fails for "
            f"{downtime_hours:g} hours, the factory "
            f"will lose approximately "
            f"{lost_capacity_hours:g} hours of machine "
            f"availability."
        )

        if capacity > 0:

            answer_text += (
                f" At its rated capacity of "
                f"{capacity:g} units/hour, this represents "
                f"approximately {lost_units:g} units of "
                f"potential production capacity."
            )

        answer_text += (
            f" {machine_name} currently operates at "
            f"{utilization:.1f}% utilization, so the "
            f"failure creates a {risk} operational risk."
        )

        # -----------------------------------------------------
        # Affected orders
        # -----------------------------------------------------

        if affected_text:

            answer_text += (
                " The affected scheduled orders are "
                + ", ".join(affected_text)
                + "."
            )

        # -----------------------------------------------------
        # Delay information
        # -----------------------------------------------------

        if potentially_delayed:

            answer_text += (
                " Based on the current schedule, "
                "the following orders may miss their "
                "deadlines after adding the downtime: "
                + ", ".join(
                    potentially_delayed
                )
                + "."
            )

        else:

            answer_text += (
                " No currently scheduled operation is "
                "estimated to cross its deadline from "
                "this simple downtime shift."
            )

        # -----------------------------------------------------
        # Urgent orders
        # -----------------------------------------------------

        if urgent_affected:

            answer_text += (
                " Priority-1 work affected by this "
                "machine should be protected first: "
                + ", ".join(
                    urgent_affected
                )
                + "."
            )

        # -----------------------------------------------------
        # Recommendation
        # -----------------------------------------------------

        answer_text += (
            " Recommended action: protect urgent orders, "
            "move compatible operations to alternative "
            "machines where possible, and re-optimize "
            "the production schedule."
        )

        evidence = [
            f"Machine: {machine_name}",
            f"Failure duration: {downtime_hours:g} hours",
            f"Current utilization: {utilization:.1f}%",
            f"Operational risk: {risk}",
            f"Current factory efficiency: {current_efficiency:.1f}%",
            f"Estimated efficiency after downtime: "
            f"{estimated_efficiency:.1f}%",
            f"Estimated lost machine capacity: "
            f"{lost_capacity_hours:g} hours",
        ]

        if capacity > 0:

            evidence.append(
                f"Estimated production capacity affected: "
                f"{lost_units:g} units"
            )

        if cost > 0:

            evidence.append(
                f"Estimated machine downtime cost: "
                f"₹{estimated_cost_impact:,.2f}"
            )

        evidence.append(
            f"Potentially delayed orders: "
            f"{len(potentially_delayed)}"
        )

        evidence.append(
            f"Affected orders: "
            f"{len(affected_orders)}"
        )

        evidence.append(
            "Recommendation: Protect urgent orders "
            "and re-optimize the production schedule."
        )

        return {
            "answer": answer_text,
            "evidence": evidence
        }

    # =========================================================
    # 4. BOTTLENECK ANALYSIS
    # =========================================================

    if any(word in q for word in [
        "bottleneck",
        "bottle neck",
        "busiest",
        "most busy",
        "highest utilization",
        "highest capacity"
    ]):

        if machines:

            bottleneck = max(
                machines,
                key=get_utilization
            )

            machine_name = get_machine_name(
                bottleneck
            )

            utilization = get_utilization(
                bottleneck
            )

            return {
                "answer": (
                    f"{machine_name} is the current bottleneck. "
                    f"It is operating at {utilization:.1f}% utilization, "
                    f"which is the highest among the available machines."
                ),

                "evidence": [
                    f"Machine: {machine_name}",
                    f"Utilization: {utilization:.1f}%",
                    "Recommendation: Protect this machine's capacity "
                    "and prioritize urgent orders."
                ]
            }

        return {
            "answer": (
                "Machine utilization data is currently unavailable, "
                "so I cannot identify the bottleneck."
            ),
            "evidence": []
        }

    # =========================================================
    # 5. URGENT / HIGH PRIORITY ORDERS
    # =========================================================

    if any(word in q for word in [
        "urgent",
        "priority",
        "high priority",
        "important orders",
        "important order"
    ]):

        urgent = [
            operation
            for operation in plan
            if get_priority(operation) == 1
        ]

        unique_orders = {}

        for operation in urgent:

            order_code = get_order_code(
                operation
            )

            if order_code not in unique_orders:
                unique_orders[order_code] = operation

        urgent_orders = list(
            unique_orders.values()
        )

        if urgent_orders:

            order_text = []

            for operation in urgent_orders:

                order_code = get_order_code(
                    operation
                )

                product = get_product(
                    operation
                )

                deadline = operation.get(
                    "deadline_hours",
                    "N/A"
                )

                order_text.append(
                    f"{order_code} "
                    f"({product}) - "
                    f"deadline {deadline}h"
                )

            return {
                "answer": (
                    f"There are {len(urgent_orders)} "
                    f"high-priority orders: "
                    + ", ".join(order_text)
                    + ". These orders should be protected "
                    "and prioritized in the production schedule."
                ),

                "evidence": order_text
            }

        return {
            "answer": (
                "No Priority-1 orders were found "
                "in the current production plan."
            ),
            "evidence": []
        }

    # =========================================================
    # 6. DELAY ANALYSIS
    # =========================================================

    if any(word in q for word in [
        "delay",
        "delayed",
        "late",
        "overdue",
        "deadline",
        "late orders"
    ]):

        delayed = [
            operation
            for operation in plan
            if operation.get("feasible") is False
        ]

        if delayed:

            operation = delayed[0]

            order_code = get_order_code(
                operation
            )

            product = get_product(
                operation
            )

            return {
                "answer": (
                    f"Order {order_code} "
                    f"({product}) has the highest immediate "
                    f"delay risk."
                ),

                "evidence": [
                    f"Priority: "
                    f"{operation.get('priority', 'N/A')}",
                    f"Machine: "
                    f"{operation.get('machine', 'N/A')}",
                    f"Planned end: "
                    f"{operation.get('end_hour', 'N/A')}h",
                    f"Deadline: "
                    f"{operation.get('deadline_hours', 'N/A')}h"
                ]
            }

        return {
            "answer": (
                "Good news: no operation is currently projected "
                "beyond its deadline in the baseline production plan."
            ),

            "evidence": [
                f"Delay risk: "
                f"{kpis.get('delay_risk', 0)}%",
                f"Efficiency: "
                f"{kpis.get('efficiency', 0)}%"
            ]
        }

    # =========================================================
    # 7. MACHINE UTILIZATION
    # =========================================================

    if any(word in q for word in [
        "utilization",
        "machine usage",
        "machine capacity",
        "how busy",
        "machine performance"
    ]):

        if machines:

            machine_lines = []

            for machine in machines:

                name = get_machine_name(
                    machine
                )

                utilization = get_utilization(
                    machine
                )

                machine_lines.append(
                    f"{name}: {utilization:.1f}%"
                )

            return {
                "answer": (
                    "Current machine utilization is: "
                    + ", ".join(machine_lines)
                ),

                "evidence": machine_lines
            }

        return {
            "answer": (
                "Machine utilization data is currently unavailable."
            ),
            "evidence": []
        }

    # =========================================================
    # 8. FACTORY EFFICIENCY
    # =========================================================

    if any(word in q for word in [
        "efficiency",
        "efficient",
        "performance",
        "factory efficiency"
    ]):

        efficiency = kpis.get(
            "efficiency",
            0
        )

        delay_risk = kpis.get(
            "delay_risk",
            0
        )

        return {
            "answer": (
                f"Factory efficiency is currently "
                f"{efficiency}%. "
                f"Overall delay risk is "
                f"{delay_risk}%."
            ),

            "evidence": [
                f"Efficiency: {efficiency}%",
                f"Delay risk: {delay_risk}%"
            ]
        }

    # =========================================================
    # 9. MACHINE FAILURE / MAINTENANCE
    # =========================================================

    if any(word in q for word in [
        "failure",
        "fail",
        "maintenance",
        "breakdown",
        "machine problem",
        "machine risk",
        "risk"
    ]):

        if machines:

            risky_machine = max(
                machines,
                key=get_utilization
            )

            name = get_machine_name(
                risky_machine
            )

            utilization = get_utilization(
                risky_machine
            )

            if utilization >= 90:
                risk = "HIGH"

            elif utilization >= 70:
                risk = "MEDIUM"

            else:
                risk = "LOW"

            return {
                "answer": (
                    f"{name} has the highest operational "
                    f"pressure at {utilization:.1f}% utilization. "
                    f"Current operational risk is {risk}."
                ),

                "evidence": [
                    f"Machine: {name}",
                    f"Utilization: {utilization:.1f}%",
                    f"Risk level: {risk}"
                ]
            }

        return {
            "answer": (
                "Machine condition data is currently unavailable."
            ),
            "evidence": []
        }

    # =========================================================
    # 10. PRODUCTION ORDERS
    # =========================================================

    if any(word in q for word in [
        "orders",
        "order list",
        "production orders",
        "how many orders",
        "list orders"
    ]):

        if plan:

            unique_orders = {}

            for operation in plan:

                order_code = get_order_code(
                    operation
                )

                if order_code not in unique_orders:
                    unique_orders[order_code] = operation

            order_list = []

            for order_code, operation in unique_orders.items():

                product = get_product(
                    operation
                )

                deadline = operation.get(
                    "deadline_hours",
                    "N/A"
                )

                priority = operation.get(
                    "priority",
                    "N/A"
                )

                order_list.append(
                    f"{order_code} - "
                    f"{product} - "
                    f"Priority {priority} - "
                    f"Deadline {deadline}h"
                )

            return {
                "answer": (
                    f"The factory currently has "
                    f"{len(order_list)} unique production orders: "
                    + "; ".join(order_list)
                ),

                "evidence": order_list
            }

        return {
            "answer": (
                "No production orders are currently available."
            ),
            "evidence": []
        }

    # =========================================================
    # 11. FACTORY STATUS / SUMMARY
    # =========================================================

    if any(word in q for word in [
        "summary",
        "status",
        "factory status",
        "overall status",
        "overall",
        "what is happening",
        "current status"
    ]):

        efficiency = kpis.get(
            "efficiency",
            0
        )

        delay_risk = kpis.get(
            "delay_risk",
            0
        )

        if machines:

            bottleneck = max(
                machines,
                key=get_utilization
            )

            machine_name = get_machine_name(
                bottleneck
            )

            utilization = get_utilization(
                bottleneck
            )

        else:

            machine_name = "Unavailable"
            utilization = 0

        return {
            "answer": (
                f"Factory status: efficiency is "
                f"{efficiency}%, delay risk is "
                f"{delay_risk}%, and "
                f"{len(plan)} production operations "
                f"are currently planned. "
                f"The current bottleneck is "
                f"{machine_name} at "
                f"{utilization:.1f}% utilization."
            ),

            "evidence": [
                f"Efficiency: {efficiency}%",
                f"Delay risk: {delay_risk}%",
                f"Planned operations: {len(plan)}",
                f"Bottleneck: {machine_name}",
                f"Bottleneck utilization: "
                f"{utilization:.1f}%"
            ]
        }

    # =========================================================
    # 12. DEFAULT RESPONSE
    # =========================================================

    return {
        "answer": (
            "I can analyze the current FactoryMind production data. "
            "You can ask me about bottlenecks, urgent orders, "
            "delays, machine utilization, efficiency, "
            "machine failures, production orders, "
            "factory status, or what-if scenarios."
        ),

        "evidence": [
            "Bottleneck analysis",
            "Urgent order analysis",
            "Delay analysis",
            "Machine utilization",
            "Efficiency analysis",
            "Maintenance risk",
            "Production orders",
            "What-if analysis"
        ]
    }