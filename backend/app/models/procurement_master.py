from sqlalchemy import Column, BigInteger, String, Text, Boolean, DateTime, Date, Enum, ForeignKey, Numeric, Integer, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    vendor_code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    contact_person = Column(String(255))
    email = Column(String(255))
    phone = Column(String(20))
    alt_phone = Column(String(20))
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    pincode = Column(String(10))
    country = Column(String(100), default="India")
    gst_number = Column(String(20))
    pan_number = Column(String(20))
    bank_name = Column(String(255))
    bank_account = Column(String(50))
    bank_ifsc = Column(String(20))
    payment_terms_days = Column(Integer, default=30)
    credit_limit = Column(Numeric(15, 2), default=0)
    vendor_type = Column(Enum("material", "transport", "service", "both", name="vendor_type_enum"), default="material")
    vendor_type_id = Column(BigInteger, ForeignKey("vendor_types.id"), nullable=True)
    vendor_category_id = Column(BigInteger, ForeignKey("vendor_categories.id"), nullable=True)
    rating = Column(Numeric(3, 2), default=0)
    is_transport_vendor = Column(Boolean, default=False)
    drug_license_number = Column(String(50))
    drug_license_state = Column(String(100))
    drug_license_expiry = Column(Date)
    gst_certificate_url = Column(String(500))
    license_doc_url = Column(String(500))
    vendor_compliance_status = Column(
        Enum("compliant", "expiring_soon", "expired", "not_required", name="vendor_compliance_status_enum"),
        default="not_required",
    )
    is_active = Column(Boolean, default=True)
    onboarded_date = Column(DateTime)
    created_by = Column(BigInteger)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    items = relationship("VendorItem", back_populates="vendor")
    type_links = relationship("VendorVendorType", back_populates="vendor", cascade="all, delete-orphan")
    primary_vendor_type = relationship("VendorType", foreign_keys=[vendor_type_id])
    category = relationship("VendorCategory", foreign_keys=[vendor_category_id])
    contracts = relationship("VendorContract", back_populates="vendor")
    ratings = relationship("VendorRating", back_populates="vendor")


class VendorType(Base):
    __tablename__ = "vendor_types"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class VendorCategory(Base):
    __tablename__ = "vendor_categories"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class VendorVendorType(Base):
    __tablename__ = "vendor_vendor_types"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    vendor_id = Column(BigInteger, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False)
    vendor_type_id = Column(BigInteger, ForeignKey("vendor_types.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    vendor = relationship("Vendor", back_populates="type_links")
    vendor_type = relationship("VendorType")

    __table_args__ = (
        UniqueConstraint("vendor_id", "vendor_type_id", name="uq_vendor_vendor_type"),
    )


class VendorItem(Base):
    __tablename__ = "vendor_items"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    vendor_id = Column(BigInteger, ForeignKey("vendors.id"), nullable=False)
    item_id = Column(BigInteger, ForeignKey("items.id"), nullable=False)
    vendor_item_code = Column(String(100))
    lead_time_days = Column(Integer, default=0)
    min_order_qty = Column(Numeric(15, 3), default=0)
    rate = Column(Numeric(15, 2), default=0)
    is_preferred = Column(Boolean, default=False)

    vendor = relationship("Vendor", back_populates="items")
    item = relationship("Item")

    __table_args__ = (
        UniqueConstraint("vendor_id", "item_id", name="uq_vendor_item"),
    )


class VendorItemHistory(Base):
    __tablename__ = "vendor_item_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    vendor_item_id = Column(BigInteger, nullable=True)
    vendor_id = Column(BigInteger, ForeignKey("vendors.id"), nullable=False)
    item_id = Column(BigInteger, ForeignKey("items.id"), nullable=False)
    action = Column(String(20), nullable=False)
    old_vendor_item_code = Column(String(100))
    new_vendor_item_code = Column(String(100))
    old_lead_time_days = Column(Integer)
    new_lead_time_days = Column(Integer)
    old_min_order_qty = Column(Numeric(15, 3))
    new_min_order_qty = Column(Numeric(15, 3))
    old_rate = Column(Numeric(15, 2))
    new_rate = Column(Numeric(15, 2))
    old_is_preferred = Column(Boolean)
    new_is_preferred = Column(Boolean)
    changed_by_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    changed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    vendor = relationship("Vendor")
    item = relationship("Item")


class VendorContract(Base):
    __tablename__ = "vendor_contracts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    vendor_id = Column(BigInteger, ForeignKey("vendors.id"), nullable=False)
    contract_number = Column(String(100), unique=True, nullable=False)
    title = Column(String(255))
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    terms = Column(Text)
    document_url = Column(String(500))
    status = Column(Enum("draft", "active", "expired", "terminated", name="contract_status_enum"), default="draft")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    vendor = relationship("Vendor", back_populates="contracts")


class VendorRating(Base):
    __tablename__ = "vendor_ratings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    vendor_id = Column(BigInteger, ForeignKey("vendors.id"), nullable=False)
    period_from = Column(DateTime)
    period_to = Column(DateTime)
    delivery_timeliness = Column(Numeric(3, 2), default=0)
    cost_efficiency = Column(Numeric(3, 2), default=0)
    service_reliability = Column(Numeric(3, 2), default=0)
    delivery_accuracy = Column(Numeric(3, 2), default=0)
    overall_rating = Column(Numeric(3, 2), default=0)
    remarks = Column(Text)
    rated_by = Column(BigInteger)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    vendor = relationship("Vendor", back_populates="ratings")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    customer_code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    contact_person = Column(String(255))
    email = Column(String(255))
    phone = Column(String(20))
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    pincode = Column(String(10))
    country = Column(String(100), default="India")
    gst_number = Column(String(20))
    credit_limit = Column(Numeric(15, 2), default=0)
    payment_terms_days = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
