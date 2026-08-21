from pydantic import BaseModel, Field

class MachineFailure(BaseModel):
    machine_code: str
    failure_hours: float = Field(default=6, ge=1, le=24)

class AssistantRequest(BaseModel):
    question: str

class OrderCreate(BaseModel):
    order_code: str
    product: str
    quantity: int
    priority: int = 2
    deadline_hours: float
    material: str

class MLPredictionRequest(BaseModel):
    machine_age_years: float
    load_percent: float
    temperature_c: float
    vibration_mm_s: float
    hours_since_maintenance: float
    batch_size: int
    operator_experience_years: float
    tool_wear_percent: float
    material_hardness: float
