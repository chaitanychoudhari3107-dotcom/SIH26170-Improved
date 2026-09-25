from sqlalchemy import Column, Integer, String, Float
from database import Base


class Component(Base):
    __tablename__ = "components"

    id = Column(Integer, primary_key=True, index=True)

    component_id = Column(String, unique=True, index=True)
    lot_id = Column(String, index=True)
    device_variant = Column(String)

    iddq_0h = Column(Float)
    iddq_24h = Column(Float)