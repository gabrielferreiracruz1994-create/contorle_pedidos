from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os

DATABASE_URL = "sqlite:///./database.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# MODELOS DO BANCO DE DADOS (SQLAlchemy)
# ==========================================

class ProfileModel(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    logo = Column(String, nullable=True)

class CardModel(Base):
    __tablename__ = "cards"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    entity = Column(String)
    total_limit = Column(Float)
    closing_day = Column(Integer)
    due_day = Column(Integer)

class QuoteModel(Base):
    __tablename__ = "quotes"
    id = Column(Integer, primary_key=True, index=True)
    client = Column(String)
    entity = Column(String)
    items = Column(String)
    payment_terms = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    total_value = Column(Float)
    status = Column(String, default="PENDENTE")
    created_at = Column(String, nullable=True)

class OrderModel(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    entity = Column(String)
    client = Column(String)
    product = Column(String)
    production_type = Column(String)
    supplier = Column(String, nullable=True)
    status_production = Column(String)
    sale_value = Column(Float, default=0.0)
    paid_by_client = Column(Float, default=0.0)
    client_paid_entry_date = Column(String, nullable=True)
    client_paid_final_date = Column(String, nullable=True)
    client_due_date = Column(String, nullable=True)
    supplier_cost = Column(Float, default=0.0)
    paid_to_supplier = Column(Float, default=0.0)
    supplier_paid_entry_date = Column(String, nullable=True)
    supplier_paid_final_date = Column(String, nullable=True)
    supplier_due_date = Column(String, nullable=True)
    is_recurrent = Column(Boolean, default=False)

class BillModel(Base):
    __tablename__ = "bills"
    id = Column(Integer, primary_key=True, index=True)
    creditor = Column(String)
    entity = Column(String)
    total_amount = Column(Float)
    installment_number = Column(Integer, default=1)
    total_installments = Column(Integer, default=1)
    installment_amount = Column(Float)
    due_date = Column(String)
    is_paid = Column(Boolean, default=False)
    is_recurrent = Column(Boolean, default=False)
    card_id = Column(Integer, nullable=True)
    group_id = Column(String, nullable=True)

class SettingModel(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True, index=True)
    value = Column(String)

Base.metadata.create_all(bind=engine)

# ==========================================
# SCHEMAS PYDANTIC
# ==========================================

class ProfileSchema(BaseModel):
    name: str
    logo: Optional[str] = None

class CardSchema(BaseModel):
    name: str
    entity: str
    total_limit: float
    closing_day: int
    due_day: int

class QuoteSchema(BaseModel):
    client: str
    entity: str
    items: str
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    total_value: float
    status: Optional[str] = "PENDENTE"
    created_at: Optional[str] = None

class OrderSchema(BaseModel):
    entity: str
    client: str
    product: str
    production_type: str
    supplier: Optional[str] = ""
    status_production: str
    sale_value: float = 0.0
    paid_by_client: float = 0.0
    client_paid_entry_date: Optional[str] = None
    client_paid_final_date: Optional[str] = None
    client_due_date: Optional[str] = None
    supplier_cost: float = 0.0
    paid_to_supplier: float = 0.0
    supplier_paid_entry_date: Optional[str] = None
    supplier_paid_final_date: Optional[str] = None
    supplier_due_date: Optional[str] = None
    is_recurrent: bool = False

class BillSchema(BaseModel):
    creditor: str
    entity: str
    total_amount: float
    installment_number: int = 1
    total_installments: int = 1
    installment_amount: float
    due_date: str
    is_recurrent: bool = False
    card_id: Optional[int] = None
    mode: Optional[str] = "SINGLE"

class BalanceSchema(BaseModel):
    initial_balance: float

# ==========================================
# APLICAÇÃO FASTAPI
# ==========================================

app = FastAPI(title="ERP Unificado API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# PROFILES
@app.get("/api/profiles")
def get_profiles(db: Session = Depends(get_db)):
    return db.query(ProfileModel).all()

@app.post("/api/profiles")
def create_profile(data: ProfileSchema, db: Session = Depends(get_db)):
    p = ProfileModel(name=data.name, logo=data.logo)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

@app.put("/api/profiles/{id}")
def update_profile(id: int, data: ProfileSchema, db: Session = Depends(get_db)):
    p = db.query(ProfileModel).filter(ProfileModel.id == id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    p.name = data.name
    if data.logo is not None:
        p.logo = data.logo
    db.commit()
    return p

@app.delete("/api/profiles/{id}")
def delete_profile(id: int, db: Session = Depends(get_db)):
    p = db.query(ProfileModel).filter(ProfileModel.id == id).first()
    if p:
        db.delete(p)
        db.commit()
    return {"ok": True}

# CARDS
@app.get("/api/cards")
def get_cards(db: Session = Depends(get_db)):
    return db.query(CardModel).all()

@app.post("/api/cards")
def create_card(data: CardSchema, db: Session = Depends(get_db)):
    c = CardModel(**data.dict())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

@app.delete("/api/cards/{id}")
def delete_card(id: int, db: Session = Depends(get_db)):
    c = db.query(CardModel).filter(CardModel.id == id).first()
    if c:
        db.delete(c)
        db.commit()
    return {"ok": True}

# QUOTES
@app.get("/api/quotes")
def get_quotes(db: Session = Depends(get_db)):
    return db.query(QuoteModel).all()

@app.post("/api/quotes")
def create_quote(data: QuoteSchema, db: Session = Depends(get_db)):
    q = QuoteModel(**data.dict())
    db.add(q)
    db.commit()
    db.refresh(q)
    return q

@app.put("/api/quotes/{id}")
def update_quote(id: int, data: QuoteSchema, db: Session = Depends(get_db)):
    q = db.query(QuoteModel).filter(QuoteModel.id == id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    for k, v in data.dict().items():
        setattr(q, k, v)
    db.commit()
    return q

@app.put("/api/quotes/{id}/status")
def update_quote_status(id: int, payload: dict, db: Session = Depends(get_db)):
    q = db.query(QuoteModel).filter(QuoteModel.id == id).first()
    if q:
        q.status = payload.get("status", "PENDENTE")
        db.commit()
    return {"ok": True}

@app.delete("/api/quotes/{id}")
def delete_quote(id: int, db: Session = Depends(get_db)):
    q = db.query(QuoteModel).filter(QuoteModel.id == id).first()
    if q:
        db.delete(q)
        db.commit()
    return {"ok": True}

# ORDERS
@app.get("/api/orders")
def get_orders(db: Session = Depends(get_db)):
    return db.query(OrderModel).all()

@app.post("/api/orders")
def create_order(data: OrderSchema, db: Session = Depends(get_db)):
    o = OrderModel(**data.dict())
    db.add(o)
    db.commit()
    db.refresh(o)
    return o

@app.put("/api/orders/{id}")
def update_order(id: int, data: OrderSchema, db: Session = Depends(get_db)):
    o = db.query(OrderModel).filter(OrderModel.id == id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    for k, v in data.dict().items():
        setattr(o, k, v)
    db.commit()
    return o

@app.put("/api/orders/{id}/status")
def update_order_status(id: int, payload: dict, db: Session = Depends(get_db)):
    o = db.query(OrderModel).filter(OrderModel.id == id).first()
    if o:
        o.status_production = payload.get("status_production", o.status_production)
        db.commit()
    return {"ok": True}

@app.delete("/api/orders/{id}")
def delete_order(id: int, db: Session = Depends(get_db)):
    o = db.query(OrderModel).filter(OrderModel.id == id).first()
    if o:
        db.delete(o)
        db.commit()
    return {"ok": True}

# BILLS
@app.get("/api/bills")
def get_bills(db: Session = Depends(get_db)):
    return db.query(BillModel).all()

@app.post("/api/bills")
def create_bill(data: BillSchema, db: Session = Depends(get_db)):
    b = BillModel(
        creditor=data.creditor,
        entity=data.entity,
        total_amount=data.total_amount,
        installment_number=data.installment_number,
        total_installments=data.total_installments,
        installment_amount=data.installment_amount,
        due_date=data.due_date,
        is_recurrent=data.is_recurrent,
        card_id=data.card_id
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b

@app.put("/api/bills/{id}")
def update_bill(id: int, data: BillSchema, db: Session = Depends(get_db)):
    b = db.query(BillModel).filter(BillModel.id == id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    b.creditor = data.creditor
    b.entity = data.entity
    b.installment_amount = data.installment_amount
    b.total_amount = data.total_amount
    b.due_date = data.due_date
    b.card_id = data.card_id
    b.is_recurrent = data.is_recurrent
    db.commit()
    return b

@app.put("/api/bills/{id}/status")
def update_bill_status(id: int, payload: dict, db: Session = Depends(get_db)):
    b = db.query(BillModel).filter(BillModel.id == id).first()
    if b:
        b.is_paid = payload.get("is_paid", False)
        db.commit()
    return {"ok": True}

@app.delete("/api/bills/{id}")
def delete_bill(id: int, mode: str = Query("SINGLE"), db: Session = Depends(get_db)):
    b = db.query(BillModel).filter(BillModel.id == id).first()
    if b:
        db.delete(b)
        db.commit()
    return {"ok": True}

# BALANCE SETTINGS
@app.get("/api/settings/balance")
def get_balance(db: Session = Depends(get_db)):
    s = db.query(SettingModel).filter(SettingModel.key == "initial_balance").first()
    return {"initial_balance": float(s.value) if s else 0.0}

@app.post("/api/settings/balance")
def set_balance(data: BalanceSchema, db: Session = Depends(get_db)):
    s = db.query(SettingModel).filter(SettingModel.key == "initial_balance").first()
    if not s:
        s = SettingModel(key="initial_balance", value=str(data.initial_balance))
        db.add(s)
    else:
        s.value = str(data.initial_balance)
    db.commit()
    return {"initial_balance": data.initial_balance}

if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
