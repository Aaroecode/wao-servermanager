from sqlalchemy import Column, Integer, String
from app.database import Base

class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    player_name = Column(String, nullable=False)
    item = Column(String, nullable=False)
    status = Column(String, default="pending")
