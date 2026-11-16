from datetime import datetime, timezone
import os
from pathlib import Path
from sqlalchemy import create_engine, String, JSON, ForeignKey, UniqueConstraint, event, Integer, Boolean,text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__='users'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    role:Mapped[str]=mapped_column(String,index=True)
    payload:Mapped[dict]=mapped_column(JSON)

class AuthSession(Base):
    __tablename__='auth_sessions'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    expires_at:Mapped[int]=mapped_column(Integer,index=True)
    revoked:Mapped[bool]=mapped_column(Boolean,default=False)
class AuthThrottle(Base):
    __tablename__='auth_throttles'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    failures:Mapped[int]=mapped_column(Integer)
    window_started:Mapped[int]=mapped_column(Integer)

class Plant(Base):
    __tablename__='plants'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    payload:Mapped[dict]=mapped_column(JSON)
class Item(Base):
    __tablename__='items'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    payload:Mapped[dict]=mapped_column(JSON)
class Supplier(Base):
    __tablename__='suppliers'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    payload:Mapped[dict]=mapped_column(JSON)
class History(Base):
    __tablename__='historical_po_lines'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    item_id:Mapped[str]=mapped_column(ForeignKey('items.id'),index=True)
    supplier_id:Mapped[str]=mapped_column(ForeignKey('suppliers.id'),index=True)
    payload:Mapped[dict]=mapped_column(JSON)
class Contract(Base):
    __tablename__='contracts'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    supplier_id:Mapped[str]=mapped_column(ForeignKey('suppliers.id'),index=True)
    payload:Mapped[dict]=mapped_column(JSON)
class ContractLine(Base):
    __tablename__='contract_lines'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    contract_id:Mapped[str]=mapped_column(ForeignKey('contracts.id'),index=True)
    item_id:Mapped[str]=mapped_column(ForeignKey('items.id'),index=True)
    payload:Mapped[dict]=mapped_column(JSON)
class Dataset(Base):
    __tablename__='data_snapshots'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    payload:Mapped[dict]=mapped_column(JSON)
class Policy(Base):
    __tablename__='policy_versions'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    status:Mapped[str]=mapped_column(String,index=True)
    payload:Mapped[dict]=mapped_column(JSON)
class Run(Base):
    __tablename__='processing_runs'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    created_at:Mapped[str]=mapped_column(String)
    input_hash:Mapped[str]=mapped_column(String,index=True)
    data_hash:Mapped[str]=mapped_column(ForeignKey('data_snapshots.id'))
    payload:Mapped[dict]=mapped_column(JSON)
class Requisition(Base):
    __tablename__='purchase_requisitions'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    payload:Mapped[dict]=mapped_column(JSON)
class RequisitionLine(Base):
    __tablename__='pr_lines'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    requisition_id:Mapped[str]=mapped_column(ForeignKey('purchase_requisitions.id'),index=True)
    payload:Mapped[dict]=mapped_column(JSON)
class RequirementRecord(Base):
    __tablename__='run_requirements'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    run_id:Mapped[str]=mapped_column(ForeignKey('processing_runs.id'),index=True)
    group_id:Mapped[str]=mapped_column(String,index=True)
    payload:Mapped[dict]=mapped_column(JSON)
class Membership(Base):
    __tablename__='requirement_pr_membership'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    requirement_id:Mapped[str]=mapped_column(ForeignKey('run_requirements.id'),index=True)
    pr_line_id:Mapped[str]=mapped_column(ForeignKey('pr_lines.id'),index=True)
class PolicyApproval(Base):
    __tablename__='policy_approvals'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    policy_id:Mapped[str]=mapped_column(ForeignKey('policy_versions.id'),index=True)
    payload:Mapped[dict]=mapped_column(JSON)
class PurchaseOrder(Base):
    __tablename__='purchase_orders'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    run_id:Mapped[str]=mapped_column(ForeignKey('processing_runs.id'),index=True)
    supplier_id:Mapped[str]=mapped_column(ForeignKey('suppliers.id'))
    payload:Mapped[dict]=mapped_column(JSON)
class PurchaseOrderLine(Base):
    __tablename__='purchase_order_lines'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    order_id:Mapped[str]=mapped_column(ForeignKey('purchase_orders.id'),index=True)
    requirement_id:Mapped[str]=mapped_column(ForeignKey('run_requirements.id'),index=True)
    payload:Mapped[dict]=mapped_column(JSON)
class SourcingRequest(Base):
    __tablename__='sourcing_requests'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    run_id:Mapped[str]=mapped_column(ForeignKey('processing_runs.id'))
    payload:Mapped[dict]=mapped_column(JSON)
class Commitment(Base):
    __tablename__='approved_pr_lines'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    action_id:Mapped[str]=mapped_column(String)
class ContractLedger(Base):
    __tablename__='contract_ledger'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    contract_id:Mapped[str]=mapped_column(ForeignKey('contracts.id'),index=True)
    payload:Mapped[dict]=mapped_column(JSON)
class Override(Base):
    __tablename__='buyer_overrides'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    payload:Mapped[dict]=mapped_column(JSON)
class Audit(Base):
    __tablename__='audit_events'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    created_at:Mapped[str]=mapped_column(String,index=True)
    payload:Mapped[dict]=mapped_column(JSON)
class Chat(Base):
    __tablename__='chat_sessions'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    payload:Mapped[dict]=mapped_column(JSON)
class ChatMessage(Base):
    __tablename__='chat_messages'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    chat_id:Mapped[str]=mapped_column(ForeignKey('chat_sessions.id'),index=True)
    payload:Mapped[dict]=mapped_column(JSON)
class ContractProposal(Base):
    __tablename__='contract_proposals'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    payload:Mapped[dict]=mapped_column(JSON)

def now(): return datetime.now(timezone.utc).isoformat()

CATALOG_LOCK=63827101
POLICY_CALENDAR_LOCK=63827102

def transaction_lock(session,key,exclusive=False):
    if session.bind.dialect.name=='postgresql':
        statement='SELECT pg_advisory_xact_lock(:key)' if exclusive else 'SELECT pg_advisory_xact_lock_shared(:key)'
        session.execute(text(statement),{'key':key})

def connect(url=None):
    if os.getenv('VERCEL') and not (url or os.getenv('DATABASE_URL')):
        raise RuntimeError('Persistent DATABASE_URL is required on Vercel; SQLite fallback is disabled')
    url=url or os.getenv('DATABASE_URL','sqlite:///.private/corvo.db')
    from .workspace import check_workspace_database
    check_workspace_database(url)
    if url.startswith('postgres://'): url=url.replace('postgres://','postgresql+psycopg://',1)
    if url.startswith('postgresql://'): url=url.replace('postgresql://','postgresql+psycopg://',1)
    if url.startswith('sqlite:///.private/'): Path('.private').mkdir(exist_ok=True)
    options={'connect_args':{'check_same_thread':False}} if url.startswith('sqlite') else {'connect_args':{'prepare_threshold':None,'connect_timeout':20},'pool_size':2,'max_overflow':1,'pool_recycle':240}
    engine=create_engine(url,**options,pool_pre_ping=True,hide_parameters=True)
    if url.startswith('sqlite'):
        @event.listens_for(engine,'connect')
        def configure(dbapi,_):
            dbapi.execute('PRAGMA foreign_keys=ON'); dbapi.execute('PRAGMA busy_timeout=10000')
    return engine,sessionmaker(engine,expire_on_commit=False)
