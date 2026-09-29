import os
from typing import List, Optional
from datetime import datetime, date
from calendar import monthrange

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELOS DO BANCO DE DADOS ---
class CompanyProfile(Base):
    __tablename__ = "company_profiles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    logo = Column(String, nullable=True)

class Card(Base):
    __tablename__ = "cards"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    entity = Column(String)
    total_limit = Column(Float, default=0.0)
    closing_day = Column(Integer, default=1)
    due_day = Column(Integer, default=10)

class Quote(Base):
    __tablename__ = "quotes"
    id = Column(Integer, primary_key=True, index=True)
    client = Column(String)
    entity = Column(String)
    items = Column(String)  # JSON string
    payment_terms = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    total_value = Column(Float, default=0.0)
    status = Column(String, default="PENDENTE")
    created_at = Column(String, nullable=True)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    entity = Column(String)
    client = Column(String)
    product = Column(String)
    production_type = Column(String, default="PROPRIA")
    supplier = Column(String, nullable=True)
    supplier_cost = Column(Float, default=0.0)
    status_production = Column(String, default="EM PRODUÇÃO")
    client_due_date = Column(String, nullable=True)
    client_paid_date = Column(String, nullable=True)
    supplier_due_date = Column(String, nullable=True)
    supplier_paid_date = Column(String, nullable=True)
    sale_value = Column(Float, default=0.0)
    paid_by_client = Column(Float, default=0.0)
    paid_to_supplier = Column(Float, default=0.0)
    client_payments = Column(String, nullable=True)  # JSON: [{"date":"YYYY-MM-DD","amount":100.0}]
    supplier_payments = Column(String, nullable=True)  # JSON: [{"date":"YYYY-MM-DD","amount":100.0}]
    is_recurrent = Column(Boolean, default=False)

class Bill(Base):
    __tablename__ = "bills"
    id = Column(Integer, primary_key=True, index=True)
    creditor = Column(String)
    entity = Column(String)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=True)
    total_amount = Column(Float, default=0.0)
    installment_number = Column(Integer, default=1)
    total_installments = Column(Integer, default=1)
    installment_amount = Column(Float, default=0.0)
    due_date = Column(String)
    is_paid = Column(Boolean, default=False)
    paid_date = Column(String, nullable=True)
    is_recurrent = Column(Boolean, default=False)
    group_id = Column(String, nullable=True)

class SystemSetting(Base):
    __tablename__ = "system_settings"
    key = Column(String, primary_key=True, index=True)
    value = Column(String)

Base.metadata.create_all(bind=engine)

# Auto-migração segura: cada coluna é tentada separadamente.
# Se a coluna já existir, o erro é ignorado sem impedir as demais migrações.
def ensure_column(sql: str):
    try:
        with engine.begin() as conn:
            conn.execute(text(sql))
    except Exception:
        pass

ensure_column("ALTER TABLE orders ADD COLUMN client_paid_date VARCHAR")
ensure_column("ALTER TABLE orders ADD COLUMN supplier_paid_date VARCHAR")
ensure_column("ALTER TABLE orders ADD COLUMN client_payments TEXT")
ensure_column("ALTER TABLE orders ADD COLUMN supplier_payments TEXT")
ensure_column("ALTER TABLE bills ADD COLUMN paid_date VARCHAR")

# --- SCHEMAS PYDANTIC ---
class CompanyProfileSchema(BaseModel):
    id: Optional[int] = None
    name: str
    logo: Optional[str] = None
    class Config:
        from_attributes = True

class CardSchema(BaseModel):
    id: Optional[int] = None
    name: str
    entity: str
    total_limit: float
    closing_day: int
    due_day: int
    class Config:
        from_attributes = True

class QuoteSchema(BaseModel):
    id: Optional[int] = None
    client: str
    entity: str
    items: str
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    total_value: float
    status: Optional[str] = "PENDENTE"
    created_at: Optional[str] = None
    class Config:
        from_attributes = True

class OrderSchema(BaseModel):
    id: Optional[int] = None
    entity: str
    client: str
    product: str
    production_type: str = "PROPRIA"
    supplier: Optional[str] = ""
    supplier_cost: float = 0.0
    status_production: str = "EM PRODUÇÃO"
    client_due_date: Optional[str] = None
    client_paid_date: Optional[str] = None
    supplier_due_date: Optional[str] = None
    supplier_paid_date: Optional[str] = None
    sale_value: float = 0.0
    paid_by_client: float = 0.0
    paid_to_supplier: float = 0.0
    client_payments: Optional[str] = None
    supplier_payments: Optional[str] = None
    is_recurrent: bool = False
    class Config:
        from_attributes = True

