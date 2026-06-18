from sqlalchemy import Column, BigInteger, DateTime, Enum, ForeignKey, Integer, Boolean, String, Text
from sqlalchemy.orm import relationship
from app.database import Base

class DispatchCustodyTransfer(Base):
    __tablename__ = "dispatch_custody_transfers"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    dispatch_order_id = Column(BigInteger, ForeignKey("dispatch_orders.id", ondelete="CASCADE"), nullable=False)
    position_id = Column(BigInteger, ForeignKey("positions.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum("pending", "acknowledged", "skipped", name="custody_status_enum"), default="pending")
    acknowledged_by_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime)
    sequence = Column(Integer, nullable=False)
    
    # SCM Custody verification fields
    seal_intact = Column(Boolean, nullable=True)
    packaging_condition = Column(String(50), nullable=True) # INTACT, DAMAGED, TAMPERED
    discrepancy_reported = Column(Boolean, nullable=True)
    remarks = Column(Text, nullable=True)
    
    dispatch = relationship("DispatchOrder", foreign_keys=[dispatch_order_id])
    position = relationship("Position", foreign_keys=[position_id])
    acknowledged_by = relationship("User", foreign_keys=[acknowledged_by_id])
