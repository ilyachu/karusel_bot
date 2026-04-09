from aiogram.fsm.state import State, StatesGroup

class CarouselFlow(StatesGroup):
    insta_auto_waiting_for_text = State()
    waiting_for_text_confirmation = State()
    choosing_slide_count = State()
    choosing_rewrite_style = State() # New: Exact, Marketing, etc.
    preview_text = State()           # New: Approve/Edit
    editing_text = State()           # New: User inputs manual edit
    choosing_visual_method = State() # New: Gen vs Preset
    choosing_gen_style = State()     # New: Existing styles or Custom
    entering_custom_prompt = State() # New: User inputs prompt
    choosing_preset = State()        # New: Pick preset image
    choosing_font = State()          # New: Select font style
    waiting_for_custom_background = State()  # New: Waiting for user to upload custom backgrounds
    waiting_for_cover_image = State()        # New: Waiting for custom cover upload
    confirming_custom_backgrounds = State()  # New: Confirming uploaded backgrounds
    choosing_text_position = State() # New: Top, Center, Bottom
    choosing_text_position = State() # New: Top, Center, Bottom
    processing = State()

    # Fast Mode States
    fast_mode_waiting_for_text = State()
    fast_mode_choosing_slide_count = State()
    fast_mode_choosing_rewrite_style = State() # New
    fast_mode_preview_text = State()           # New
    fast_mode_choosing_visual = State()
    fast_mode_waiting_for_custom_bg = State()  # New: dedicated state for custom bg upload
    fast_mode_waiting_for_cover = State()
    fast_mode_choosing_font = State()