class BillSchema(BaseModel):
    id: Optional[int] = None
    creditor: str
    entity: str
    card_id: Optional[int] = None
    total_amount: float
    installment_number: int = 1
    total_installments: int = 1
    installment_amount: float
    due_date: str
    is_paid: bool = False
    paid_date: Optional[str] = None
    is_recurrent: bool = False
    group_id: Optional[str] = None
    mode: Optional[str] = "SINGLE"
    class Config:
        from_attributes = True

# --- APP & DEPENDENCIAS ---
app = FastAPI(title="ERP Unificado")
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    if not db.query(CompanyProfile).first():
        db.add(CompanyProfile(name="CVN"))
        db.commit()
    db.close()

# --- ROTAS DE PAGINAS ---
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- API PERFIS ---
@app.get("/api/profiles", response_model=List[CompanyProfileSchema])
def get_profiles(db: Session = Depends(get_db)):
    return db.query(CompanyProfile).all()

@app.post("/api/profiles", response_model=CompanyProfileSchema)
def create_profile(p: CompanyProfileSchema, db: Session = Depends(get_db)):
    db_p = CompanyProfile(name=p.name, logo=p.logo)
    db.add(db_p)
    db.commit()
    db.refresh(db_p)
    return db_p

@app.put("/api/profiles/{id}", response_model=CompanyProfileSchema)
def update_profile(id: int, p: CompanyProfileSchema, db: Session = Depends(get_db)):
    db_p = db.query(CompanyProfile).filter(CompanyProfile.id == id).first()
    if db_p:
        db_p.name = p.name
        if p.logo is not None:
            db_p.logo = p.logo
        db.commit()
        db.refresh(db_p)
    return db_p

@app.delete("/api/profiles/{id}")
def delete_profile(id: int, db: Session = Depends(get_db)):
    db_p = db.query(CompanyProfile).filter(CompanyProfile.id == id).first()
    if db_p:
        db.delete(db_p)
        db.commit()
    return {"ok": True}

# --- API CARTÕES ---
@app.get("/api/cards", response_model=List[CardSchema])
def get_cards(db: Session = Depends(get_db)):
    return db.query(Card).all()

@app.post("/api/cards", response_model=CardSchema)
def create_card(c: CardSchema, db: Session = Depends(get_db)):
    db_c = Card(**c.dict(exclude={"id"}))
    db.add(db_c)
    db.commit()
    db.refresh(db_c)
    return db_c

@app.put("/api/cards/{id}", response_model=CardSchema)
def update_card(id: int, c: CardSchema, db: Session = Depends(get_db)):
    db_c = db.query(Card).filter(Card.id == id).first()
    if db_c:
        for k, v in c.dict(exclude={"id"}).items():
            setattr(db_c, k, v)
        db.commit()
        db.refresh(db_c)
    return db_c

@app.delete("/api/cards/{id}")
def delete_card(id: int, db: Session = Depends(get_db)):
    db_c = db.query(Card).filter(Card.id == id).first()
    if db_c:
        db.delete(db_c)
        db.commit()
    return {"ok": True}

# --- API ORÇAMENTOS ---
@app.get("/api/quotes", response_model=List[QuoteSchema])
def get_quotes(db: Session = Depends(get_db)):
    return db.query(Quote).all()

@app.post("/api/quotes", response_model=QuoteSchema)
def create_quote(q: QuoteSchema, db: Session = Depends(get_db)):
    db_q = Quote(**q.dict(exclude={"id"}))
    db.add(db_q)
    db.commit()
    db.refresh(db_q)
    return db_q

@app.put("/api/quotes/{id}", response_model=QuoteSchema)
def update_quote(id: int, q: QuoteSchema, db: Session = Depends(get_db)):
    db_q = db.query(Quote).filter(Quote.id == id).first()
    if db_q:
        for k, v in q.dict(exclude={"id"}).items():
            setattr(db_q, k, v)
        db.commit()
        db.refresh(db_q)
    return db_q

@app.put("/api/quotes/{id}/status")
def update_quote_status(id: int, data: dict, db: Session = Depends(get_db)):
    db_q = db.query(Quote).filter(Quote.id == id).first()
    if db_q:
        db_q.status = data.get("status", db_q.status)
        db.commit()
    return {"ok": True}

