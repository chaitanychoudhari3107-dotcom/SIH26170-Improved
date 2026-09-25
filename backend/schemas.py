from pydantic import BaseModel


class ComponentCreate(BaseModel):
    component_id: str
    lot_id: str
    device_variant: str

    iddq_0h: float
    iddq_24h: float