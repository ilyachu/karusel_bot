# Input validation constants and helpers

MAX_TEXT_LENGTH = 10000
MAX_FILE_SIZE_MB = 10
MAX_VOICE_DURATION_SECONDS = 300  # 5 minutes

def validate_text_length(text: str) -> tuple[bool, str]:
    """
    Validate text length.
    Returns (is_valid, error_message)
    """
    if len(text) > MAX_TEXT_LENGTH:
        return False, f"⚠️ Текст слишком длинный! Максимум {MAX_TEXT_LENGTH} символов. У вас: {len(text)}"
    if len(text.strip()) == 0:
        return False, "⚠️ Текст не может быть пустым."
    return True, ""

def validate_file_size(file_size: int) -> tuple[bool, str]:
    """
    Validate file size in bytes.
    Returns (is_valid, error_message)
    """
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        return False, f"⚠️ Файл слишком большой! Максимум {MAX_FILE_SIZE_MB} МБ."
    return True, ""
