from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import List, Optional
import os

# ==========================================
# CONFIGURAÇÃO DO BANCO DE DADOS (SUPABASE / POSTGRESQL)
# ==========================================
# COLE A SUA URL DO SUPABASE AQUI:
MINHA_URL_SUPABASE = "postgresql://postgresql://postgres.fccxyypigatzjhhxqtua:ElisaAlana220417!@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"

DATABASE_URL = os.getenv("DATABASE_URL", MINHA_URL_SUPABASE)
if DATABASE_URL.startswith("postgres://"): DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"): engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else: engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# MODELOS DO BANCO DE DADOS
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

class QuoteDB(Base):
    __tablename__ = "quotes"
    id = Column(Integer, primary_key=True, index=True)
    client = Column(String)
    entity = Column(String)
    items = Column(String)
    payment_terms = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    total_value = Column(Float, default=0.0)
    status = Column(String, default="PENDENTE")
    created_at = Column(String)

class ProfileDB(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    logo = Column(Text, nullable=True)

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
# SCHEMAS DE VALIDAÇÃO
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
    created_by_user: Optional[str] = None

class BillUpdateSchema(BaseModel):
    mode: str = "SINGLE"
    creditor: str
    entity: str
    installment_amount: float
    due_date: str
    card_id: Optional[int] = None

class BillStatusSchema(BaseModel):
    is_paid: bool

class QuoteSchema(BaseModel):
    client: str
    entity: str
    items: str
    payment_terms: Optional[str] = ""
    notes: Optional[str] = ""
    total_value: float = 0.0
    status: str = "PENDENTE"
    created_at: str

class QuoteStatusSchema(BaseModel):
    status: str

class ProfileSchema(BaseModel):
    name: str
    logo: Optional[str] = None

class CardSchema(BaseModel):
    name: str
    entity: str
    total_limit: float
    closing_day: int
    due_day: int

class BalanceSchema(BaseModel):
    initial_balance: float

app = FastAPI(title="ERP Unificado API")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@app.get("/", response_class=HTMLResponse)
def read_root():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(template_path, "r", encoding="utf-8") as file: return file.read()

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
    if setting: setting.value = str(data.initial_balance)
    else: db.add(SettingDB(key="initial_balance", value=str(data.initial_balance)))
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
    db.add(ProfileDB(name=profile.name, logo=profile.logo))
    db.commit()
    db.close()
    return {"success": True}

# ==========================================
# NOVA ROTA: EDITAR PERFIL (COM ATUALIZAÇÃO EM CASCATA)
# ==========================================
@app.put("/api/profiles/{id}")
def update_profile(id: int, profile: ProfileSchema):
    db = SessionLocal()
    db_profile = db.query(ProfileDB).filter(ProfileDB.id == id).first()
    if not db_profile:
        db.close()
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    
    old_name = db_profile.name
    new_name = profile.name
    
    db_profile.name = new_name
    db_profile.logo = profile.logo
    
    # Se o nome da empresa mudou, atualiza todos os pedidos, contas e orçamentos antigos pra não perder o vínculo!
    if old_name != new_name:
        db.query(OrderDB).filter(OrderDB.entity == old_name).update({OrderDB.entity: new_name})
        db.query(BillDB).filter(BillDB.entity == old_name).update({BillDB.entity: new_name})
        db.query(QuoteDB).filter(QuoteDB.entity == old_name).update({QuoteDB.entity: new_name})
        db.query(CardDB).filter(CardDB.entity == old_name).update({CardDB.entity: new_name})

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
    db.add(CardDB(**card.dict()))
    db.commit()
    db.close()
    return {"success": True}

@app.put("/api/cards/{id}")
def update_card(id: int, card: CardSchema):
    db = SessionLocal()
    db_card = db.query(CardDB).filter(CardDB.id == id).first()
    for key, value in card.dict().items(): setattr(db_card, key, value)
    db.commit()
    db.close()
    return {"success": True}

@app.delete("/api/cards/{id}")
def delete_card(id: int):
    db = SessionLocal()
    db.query(CardDB).filter(CardDB.id == id).delete()
    for b in db.query(BillDB).filter(BillDB.card_id == id).all(): b.card_id = None
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
    db.add(OrderDB(**order.dict()))
    db.commit()
    db.close()
    return {"success": True}

@app.put("/api/orders/{id}")
def update_order(id: int, order: OrderSchema):
    db = SessionLocal()
    db_order = db.query(OrderDB).filter(OrderDB.id == id).first()
    for key, value in order.dict().items(): setattr(db_order, key, value)
    db.commit()
    db.close()
    return {"success": True}

@app.put("/api/orders/{id}/status")
def update_order_status(id: int, status: OrderStatusSchema):
    db = SessionLocal()
    db_order = db.query(OrderDB).filter(OrderDB.id == id).first()
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
    db.add(BillDB(**bill.dict()))
    db.commit()
    db.close()
    return {"success": True}

@app.put("/api/bills/{id}/status")
def update_bill_status(id: int, status: BillStatusSchema):
    db = SessionLocal()
    db_bill = db.query(BillDB).filter(BillDB.id == id).first()
    db_bill.is_paid = status.is_paid
    db.commit()
    db.close()
    return {"success": True}

@app.put("/api/bills/{id}")
def update_bill(id: int, update: BillUpdateSchema):
    db = SessionLocal()
    db_bill = db.query(BillDB).filter(BillDB.id == id).first()
    if update.mode == "SINGLE" or not db_bill.group_id:
        db_bill.creditor = update.creditor
        db_bill.entity = update.entity
        db_bill.installment_amount = update.installment_amount
        db_bill.due_date = update.due_date
        db_bill.card_id = update.card_id
    else:
        query = db.query(BillDB).filter(BillDB.group_id == db_bill.group_id)
        if update.mode == "FUTURE": query = query.filter(BillDB.installment_number >= db_bill.installment_number)
        for b in query.all():
            b.creditor = update.creditor
            b.entity = update.entity
            b.installment_amount = update.installment_amount
            b.card_id = update.card_id
            if b.id == db_bill.id: b.due_date = update.due_date
    db.commit()
    db.close()
    return {"success": True}

@app.delete("/api/bills/{id}")
def delete_bill(id: int, mode: str = Query("SINGLE")):
    db = SessionLocal()
    db_bill = db.query(BillDB).filter(BillDB.id == id).first()
    if mode == "SINGLE" or not db_bill.group_id: db.delete(db_bill)
    else:
        query = db.query(BillDB).filter(BillDB.group_id == db_bill.group_id)
        if mode == "FUTURE": query = query.filter(BillDB.installment_number >= db_bill.installment_number)
        query.delete()
    db.commit()
    db.close()
    return {"success": True}

@app.get("/api/quotes")
def get_quotes():
    db = SessionLocal()
    quotes = db.query(QuoteDB).all()
    db.close()
    return quotes

@app.post("/api/quotes")
def create_quote(quote: QuoteSchema):
    db = SessionLocal()
    db.add(QuoteDB(**quote.dict()))
    db.commit()
    db.close()
    return {"success": True}

@app.put("/api/quotes/{id}")
def update_quote(id: int, quote: QuoteSchema):
    db = SessionLocal()
    db_quote = db.query(QuoteDB).filter(QuoteDB.id == id).first()
    for key, value in quote.dict().items(): setattr(db_quote, key, value)
    db.commit()
    db.close()
    return {"success": True}

@app.put("/api/quotes/{id}/status")
def update_quote_status(id: int, status: QuoteStatusSchema):
    db = SessionLocal()
    db_quote = db.query(QuoteDB).filter(QuoteDB.id == id).first()
    db_quote.status = status.status
    db.commit()
    db.close()
    return {"success": True}

@app.delete("/api/quotes/{id}")
def delete_quote(id: int):
    db = SessionLocal()
    db.query(QuoteDB).filter(QuoteDB.id == id).delete()
    db.commit()
    db.close()
    return {"success": True}
