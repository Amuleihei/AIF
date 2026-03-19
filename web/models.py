import os
import secrets

from sqlalchemy import create_engine, Column, Integer, String, Float, Text, UniqueConstraint, Index, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from flask_login import UserMixin
from datetime import datetime
from pathlib import Path
from werkzeug.security import check_password_hash, generate_password_hash

# 数据库配置
DB_PATH = Path(__file__).resolve().parent.parent / "unified.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"timeout": 30},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _conn_record):
    # 读写优化：WAL + NORMAL，降低锁等待，提升页面并发响应。
    cur = dbapi_conn.cursor()
    try:
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA synchronous=NORMAL;")
        cur.execute("PRAGMA temp_store=MEMORY;")
        cur.execute("PRAGMA cache_size=-20000;")
        cur.execute("PRAGMA busy_timeout=30000;")
    finally:
        cur.close()

Base = declarative_base()
Session = sessionmaker(bind=engine, expire_on_commit=False)

class User(UserMixin, Base):
    """用户表"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password = Column(String(120), nullable=False)
    role = Column(String(20), default='user')  # admin/boss/finance/user

    def set_password(self, plain_password: str) -> None:
        self.password = generate_password_hash(str(plain_password or ""))

    @staticmethod
    def _is_password_hash(value: str) -> bool:
        text = str(value or "")
        return text.startswith("pbkdf2:") or text.startswith("scrypt:")

    def verify_password(self, plain_password: str) -> bool:
        raw = str(self.password or "")
        given = str(plain_password or "")
        if self._is_password_hash(raw):
            try:
                return check_password_hash(raw, given)
            except Exception:
                return False
        # 兼容旧库明文密码
        return raw == given

    def has_permission(self, permission):
        role_permissions = {
            'admin': ['admin', 'view', 'edit', 'export', 'delete', 'manage_users'],
            'boss': ['view'],  # 只能查看
            'finance': ['view', 'export', 'edit'],  # 查看、导出、编辑
        }
        user_permissions = role_permissions.get(self.role, [])
        return permission in user_permissions

class TrayBatch(Base):
    """托批次编号表"""
    __tablename__ = 'tray_batches'

    id = Column(Integer, primary_key=True)
    batch_number = Column(String(50), unique=True, nullable=False)  # 批次编号
    kiln_id = Column(String(10), nullable=False)  # 窑ID
    tray_count = Column(Integer, default=0)  # 托数量
    total_volume = Column(Float, default=0.0)  # 总立方数
    status = Column(String(20), default='active')  # active/completed
    created_at = Column(String(50), default=lambda: datetime.now().isoformat())
    created_by = Column(String(80))  # 创建者用户名

class ProductBatch(Base):
    """成品批次编号表"""
    __tablename__ = 'product_batches'

    id = Column(Integer, primary_key=True)
    batch_number = Column(String(50), unique=True, nullable=False)  # 成品批次编号
    tray_batch_id = Column(Integer, nullable=True)  # 关联的托批次ID
    product_count = Column(Integer, default=0)  # 成品数量
    total_volume = Column(Float, default=0.0)  # 总立方数
    status = Column(String(20), default='active')  # active/shipped
    created_at = Column(String(50), default=lambda: datetime.now().isoformat())
    created_by = Column(String(80))  # 创建者用户名

class LogEntry(Base):
    """原木入库记录表"""
    __tablename__ = 'log_entries'

    id = Column(Integer, primary_key=True)
    truck_number = Column(String(50), nullable=False)  # 车牌号
    driver_name = Column(String(80), nullable=False)  # 司机姓名
    log_amount = Column(Float, nullable=False)  # 原木入库数量(MT)
    created_at = Column(String(50), default=lambda: datetime.now().isoformat())
    created_by = Column(String(80))  # 创建者用户名

class LogEntryMeta(Base):
    """原木入库扩展信息（尺寸区间与单价）"""
    __tablename__ = "log_entry_meta"

    id = Column(Integer, primary_key=True)
    log_entry_id = Column(Integer, nullable=False, unique=True)
    size_range = Column(String(80), default="")
    price_per_mt = Column(Float, default=0.0)
    created_at = Column(String(50), default=lambda: datetime.now().isoformat())
    created_by = Column(String(80))

class LogEntryDetail(Base):
    """原木入库明细（尺寸/长度/数量/折算MT）"""
    __tablename__ = "log_entry_details"

    id = Column(Integer, primary_key=True)
    log_entry_id = Column(Integer, nullable=False)
    size_mm = Column(Integer, default=0)
    length_ft = Column(Integer, default=3)
    quantity = Column(Integer, default=0)
    consumed_mt = Column(Float, default=0.0)
    created_at = Column(String(50), default=lambda: datetime.now().isoformat())
    created_by = Column(String(80))

class LogDriverProfile(Base):
    """司机常用原木规格价格（用于自动回填）"""
    __tablename__ = "log_driver_profiles"

    id = Column(Integer, primary_key=True)
    driver_name = Column(String(80), nullable=False, unique=True)
    size_range = Column(String(80), default="")
    price_per_mt = Column(Float, default=0.0)
    updated_at = Column(String(50), default=lambda: datetime.now().isoformat())
    updated_by = Column(String(80))

class LogPricingProfile(Base):
    """司机+车牌价目配置（用于自动回填）"""
    __tablename__ = "log_pricing_profiles"

    id = Column(Integer, primary_key=True)
    driver_name = Column(String(80), nullable=False)
    truck_number = Column(String(50), default="")
    updated_at = Column(String(50), default=lambda: datetime.now().isoformat())
    updated_by = Column(String(80))
    __table_args__ = (UniqueConstraint("driver_name", "truck_number", name="uq_log_pricing_driver_truck"),)


class LogPricingRule(Base):
    """司机价目分段规则"""
    __tablename__ = "log_pricing_rules"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, nullable=False)
    rule_key = Column(String(40), nullable=False)
    rule_label = Column(String(80), default="")
    min_size = Column(Float, default=0.0)
    max_size = Column(Float, default=0.0)
    is_max_open = Column(Integer, default=0)  # 1: 无上限
    price_per_mt = Column(Float, default=0.0)
    enabled = Column(Integer, default=0)
    updated_at = Column(String(50), default=lambda: datetime.now().isoformat())
    __table_args__ = (UniqueConstraint("profile_id", "rule_key", name="uq_log_pricing_profile_rule"),)


class LogEntrySettlement(Base):
    """每次原木入库的分段汇总（MT 与金额）"""
    __tablename__ = "log_entry_settlements"

    id = Column(Integer, primary_key=True)
    log_entry_id = Column(Integer, nullable=False)
    driver_name = Column(String(80), default="")
    truck_number = Column(String(50), default="")
    rule_key = Column(String(40), default="")
    rule_label = Column(String(80), default="")
    price_per_mt = Column(Float, default=0.0)
    mt = Column(Float, default=0.0)
    amount_ks = Column(Float, default=0.0)
    created_at = Column(String(50), default=lambda: datetime.now().isoformat())
    created_by = Column(String(80))

class LogConsumption(Base):
    """原木消耗记录表"""
    __tablename__ = 'log_consumptions'

    id = Column(Integer, primary_key=True)
    log_entry_id = Column(Integer, nullable=True)  # 关联的入库记录ID
    consumed_amount = Column(Float, nullable=False)  # 消耗数量(MT)
    operation_type = Column(String(50), default='saw')  # 操作类型：saw(锯解)等
    created_at = Column(String(50), default=lambda: datetime.now().isoformat())
    created_by = Column(String(80))  # 操作者用户名

class SawRecord(Base):
    """锯解记录"""
    __tablename__ = 'saw_records'

    id = Column(Integer, primary_key=True)
    saw_mt = Column(Float, nullable=False)
    saw_trays = Column(Integer, nullable=False)
    bark_sales_amount = Column(Float, default=0.0)
    dust_sales_amount = Column(Float, default=0.0)
    created_at = Column(String(50), default=lambda: datetime.now().isoformat())
    created_by = Column(String(80))

class SawMachineRecord(Base):
    """单次锯机记录（保留 1-6 号锯历史）"""
    __tablename__ = 'saw_machine_records'

    id = Column(Integer, primary_key=True)
    saw_record_id = Column(Integer, nullable=True)
    machine_no = Column(Integer, nullable=False)
    saw_mt = Column(Float, default=0.0)
    saw_trays = Column(Integer, default=0)
    bark_m3 = Column(Float, default=0.0)
    dust_bags = Column(Integer, default=0)
    created_at = Column(String(50), default=lambda: datetime.now().isoformat())
    created_by = Column(String(80))

class SawMachineLogDetail(Base):
    """锯机原木消耗明细（尺寸/长度/数量）"""
    __tablename__ = 'saw_machine_log_details'

    id = Column(Integer, primary_key=True)
    machine_record_id = Column(Integer, nullable=True)
    saw_record_id = Column(Integer, nullable=True)
    machine_no = Column(Integer, nullable=False)
    size_mm = Column(Integer, default=0)
    length_ft = Column(Integer, default=3)
    quantity = Column(Integer, default=0)
    consumed_mt = Column(Float, default=0.0)
    created_at = Column(String(50), default=lambda: datetime.now().isoformat())
    created_by = Column(String(80))

class DipRecord(Base):
    """药浸记录"""
    __tablename__ = 'dip_records'

    id = Column(Integer, primary_key=True)
    dip_cans = Column(Integer, nullable=False)
    dip_trays = Column(Integer, nullable=False)
    dip_chemicals = Column(Float, default=0.0)
    created_at = Column(String(50), default=lambda: datetime.now().isoformat())
    created_by = Column(String(80))

class SortRecord(Base):
    """拣选记录"""
    __tablename__ = 'sort_records'

    id = Column(Integer, primary_key=True)
    sort_trays = Column(Integer, nullable=False)
    sorted_kiln_trays = Column(String, default="")
    created_at = Column(String(50), default=lambda: datetime.now().isoformat())
    created_by = Column(String(80))

class ByproductRecord(Base):
    """副产品记录（树皮金额 + 木渣袋库存流转）"""
    __tablename__ = 'byproduct_records'

    id = Column(Integer, primary_key=True)
    bark_sale_amount = Column(Float, default=0.0)
    dust_bags_in = Column(Integer, default=0)
    dust_bags_out = Column(Integer, default=0)
    dust_sale_amount = Column(Float, default=0.0)
    created_at = Column(String(50), default=lambda: datetime.now().isoformat())
    created_by = Column(String(80))
class InventoryRaw(Base):
    """原材料库存"""
    __tablename__ = 'inventory_raw'

    material = Column(String(50), primary_key=True)
    volume = Column(Float, default=0.0)

class InventoryWip(Base):
    """半成品库存"""
    __tablename__ = 'inventory_wip'

    batch_number = Column(String(50), primary_key=True)
    kiln_id = Column(String(10))
    tray_count = Column(Integer, default=0)
    total_volume = Column(Float, default=0.0)
    status = Column(String(20), default='active')
    created_at = Column(String(50))
    created_by = Column(String(80))

class InventoryProduct(Base):
    """成品库存"""
    __tablename__ = 'inventory_product'

    product_id = Column(String(50), primary_key=True)
    spec = Column(String(50))
    grade = Column(String(10))
    pcs = Column(Integer, default=0)
    volume = Column(Float, default=0.0)
    status = Column(String(20), default='库存')

class FinanceAccount(Base):
    """财务账户"""
    __tablename__ = 'finance_accounts'

    account_name = Column(String(50), primary_key=True)
    balance = Column(Float, default=0.0)

class FinanceRecord(Base):
    """财务记录"""
    __tablename__ = 'finance_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(String(50))
    type = Column(String(20))
    amount = Column(Float)
    account = Column(String(50))
    note = Column(String(200))

class HrEmployee(Base):
    """员工信息"""
    __tablename__ = 'hr_employees'

    id = Column(String(50), primary_key=True)
    name = Column(String(80))
    position = Column(String(50))
    salary = Column(Float)

class Order(Base):
    """订单"""
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    order_data = Column(String)  # JSON string

class OrderConfig(Base):
    """订单配置"""
    __tablename__ = 'order_config'

    key = Column(String(50), primary_key=True)
    value = Column(String(50))

class SystemConfig(Base):
    """系统配置"""
    __tablename__ = 'system_config'

    key = Column(String(50), primary_key=True)
    value = Column(String)  # JSON string


class FlowMetric(Base):
    """流程标量数据（替代 flow_data JSON 的简单字段）"""
    __tablename__ = "flow_metrics"

    key = Column(String(64), primary_key=True)
    value = Column(String(200), default="")


class FlowSelectedTray(Base):
    """待入窑托明细（selected_trays）"""
    __tablename__ = "flow_selected_trays"

    tray_id = Column(String(64), primary_key=True)
    length_mm = Column(Integer, default=0)
    width_mm = Column(Integer, default=0)
    thick_mm = Column(Integer, default=0)
    pcs = Column(Integer, default=0)
    spec = Column(String(64), default="")
    full_spec = Column(String(64), default="")
    seq = Column(Integer, default=0)


class FlowSelectedTrayDetail(Base):
    """Web 待入窑池明细（selected_tray_details）"""
    __tablename__ = "flow_selected_tray_details"

    tray_id = Column(String(64), primary_key=True)
    spec = Column(String(64), default="")
    count = Column(Integer, default=0)
    volume = Column(Float, default=0.0)
    batch_number = Column(String(64), default="")
    seq = Column(Integer, default=0)


class FlowKilnDoneTray(Base):
    """出窑待二选托明细（kiln_done_trays）"""
    __tablename__ = "flow_kiln_done_trays"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tray_id = Column(String(64), default="")
    spec = Column(String(64), default="")
    seq = Column(Integer, default=0)


class FlowSawMachineTotal(Base):
    """锯机累计统计（saw_machine_totals）"""
    __tablename__ = "flow_saw_machine_totals"

    machine_no = Column(Integer, primary_key=True)
    mt = Column(Float, default=0.0)
    tray = Column(Integer, default=0)


class FlowSawMachineDaily(Base):
    """锯机日统计（saw_machine_daily）"""
    __tablename__ = "flow_saw_machine_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    day = Column(String(20), nullable=False)
    machine_no = Column(Integer, nullable=False)
    mt = Column(Float, default=0.0)
    tray = Column(Integer, default=0)
    bark = Column(Integer, default=0)
    dust = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint("day", "machine_no", name="uq_flow_saw_machine_daily"),)


class FlowSecondSortRecord(Base):
    """二次拣选记录（second_sort_records）"""
    __tablename__ = "flow_second_sort_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(String(50), default=lambda: datetime.now().isoformat())
    trays = Column(Integer, default=0)
    ok_m3 = Column(Float, default=0.0)
    ab_m3 = Column(Float, default=0.0)
    bc_m3 = Column(Float, default=0.0)
    loss_m3 = Column(Float, default=0.0)
    spec_summary = Column(Text, default="")


class KilnState(Base):
    """窑状态（替代 kilns JSON 的窑头字段）"""
    __tablename__ = "kiln_states"

    kiln_id = Column(String(8), primary_key=True)
    status = Column(String(20), default="empty")
    start = Column(String(50), default="")
    dry_start = Column(String(50), default="")
    completed_time = Column(String(50), default="")
    last_volume = Column(Float, default=0.0)
    unloaded_count = Column(Integer, default=0)
    unloading_total_trays = Column(Integer, default=0)
    unloading_out_trays = Column(Integer, default=0)
    unloading_out_applied = Column(Integer, default=0)
    last_trays = Column(Integer, default=0)
    manual_elapsed_hours = Column(Integer, default=0)
    manual_remaining_hours = Column(Integer, default=0)


class KilnTray(Base):
    """窑内托明细（kilns[k].trays）"""
    __tablename__ = "kiln_trays"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kiln_id = Column(String(8), nullable=False)
    tray_id = Column(String(64), default="")
    spec = Column(String(64), default="")
    count = Column(Integer, default=0)
    volume = Column(Float, default=0.0)
    batch_number = Column(String(64), default="")
    seq = Column(Integer, default=0)


class ShippingOrder(Base):
    """发货单（替代 shipping_data JSON 头）"""
    __tablename__ = "shipping_orders"

    shipment_no = Column(String(64), primary_key=True)
    customer = Column(String(120), default="")
    destination = Column(String(120), default="")
    vehicle_no = Column(String(64), default="")
    driver_name = Column(String(80), default="")
    tracking_no = Column(String(80), default="")
    departure_at = Column(String(50), default="")
    eta_hours_to_yangon = Column(Integer, default=36)
    yangon_arrived_at = Column(String(50), default="")
    yangon_departed_at = Column(String(50), default="")
    china_port_arrived_at = Column(String(50), default="")
    status = Column(String(40), default="去仰光途中")
    remark = Column(String(300), default="")
    created_at = Column(String(50), default=lambda: datetime.now().isoformat())
    updated_at = Column(String(50), default=lambda: datetime.now().isoformat())


class ShippingOrderItem(Base):
    """发货单产品行（shipping_data.shipments[].products）"""
    __tablename__ = "shipping_order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_no = Column(String(64), nullable=False)
    product_id = Column(String(64), default="")
    spec = Column(String(64), default="")
    grade = Column(String(20), default="")
    pcs = Column(Integer, default=0)
    volume = Column(Float, default=0.0)
    status = Column(String(40), default="运输中")
    seq = Column(Integer, default=0)


class TgSetting(Base):
    """TG 系统设置（替代 tg_system_cfg JSON）"""
    __tablename__ = "tg_settings"

    key = Column(String(80), primary_key=True)
    value = Column(String(200), default="")


class TgPendingUser(Base):
    """TG 待审核用户（替代 tg_pending_users JSON）"""
    __tablename__ = "tg_pending_users"

    user_id = Column(String(50), primary_key=True)
    username = Column(String(120), default="")
    created_at = Column(Integer, default=0)


class TgUserRole(Base):
    """TG 用户角色"""
    __tablename__ = "tg_user_roles"

    user_id = Column(String(50), primary_key=True)
    role = Column(String(20), default="")


class AdminAuditLog(Base):
    """管理员操作审计日志"""
    __tablename__ = "admin_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    operator = Column(String(80), default="")
    action = Column(String(80), default="")
    target = Column(String(120), default="")
    detail = Column(String(500), default="")
    created_at = Column(String(50), default=lambda: datetime.now().isoformat())
    __table_args__ = (
        Index("idx_admin_audit_created_at", "created_at"),
        Index("idx_admin_audit_action", "action"),
        Index("idx_admin_audit_operator", "operator"),
    )


class LoginSecurity(Base):
    """登录安全控制（失败次数/锁定）"""
    __tablename__ = "login_security"

    username = Column(String(80), primary_key=True)
    failed_count = Column(Integer, default=0)
    locked_until_ts = Column(Integer, default=0)
    last_fail_ts = Column(Integer, default=0)


class LoginTrustedIp(Base):
    """登录可信 IP（用于外网异地登录提醒）"""
    __tablename__ = "login_trusted_ips"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), nullable=False)
    ip = Column(String(80), nullable=False)
    first_seen_ts = Column(Integer, default=0)
    last_seen_ts = Column(Integer, default=0)
    last_user_agent = Column(String(300), default="")
    __table_args__ = (UniqueConstraint("username", "ip", name="uq_login_trusted_user_ip"),)
def migrate_legacy_password_hashes(session) -> int:
    changed = 0
    users = session.query(User).all()
    for user in users:
        if User._is_password_hash(user.password):
            continue
        if not str(user.password or "").strip():
            continue
        user.password = generate_password_hash(str(user.password))
        changed += 1
    return changed


def _ensure_runtime_indexes() -> None:
    # 兼容已存在表：补齐高频筛选索引，提升审计页加载速度。
    with engine.begin() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_admin_audit_created_at ON admin_audit_logs(created_at)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_admin_audit_action ON admin_audit_logs(action)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_admin_audit_operator ON admin_audit_logs(operator)"))


# 创建默认用户
def create_default_user():
    Base.metadata.create_all(engine)  # 确保表被创建
    _ensure_runtime_indexes()
    session = Session()

    if migrate_legacy_password_hashes(session) > 0:
        print("🔐 已完成旧版明文密码自动升级（转为哈希存储）")

    has_any_user = session.query(User).first() is not None
    if has_any_user:
        session.commit()
        session.close()
        return

    # 空库时仅在显式配置了密码后才引导创建默认用户，避免弱口令落地。
    bootstrap = [
        {
            "username": os.getenv("AIF_BOOTSTRAP_ADMIN_USER", "admin"),
            "password": os.getenv("AIF_BOOTSTRAP_ADMIN_PASSWORD", "").strip(),
            "role": "admin",
        },
        {
            "username": os.getenv("AIF_BOOTSTRAP_BOSS_USER", "boss"),
            "password": os.getenv("AIF_BOOTSTRAP_BOSS_PASSWORD", "").strip(),
            "role": "boss",
        },
        {
            "username": os.getenv("AIF_BOOTSTRAP_FINANCE_USER", "finance"),
            "password": os.getenv("AIF_BOOTSTRAP_FINANCE_PASSWORD", "").strip(),
            "role": "finance",
        },
    ]

    if not bootstrap[0]["password"]:
        one_time = secrets.token_urlsafe(12)
        print("⚠️ 空库未检测到 AIF_BOOTSTRAP_ADMIN_PASSWORD，已跳过默认账号创建。")
        print(f"⚠️ 建议设置环境变量后重启服务，例如管理员初始口令：{one_time}")
        session.commit()
        session.close()
        return

    next_id = 1
    for row in bootstrap:
        if not row["password"]:
            continue
        user = User(
            id=next_id,
            username=row["username"],
            password=generate_password_hash(row["password"]),
            role=row["role"],
        )
        session.add(user)
        next_id += 1

    session.commit()
    session.close()

# 编号生成函数
def generate_tray_batch_number(kiln_id):
    """生成托批次编号"""
    from datetime import datetime
    now = datetime.now()
    date_str = now.strftime('%Y%m%d')
    session = Session()

    # 查找当天该窑的最后一个批次号
    existing = session.query(TrayBatch).filter(
        TrayBatch.batch_number.like(f'{kiln_id}{date_str}%')
    ).order_by(TrayBatch.batch_number.desc()).first()

    if existing:
        # 提取序号并加1
        seq = int(existing.batch_number[-3:]) + 1
    else:
        seq = 1

    batch_number = f"{kiln_id}{date_str}{seq:04d}"
    session.close()
    return batch_number

def generate_product_batch_number():
    """生成成品批次编号"""
    from datetime import datetime
    now = datetime.now()
    date_str = now.strftime('%Y%m%d')
    session = Session()

    # 查找当天最后一个成品批次号
    existing = session.query(ProductBatch).filter(
        ProductBatch.batch_number.like(f'CP{date_str}%')
    ).order_by(ProductBatch.batch_number.desc()).first()

    if existing:
        seq = int(existing.batch_number[-3:]) + 1
    else:
        seq = 1

    batch_number = f"CP{date_str}{seq:03d}"
    session.close()
    return batch_number

# 初始化数据库
create_default_user()
