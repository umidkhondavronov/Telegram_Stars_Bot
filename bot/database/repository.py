from datetime import datetime, timezone
from decimal import Decimal
import secrets
import string
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.models import (
    DepositOrder, DepositStatus, ShopOrder, ShopOrderStatus, StarOrder,
    Transaction, TransactionType, User, Wallet, PremiumOrder,
)

async def get_or_create_user(session: AsyncSession, tg_user):
    user = await session.get(User, tg_user.id)
    if not user:
        user = User(id=tg_user.id, username=tg_user.username, first_name=tg_user.first_name)
        session.add(user)
        session.add(Wallet(user_id=tg_user.id, balance=Decimal("0.00")))
        await session.commit()
    else:
        user.username = tg_user.username
        user.first_name = tg_user.first_name
        await session.commit()
    return user

async def get_balance(session, user_id):
    wallet = await session.get(Wallet, user_id)
    return wallet.balance if wallet else Decimal("0.00")

async def change_balance(session, user_id, amount, transaction_type, description):
    wallet = await session.get(Wallet, user_id, with_for_update=True)
    if not wallet:
        raise ValueError("Hamyon topilmadi")
    if transaction_type == TransactionType.DEBIT:
        if wallet.balance < amount:
            raise ValueError("Insufficient balance")
        wallet.balance -= amount
    else:
        wallet.balance += amount
    session.add(Transaction(user_id=user_id, amount=amount, type=transaction_type.value, description=description))
    await session.commit()
    return wallet.balance

async def get_recent_transactions(session, user_id, limit=10):
    r = await session.execute(select(Transaction).where(Transaction.user_id == user_id).order_by(desc(Transaction.created_at)).limit(limit))
    return r.scalars().all()

async def get_recent_orders(session, user_id, limit=10):
    legacy = await session.execute(select(StarOrder).where(StarOrder.user_id == user_id).order_by(desc(StarOrder.created_at)).limit(limit))
    shop = await session.execute(select(ShopOrder).where(ShopOrder.user_id == user_id).order_by(desc(ShopOrder.created_at)).limit(limit))
    premium = await session.execute(select(PremiumOrder).where(PremiumOrder.user_id == user_id).order_by(desc(PremiumOrder.created_at)).limit(limit))
    rows = []
    for r in legacy.scalars().all():
        rows.append((r.created_at, f"⭐ {r.stars:,}", r.price, r.status, None))
    for r in shop.scalars().all():
        label = f"⭐ {r.stars:,}" if r.kind == "stars" else r.item_name
        rows.append((r.created_at, label, r.price, r.status, r.recipient_username))
    for r in premium.scalars().all():
        rows.append((r.created_at, f"💎 Premium {r.months} oy", r.price, r.status, r.recipient))
    rows.sort(key=lambda x: x[0], reverse=True)
    return rows[:limit]

async def create_order(session, user_id, stars, price):
    # Kept for compatibility with older code.
    return await create_shop_order(session, user_id, "stars", str(stars), f"⭐ {stars:,} Stars", stars, price, user_id, None)

async def create_shop_order(session, user_id, kind, item_key, item_name, stars, price, recipient_user_id, recipient_username):
    wallet = await session.get(Wallet, user_id, with_for_update=True)
    if not wallet or wallet.balance < price:
        raise ValueError("Insufficient balance")
    wallet.balance -= price
    order = ShopOrder(
        user_id=user_id,
        kind=kind,
        item_key=item_key,
        item_name=item_name,
        stars=stars,
        price=price,
        recipient_user_id=recipient_user_id,
        recipient_username=recipient_username,
        status=ShopOrderStatus.PENDING.value,
    )
    session.add(order)
    session.add(Transaction(
        user_id=user_id,
        amount=price,
        type=TransactionType.DEBIT.value,
        description=f"{item_name} buyurtmasi" + (f" → {recipient_username}" if recipient_username else " → o'zimga"),
    ))
    await session.commit()
    await session.refresh(order)
    return order, wallet.balance

async def complete_shop_order(session: AsyncSession, order_id: int):
    order = await session.get(ShopOrder, order_id, with_for_update=True)
    if not order:
        raise ValueError("Buyurtma topilmadi")
    if order.status != ShopOrderStatus.PENDING.value:
        raise ValueError("Bu buyurtma allaqachon ko'rib chiqilgan")
    order.status = ShopOrderStatus.COMPLETED.value
    order.completed_at = datetime.now(timezone.utc)
    await session.commit()
    return order

