from aiogram.fsm.state import State, StatesGroup

class CarouselFlow(StatesGroup):
    insta_auto_waiting_for_text = State()
    insta_auto_waiting_for_background = State()
    waiting_for_text_confirmation = State()
    cover_waiting_for_text = State()
    cover_choosing_style = State()
    cover_choosing_background = State()
    cover_waiting_for_background = State()
    cover_choosing_format = State()
    cover_processing = State()
    insta_cover_waiting_for_text = State()