@app.delete("/api/quotes/{id}")
def delete_quote(id: int, db: Session = Depends(get_db)):
    db_q = db.query(Quote).filter(Quote.id == id).first()
    if db_q:
        db.delete(db_q)
        db.commit()
    return {"ok": True}

# --- API PEDIDOS ---
@app.get("/api/orders", response_model=List[OrderSchema])
def get_orders(db: Session = Depends(get_db)):
    return db.query(Order).all()

@app.post("/api/orders", response_model=OrderSchema)
def create_order(o: OrderSchema, db: Session = Depends(get_db)):
    db_o = Order(**o.dict(exclude={"id"}))
    db.add(db_o)
    db.commit()
    db.refresh(db_o)
    return db_o

@app.put("/api/orders/{id}", response_model=OrderSchema)
def update_order(id: int, o: OrderSchema, db: Session = Depends(get_db)):
    db_o = db.query(Order).filter(Order.id == id).first()
    if db_o:
        for k, v in o.dict(exclude={"id"}).items():
            setattr(db_o, k, v)
        db.commit()
        db.refresh(db_o)
    return db_o

@app.put("/api/orders/{id}/status")
def update_order_status(id: int, data: dict, db: Session = Depends(get_db)):
    db_o = db.query(Order).filter(Order.id == id).first()
    if db_o:
        db_o.status_production = data.get("status_production", db_o.status_production)
        db.commit()
    return {"ok": True}

@app.delete("/api/orders/{id}")
def delete_order(id: int, db: Session = Depends(get_db)):
    db_o = db.query(Order).filter(Order.id == id).first()
    if db_o:
        db.delete(db_o)
        db.commit()
    return {"ok": True}

# --- API CONTAS (BILLS) ---
@app.get("/api/bills", response_model=List[BillSchema])
def get_bills(db: Session = Depends(get_db)):
    return db.query(Bill).all()

@app.post("/api/bills", response_model=BillSchema)
def create_bill(b: BillSchema, db: Session = Depends(get_db)):
    data = b.dict(exclude={"id", "mode"})
    db_b = Bill(**data)
    db.add(db_b)
    db.commit()
    db.refresh(db_b)
    return db_b

@app.put("/api/bills/{id}", response_model=BillSchema)
def update_bill(id: int, b: BillSchema, db: Session = Depends(get_db)):
    db_b = db.query(Bill).filter(Bill.id == id).first()
    if db_b:
        data = b.dict(exclude={"id", "mode"})
        for k, v in data.items():
            setattr(db_b, k, v)
        db.commit()
        db.refresh(db_b)
    return db_b

@app.put("/api/bills/{id}/status")
def update_bill_status(id: int, data: dict, db: Session = Depends(get_db)):
    db_b = db.query(Bill).filter(Bill.id == id).first()
    if db_b:
        db_b.is_paid = data.get("is_paid", db_b.is_paid)
        if db_b.is_paid:
            db_b.paid_date = data.get("paid_date") or db_b.paid_date or date.today().isoformat()
        else:
            db_b.paid_date = None
        db.commit()
    return {"ok": True}

@app.delete("/api/bills/{id}")
def delete_bill(id: int, mode: str = "SINGLE", db: Session = Depends(get_db)):
    db_b = db.query(Bill).filter(Bill.id == id).first()
    if db_b:
        if mode == "ALL" and db_b.group_id:
            db.query(Bill).filter(Bill.group_id == db_b.group_id).delete()
        elif mode == "FUTURE" and db_b.group_id:
            db.query(Bill).filter(Bill.group_id == db_b.group_id, Bill.installment_number >= db_b.installment_number).delete()
        else:
            db.delete(db_b)
        db.commit()
    return {"ok": True}

# --- CONFIGURAÇÃO SALDO CAIXA ---
@app.get("/api/settings/balance")
def get_balance(db: Session = Depends(get_db)):
    setting = db.query(SystemSetting).filter(SystemSetting.key == "initial_balance").first()
    val = float(setting.value) if setting else 0.0
    return {"initial_balance": val}

@app.post("/api/settings/balance")
def set_balance(data: dict, db: Session = Depends(get_db)):
    val = str(data.get("initial_balance", 0.0))
    setting = db.query(SystemSetting).filter(SystemSetting.key == "initial_balance").first()
    if setting:
        setting.value = val
    else:
        db.add(SystemSetting(key="initial_balance", value=val))
    db.commit()
    return {"ok": True}
