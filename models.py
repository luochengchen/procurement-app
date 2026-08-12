"""Data models for the procurement app."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


# === Material models ===

class MaterialCategory(Base):
    __tablename__ = "material_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    icon = Column(String(16), default="📦")
    sort_order = Column(Integer, default=0)

    materials = relationship("Material", back_populates="category", lazy="select")

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "icon": self.icon, "sort_order": self.sort_order}


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("material_categories.id"), nullable=False)
    name = Column(String(128), nullable=False)
    spec = Column(String(256), default="")
    unit = Column(String(32), default="kg")
    current_price = Column(Float, default=0.0)
    price_date = Column(Date, default=date.today)
    currency = Column(String(8), default="CNY")
    price_source = Column(String(256), default="")
    price_url = Column(String(512), default="")
    trend = Column(String(16), default="stable")  # up / down / stable
    notes = Column(Text, default="")

    category = relationship("MaterialCategory", back_populates="materials")
    price_history = relationship("PriceHistory", back_populates="material", lazy="select",
                                 order_by="PriceHistory.recorded_date.desc()")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "",
            "name": self.name,
            "spec": self.spec,
            "unit": self.unit,
            "current_price": self.current_price,
            "price_date": self.price_date.isoformat() if self.price_date else "",
            "currency": self.currency,
            "price_source": self.price_source,
            "price_url": self.price_url,
            "trend": self.trend,
            "notes": self.notes,
        }


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    price = Column(Float, nullable=False)
    recorded_date = Column(Date, default=date.today)

    material = relationship("Material", back_populates="price_history")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "material_id": self.material_id,
            "price": self.price,
            "recorded_date": self.recorded_date.isoformat() if self.recorded_date else "",
        }


# === Cost calculation models ===

class CostTemplate(Base):
    __tablename__ = "cost_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("CostItem", back_populates="template", lazy="select",
                         cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "items": [item.to_dict() for item in self.items],
        }


class CostItem(Base):
    __tablename__ = "cost_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey("cost_templates.id"), nullable=False)
    item_type = Column(String(32), nullable=False, default="material")
    # material / labor / utility / processing_out / processing_own / other
    name = Column(String(256), nullable=False)
    unit = Column(String(32), default="pcs")
    unit_price = Column(Float, default=0.0)
    quantity = Column(Float, default=1.0)
    subtotal = Column(Float, default=0.0)

    template = relationship("CostTemplate", back_populates="items")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "template_id": self.template_id,
            "item_type": self.item_type,
            "name": self.name,
            "unit": self.unit,
            "unit_price": self.unit_price,
            "quantity": self.quantity,
            "subtotal": self.subtotal,
        }


# === Certification models ===

class Certification(Base):
    __tablename__ = "certifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_category = Column(String(128), nullable=False)
    target_country = Column(String(64), nullable=False)
    cert_name = Column(String(256), nullable=False)
    cert_body = Column(String(256), default="")
    is_mandatory = Column(Boolean, default=True)
    estimated_cost = Column(String(128), default="")
    lead_time_days = Column(Integer, default=30)
    description = Column(Text, default="")
    reference_url = Column(String(512), default="")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_category": self.product_category,
            "target_country": self.target_country,
            "cert_name": self.cert_name,
            "cert_body": self.cert_body,
            "is_mandatory": self.is_mandatory,
            "estimated_cost": self.estimated_cost,
            "lead_time_days": self.lead_time_days,
            "description": self.description,
            "reference_url": self.reference_url,
        }
