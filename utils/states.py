from aiogram.fsm.state import State, StatesGroup

class CarouselFlow(StatesGroup):
    insta_auto_waiting_for_text = State()
    insta_auto_waiting_for_background = State()
    waiting_for_text_confirmation = State()
    cover_waiting_for_text = State()
    cover_choosing_text_mode = State()
    cover_choosing_style = State()
    cover_choosing_background = State()
    cover_waiting_for_background = State()
    cover_choosing_format = State()
    cover_processing = State()
    insta_cover_waiting_for_text = State()


class TestRenderFlow(StatesGroup):
    """Mini-FSM for the admin-only experimental-render entry point.

    Triggered by the main-menu button '🧪 Тестовый рендер' or the
    '/test_render' command. Stays in this state until the admin sends
    /start or a new top-level command.
    """

    waiting_for_text = State()
    waiting_for_background = State()
    waiting_for_rewrite = State()
    waiting_for_style = State()
