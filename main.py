import os
import sys
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

def get_resource_path(relative_path: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./financeiro.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ProfileModel(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

class CardModel(Base):
    __tablename__ = "cards"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    entity = Column(String, nullable=False)
    total_limit = Column(Float, nullable=False)
    closing_day = Column(Integer, nullable=False)
    due_day = Column(Integer, nullable=False)

class BillModel(Base):
    __tablename__ = "bills"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(String, nullable=True)
    creditor = Column(String, nullable=False)
    entity = Column(String, nullable=False)
    total_amount = Column(Float, nullable=False)
    installment_number = Column(Integer, nullable=False)
    total_installments = Column(Integer, nullable=False)
    installment_amount = Column(Float, nullable=False)
    due_date = Column(String, nullable=False)
    is_paid = Column(Boolean, default=False)
    is_recurrent = Column(Boolean, default=False)
    created_by_user = Column(String, nullable=False)
    card_id = Column(Integer, ForeignKey("cards.id", ondelete="CASCADE"), nullable=True)

class OrderModel(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    entity = Column(String, nullable=False)
    client = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    product = Column(String, nullable=False)
    production_type = Column(String, nullable=False)
    supplier = Column(String, nullable=True)
    supplier_cost = Column(Float, default=0.0)
    status_production = Column(String, default="EM PRODUÇÃO")
    supplier_due_date = Column(String, nullable=True)
    client_due_date = Column(String, nullable=True)
    sale_value = Column(Float, default=0.0)
    paid_by_client = Column(Float, default=0.0)
    paid_to_supplier = Column(Float, default=0.0)

class SettingsModel(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=False)

Base.metadata.create_all(bind=engine)

db_init = SessionLocal()
if db_init.query(ProfileModel).count() == 0:
    db_init.add_all([
        ProfileModel(name="Gabriel"),
        ProfileModel(name="Jéssica"),
        ProfileModel(name="Empresas")
    ])
    db_init.commit()

if not db_init.query(SettingsModel).filter(SettingsModel.key == "initial_balance").first():
    db_init.add(SettingsModel(key="initial_balance", value="0.00"))
    db_init.commit()

db_init.close()

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ProfileCreate(BaseModel):
    name: str

class CardCreate(BaseModel):
    name: str
    entity: str
    total_limit: float
    closing_day: int
    due_day: int

class BillCreate(BaseModel):
    creditor: str
    entity: str
    total_amount: float
    installment_number: int
    total_installments: int
    installment_amount: float
    due_date: str
    is_recurrent: bool
    created_by_user: str
    card_id: Optional[int] = None

class BillStatusUpdate(BaseModel):
    is_paid: bool

class OrderSchema(BaseModel):
    entity: str
    client: str
    phone: Optional[str] = None
    product: str
    production_type: str
    supplier: Optional[str] = None
    supplier_cost: float
    status_production: str
    supplier_due_date: Optional[str] = None
    client_due_date: Optional[str] = None
    sale_value: float
    paid_by_client: float
    paid_to_supplier: float

class OrderStatusUpdate(BaseModel):
    status_production: str

class BalanceUpdate(BaseModel):
    initial_balance: float

@app.get("/manifest.json")
def get_manifest():
    manifest_path = get_resource_path("manifest.json")
    if os.path.exists(manifest_path):
        return FileResponse(manifest_path, media_type="application/json")
    raise HTTPException(status_code=404, detail="Manifest não encontrado")

@app.get("/api/profiles")
def get_profiles(db: Session = Depends(get_db)):
    return db.query(ProfileModel).all()

@app.post("/api/profiles")
def create_profile(profile: ProfileCreate, db: Session = Depends(get_db)):
    existing = db.query(ProfileModel).filter(ProfileModel.name == profile.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Perfil já existe")
    db_profile = ProfileModel(name=profile.name)
    db.add(db_profile); db.commit(); db.refresh(db_profile)
    return db_profile

@app.delete("/api/profiles/{profile_id}")
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.query(ProfileModel).filter(ProfileModel.id == profile_id).first()
    if profile:
        db.delete(profile); db.commit()
        return {"message": "Perfil excluído"}
    raise HTTPException(status_code=404, detail="Perfil não encontrado")

@app.get("/api/cards")
def get_cards(db: Session = Depends(get_db)):
    return db.query(CardModel).all()

@app.post("/api/cards")
def create_card(card: CardCreate, db: Session = Depends(get_db)):
    db_card = CardModel(**card.dict())
    db.add(db_card); db.commit(); db.refresh(db_card)
    return db_card

@app.delete("/api/cards/{card_id}")
def delete_card(card_id: int, db: Session = Depends(get_db)):
    card = db.query(CardModel).filter(CardModel.id == card_id).first()
    if card:
        db.query(BillModel).filter(BillModel.card_id == card_id).delete()
        db.delete(card); db.commit()
        return {"message": "Cartão excluído"}
    raise HTTPException(status_code=404, detail="Cartão não encontrado")

@app.get("/api/bills")
def get_bills(db: Session = Depends(get_db)):
    return db.query(BillModel).all()

@app.post("/api/bills")
def create_bill(bill: BillCreate, db: Session = Depends(get_db)):
    db_bill = BillModel(**bill.dict())
    db.add(db_bill); db.commit(); db.refresh(db_bill)
    return db_bill

@app.put("/api/bills/{bill_id}/status")
def update_bill_status(bill_id: int, status_data: BillStatusUpdate, db: Session = Depends(get_db)):
    bill = db.query(BillModel).filter(BillModel.id == bill_id).first()
    if bill:
        bill.is_paid = status_data.is_paid
        db.commit()
        return {"message": "Status atualizado"}
    raise HTTPException(status_code=404, detail="Dívida não encontrada")

@app.delete("/api/bills/{bill_id}")
def delete_bill(bill_id: int, db: Session = Depends(get_db)):
    bill = db.query(BillModel).filter(BillModel.id == bill_id).first()
    if bill:
        db.delete(bill); db.commit()
        return {"message": "Excluído com sucesso"}
    raise HTTPException(status_code=404, detail="Não encontrado")

@app.get("/api/orders")
def get_orders(db: Session = Depends(get_db)):
    return db.query(OrderModel).all()

@app.post("/api/orders")
def create_order(order: OrderSchema, db: Session = Depends(get_db)):
    db_order = OrderModel(**order.dict())
    db.add(db_order); db.commit(); db.refresh(db_order)
    return db_order

@app.put("/api/orders/{order_id}/status")
def update_order_status(order_id: int, status_data: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if order:
        order.status_production = status_data.status_production
        db.commit()
        return {"message": "Status do pedido atualizado com sucesso"}
    raise HTTPException(status_code=404, detail="Pedido não encontrado")

@app.delete("/api/orders/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if order:
        db.delete(order); db.commit()
        return {"message": "Pedido excluído"}
    raise HTTPException(status_code=404, detail="Pedido não encontrado")

@app.get("/api/settings/balance")
def get_balance(db: Session = Depends(get_db)):
    setting = db.query(SettingsModel).filter(SettingsModel.key == "initial_balance").first()
    val = float(setting.value) if setting else 0.0
    return {"initial_balance": val}

@app.post("/api/settings/balance")
def update_balance(data: BalanceUpdate, db: Session = Depends(get_db)):
    setting = db.query(SettingsModel).filter(SettingsModel.key == "initial_balance").first()
    if not setting:
        setting = SettingsModel(key="initial_balance", value=str(data.initial_balance))
        db.add(setting)
    else:
        setting.value = str(data.initial_balance)
    db.commit()
    return {"initial_balance": data.initial_balance}

@app.get("/")
def read_root():
    path_templates = get_resource_path(os.path.join("templates", "index.html"))
    path_local = get_resource_path("index.html")
    if os.path.exists(path_templates):
        return FileResponse(path_templates)
    elif os.path.exists(path_local):
        return FileResponse(path_local)
    return {"message": "Erro: Arquivo index.html não encontrado!"}
