from aiogram.fsm.state import State, StatesGroup

class OrderStates(StatesGroup):
    waiting_for_link = State()
    waiting_for_quantity = State()
    confirm_order = State()

class DepositStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_receipt = State()

class DownloaderStates(StatesGroup):
    waiting_for_username = State()

class AdminStates(StatesGroup):
    waiting_for_api_key = State()
    waiting_for_margin = State()
    waiting_for_card = State()
    waiting_for_user_id = State()
    waiting_for_balance_amount = State()
    waiting_for_broadcast_msg = State()