async def cancel_shop_order(session: AsyncSession, order_id: int):
    order = await session.get(ShopOrder, order_id, with_for_update=True)
    if not order:
        raise ValueError("Buyurtma topilmadi")
    if order.status != ShopOrderStatus.PENDING.value:
        raise ValueError("Bu buyurtma allaqachon ko'rib chiqilgan")
    wallet = await session.get(Wallet, order.user_id, with_for_update=True)
    if not wallet:
        raise ValueError("Hamyon topilmadi")
    wallet.balance += order.price
    order.status = ShopOrderStatus.CANCELLED.value
    order.completed_at = datetime.now(timezone.utc)
    session.add(Transaction(
        user_id=order.user_id,
        amount=order.price,
        type=TransactionType.CREDIT.value,
        description=f"Refund: order #{order.id}",
    ))
    await session.commit()
    return order, wallet.balance

def _new_deposit_code():
    alphabet = string.ascii_lowercase + string.digits
    return "dep_" + "".join(secrets.choice(alphabet) for _ in range(10))

async def create_deposit_order(session: AsyncSession, user_id: int, amount: Decimal):
    for _ in range(10):
        code = _new_deposit_code()
        exists = await session.scalar(select(DepositOrder.id).where(DepositOrder.code == code))
        if not exists:
            break
    else:
        raise RuntimeError("Could not create a unique order code")
    order = DepositOrder(user_id=user_id, amount=amount, code=code)
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order

async def attach_deposit_screenshot(session: AsyncSession, order_id: int, file_id: str):
    order = await session.get(DepositOrder, order_id, with_for_update=True)
    if not order or order.status != DepositStatus.PENDING.value:
        raise ValueError("Bu balans to'ldirish buyurtmasi endi kutilmayapti")
    order.screenshot_file_id = file_id
    await session.commit()
    return order

async def approve_deposit(session: AsyncSession, order_id: int):
    order = await session.get(DepositOrder, order_id, with_for_update=True)
    if not order:
        raise ValueError("Balans to'ldirish buyurtmasi topilmadi")
    if order.status != DepositStatus.PENDING.value:
        raise ValueError("Bu balans to'ldirish buyurtmasi allaqachon ko'rib chiqilgan")
    wallet = await session.get(Wallet, order.user_id, with_for_update=True)
    if not wallet:
        raise ValueError("Hamyon topilmadi")
    wallet.balance += order.amount
    order.status = DepositStatus.APPROVED.value
    order.reviewed_at = datetime.now(timezone.utc)
    session.add(Transaction(user_id=order.user_id, amount=order.amount, type=TransactionType.CREDIT.value, description=f"Balance top-up: {order.code}"))
    await session.commit()
    return order, wallet.balance

async def reject_deposit(session: AsyncSession, order_id: int):
    order = await session.get(DepositOrder, order_id, with_for_update=True)
    if not order:
        raise ValueError("Balans to'ldirish buyurtmasi topilmadi")
    if order.status != DepositStatus.PENDING.value:
        raise ValueError("Bu balans to'ldirish buyurtmasi allaqachon ko'rib chiqilgan")
    order.status = DepositStatus.REJECTED.value
    order.reviewed_at = datetime.now(timezone.utc)
    await session.commit()
    return order


async def get_setting(session: AsyncSession, key: str, default=None):
    from bot.database.models import BotSetting
    row = await session.get(BotSetting, key)
    return row.value if row else default

async def set_setting(session: AsyncSession, key: str, value: str):
    from bot.database.models import BotSetting
    row = await session.get(BotSetting, key)
    if row:
        row.value = str(value)
    else:
        session.add(BotSetting(key=key, value=str(value)))
    await session.commit()


async def complete_premium_order(session: AsyncSession, order_id: int):
    order = await session.get(PremiumOrder, order_id, with_for_update=True)
    if not order:
        raise ValueError("Premium buyurtmasi topilmadi")
    if order.status != "pending":
        raise ValueError("Bu Premium buyurtmasi allaqachon ko'rib chiqilgan")
    order.status = "completed"
    await session.commit()
    return order

async def cancel_premium_order(session: AsyncSession, order_id: int):
    order = await session.get(PremiumOrder, order_id, with_for_update=True)
    if not order:
        raise ValueError("Premium buyurtmasi topilmadi")
    if order.status != "pending":
        raise ValueError("Bu Premium buyurtmasi allaqachon ko'rib chiqilgan")
    wallet = await session.get(Wallet, order.user_id, with_for_update=True)
    if not wallet:
        raise ValueError("Hamyon topilmadi")
    wallet.balance += order.price
    order.status = "cancelled"
    session.add(Transaction(user_id=order.user_id, amount=order.price, type=TransactionType.CREDIT.value, description=f"Premium refund: order #{order.id}"))
    await session.commit()
    return order, wallet.balance
