from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import List, Optional
import os

# ==========================================
# CONFIGURAÇÃO DO BANCO DE DADOS (SUPABASE / POSTGRESQL)
# ==========================================
# Coloque a sua URL do Supabase abaixo, mantendo as aspas.
# Exemplo: "postgresql://postgres:SuaSenha@db.abcd123.supabase.co:5432/postgres"
MINHA_URL_SUPABASE = "postgresql://postgres:[SUA_SENHA]@db.[SEU_PROJETO].supabase.co:5432/postgres"

# Pega a URL do ambiente (se existir na nuvem) ou usa a do Supabase informada acima
DATABASE_URL = os.getenv("DATABASE_URL", MINHA_URL_SUPABASE)

# Corrige o prefixo (o SQLAlchemy mais novo exige postgresql:// ao invés de postgres://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Se por acaso for SQLite, precisa de argumentos especiais, se for Postgres, não.
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# MODELOS DO BANCO DE DADOS (SQLAlchemy)
# ==========================================
class OrderDB(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    entity = Column(String, index=True)
    client = Column(String)
    product = Column(String)
    production_type = Column(String)
    supplier = Column(String, nullable=True)
    supplier_cost = Column(Float, default=0.0)
    status_production = Column(String)
    client_due_date = Column(String, nullable=True)
    supplier_due_date = Column(String, nullable=True)
    sale_value = Column(Float, default=0.0)
    paid_by_client = Column(Float, default=0.0)
    paid_to_supplier = Column(Float, default=0.0)
    is_recurrent = Column(Boolean, default=False)

class BillDB(Base):
    __tablename__ = "bills"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(String, nullable=True, index=True)
    creditor = Column(String)
    entity = Column(String)
    total_amount = Column(Float, default=0.0)
    installment_number = Column(Integer, default=1)
    total_installments = Column(Integer, default=1)
    installment_amount = Column(Float, default=0.0)
    due_date = Column(String)
    is_recurrent = Column(Boolean, default=False)
    is_paid = Column(Boolean, default=False)
    created_by_user = Column(String, nullable=True)
    card_id = Column(Integer, nullable=True)

class ProfileDB(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

class CardDB(Base):
    __tablename__ = "cards"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    entity = Column(String)
    total_limit = Column(Float, default=0.0)
    closing_day = Column(Integer)
    due_day = Column(Integer)

class SettingDB(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True, index=True)
    value = Column(String)

Base.metadata.create_all(bind=engine)

# ==========================================
# SCHEMAS DE VALIDAÇÃO (Pydantic)
# ==========================================
class OrderSchema(BaseModel):
    entity: str
    client: str
    product: str
    production_type: str
    supplier: Optional[str] = ""
    supplier_cost: float = 0.0
    status_production: str
    client_due_date: Optional[str] = None
    supplier_due_date: Optional[str] = None
    sale_value: float = 0.0
    paid_by_client: float = 0.0
    paid_to_supplier: float = 0.0
    is_recurrent: bool = False

class OrderStatusSchema(BaseModel):
    status_production: str

class BillSchema(BaseModel):
    group_id: Optional[str] = None
    creditor: str
    entity: str
    total_amount: float = 0.0
    installment_number: int = 1
    total_installments: int = 1
    installment_amount: float = 0.0
    due_date: str
    is_recurrent: bool = False
    card_id: Optional[int] = None

class BillUpdateSchema(BaseModel):
    mode: str = "SINGLE" # SINGLE, FUTURE, ALL
    creditor: str
    entity: str
    installment_amount: float
    due_date: str
    card_id: Optional[int] = None

class BillStatusSchema(BaseModel):
    is_paid: bool

class ProfileSchema(BaseModel):
    name: str

class CardSchema(BaseModel):
    name: str
    entity: str
    total_limit: float
    closing_day: int
    due_day: int

class BalanceSchema(BaseModel):
    initial_balance: float

# ==========================================
# INICIALIZAÇÃO DA API
# ==========================================
app = FastAPI(title="ERP Unificado API")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Servir a página principal
@app.get("/", response_class=HTMLResponse)
def read_root():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(template_path, "r", encoding="utf-8") as file:
        return file.read()

# ==========================================
# ROTAS: CONFIGURAÇÕES E DADOS
# ==========================================
@app.get("/api/settings/balance")
def get_balance():
    db = SessionLocal()
    setting = db.query(SettingDB).filter(SettingDB.key == "initial_balance").first()
    db.close()
    return {"initial_balance": float(setting.value) if setting else 0.0}

@app.post("/api/settings/balance")
def set_balance(data: BalanceSchema):
    db = SessionLocal()
    setting = db.query(SettingDB).filter(SettingDB.key == "initial_balance").first()
    if setting:
        setting.value = str(data.initial_balance)
    else:
        new_setting = SettingDB(key="initial_balance", value=str(data.initial_balance))
        db.add(new_setting)
    db.commit()
    db.close()
    return {"success": True}

@app.get("/api/profiles")
def get_profiles():
    db = SessionLocal()
    profiles = db.query(ProfileDB).all()
    db.close()
    return profiles

@app.post("/api/profiles")
def create_profile(profile: ProfileSchema):
    db = SessionLocal()
    new_profile = ProfileDB(name=profile.name)
    db.add(new_profile)
    db.commit()
    db.close()
    return {"success": True}

@app.delete("/api/profiles/{id}")
def delete_profile(id: int):
    db = SessionLocal()
    db.query(ProfileDB).filter(ProfileDB.id == id).delete()
    db.commit()
    db.close()
    return {"success": True}

@app.get("/api/cards")
def get_cards():
    db = SessionLocal()
    cards = db.query(CardDB).all()
    db.close()
    return cards

@app.post("/api/cards")
def create_card(card: CardSchema):
    db = SessionLocal()
    new_card = CardDB(**card.dict())
    db.add(new_card)
    db.commit()
    db.close()
    return {"success": True}

@app.put("/api/cards/{id}")
def update_card(id: int, card: CardSchema):
    db = SessionLocal()
    db_card = db.query(CardDB).filter(CardDB.id == id).first()
    if not db_card:
        db.close()
        raise HTTPException(status_code=404)
    for key, value in card.dict().items():
        setattr(db_card, key, value)
    db.commit()
    db.close()
    return {"success": True}

@app.delete("/api/cards/{id}")
def delete_card(id: int):
    db = SessionLocal()
    db.query(CardDB).filter(CardDB.id == id).delete()
    bills = db.query(BillDB).filter(BillDB.card_id == id).all()
    for b in bills:
        b.card_id = None
    db.commit()
    db.close()
    return {"success": True}

@app.get("/api/orders")
def get_orders():
    db = SessionLocal()
    orders = db.query(OrderDB).all()
    db.close()
    return orders

@app.post("/api/orders")
def create_order(order: OrderSchema):
    db = SessionLocal()
    new_order = OrderDB(**order.dict())
    db.add(new_order)
    db.commit()
    db.close()
    return {"success": True}

@app.put("/api/orders/{id}")
def update_order(id: int, order: OrderSchema):
    db = SessionLocal()
    db_order = db.query(OrderDB).filter(OrderDB.id == id).first()
    if not db_order:
        db.close()
        raise HTTPException(status_code=404)
    for key, value in order.dict().items():
        setattr(db_order, key, value)
    db.commit()
    db.close()
    return {"success": True}

@app.put("/api/orders/{id}/status")
def update_order_status(id: int, status: OrderStatusSchema):
    db = SessionLocal()
    db_order = db.query(OrderDB).filter(OrderDB.id == id).first()
    if not db_order:
        db.close()
        raise HTTPException(status_code=404)
    db_order.status_production = status.status_production
    db.commit()
    db.close()
    return {"success": True}

@app.delete("/api/orders/{id}")
def delete_order(id: int):
    db = SessionLocal()
    db.query(OrderDB).filter(OrderDB.id == id).delete()
    db.commit()
    db.close()
    return {"success": True}

@app.get("/api/bills")
def get_bills():
    db = SessionLocal()
    bills = db.query(BillDB).all()
    db.close()
    return bills

@app.post("/api/bills")
def create_bill(bill: BillSchema):
    db = SessionLocal()
    new_bill = BillDB(**bill.dict())
    db.add(new_bill)
    db.commit()
    db.close()
    return {"success": True}

@app.put("/api/bills/{id}/status")
def update_bill_status(id: int, status: BillStatusSchema):
    db = SessionLocal()
    db_bill = db.query(BillDB).filter(BillDB.id == id).first()
    if not db_bill:
        db.close()
        raise HTTPException(status_code=404)
    db_bill.is_paid = status.is_paid
    db.commit()
    db.close()
    return {"success": True}

@app.put("/api/bills/{id}")
def update_bill(id: int, update: BillUpdateSchema):
    db = SessionLocal()
    db_bill = db.query(BillDB).filter(BillDB.id == id).first()
    if not db_bill:
        db.close()
        raise HTTPException(status_code=404)

    if update.mode == "SINGLE" or not db_bill.group_id:
        db_bill.creditor = update.creditor
        db_bill.entity = update.entity
        db_bill.installment_amount = update.installment_amount
        db_bill.due_date = update.due_date
        db_bill.card_id = update.card_id
    else:
        query = db.query(BillDB).filter(BillDB.group_id == db_bill.group_id)
        if update.mode == "FUTURE":
            query = query.filter(BillDB.installment_number >= db_bill.installment_number)
        
        group_bills = query.all()
        for b in group_bills:
            b.creditor = update.creditor
            b.entity = update.entity
            b.installment_amount = update.installment_amount
            b.card_id = update.card_id
            if b.id == db_bill.id:
                b.due_date = update.due_date
    db.commit()
    db.close()
    return {"success": True}

@app.delete("/api/bills/{id}")
def delete_bill(id: int, mode: str = Query("SINGLE")):
    db = SessionLocal()
    db_bill = db.query(BillDB).filter(BillDB.id == id).first()
    if not db_bill:
        db.close()
        raise HTTPException(status_code=404)

    if mode == "SINGLE" or not db_bill.group_id:
        db.delete(db_bill)
    else:
        query = db.query(BillDB).filter(BillDB.group_id == db_bill.group_id)
        if mode == "FUTURE":
            query = query.filter(BillDB.installment_number >= db_bill.installment_number)
        query.delete()

    db.commit()
    db.close()
    return {"success": True}
