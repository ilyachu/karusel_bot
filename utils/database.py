import sqlite3
import logging
import os

DB_NAME = "bot_database.db"

def init_db():
    """Initialize the database and create tables if they don't exist."""
    if not os.path.exists(DB_NAME):
        # Create file if not exists
        open(DB_NAME, 'a').close()
        
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Create users table
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                logo_text TEXT DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS allowed_users (
                user_id INTEGER PRIMARY KEY,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        conn.commit()
        conn.close()
        logging.info("Database initialized successfully.")
    except Exception as e:
        logging.error(f"Error initializing database: {e}")

def set_user_logo(user_id: int, logo_text: str):
    """Set or update the custom logo for a user."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO users (user_id, logo_text)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET logo_text = excluded.logo_text
        ''', (user_id, logo_text))
        
        conn.commit()
        conn.close()
        logging.info(f"Logo updated for user {user_id}: {logo_text}")
        return True
    except Exception as e:
        logging.error(f"Error setting logo for user {user_id}: {e}")
        return False

def get_user_logo(user_id: int) -> str:
    """Get the custom logo for a user, or return default."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT logo_text FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        logo = result[0] if result and result[0] else "chu ai"
        logging.info(f"Retrieved logo for user {user_id}: {logo}")
        return logo
    except Exception as e:
        logging.error(f"Error getting logo for user {user_id}: {e}")
        return "chu ai"

def reset_user_logo(user_id: int):
    """Reset user's logo to default (NULL)."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE users SET logo_text = NULL WHERE user_id = ?', (user_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error resetting user logo: {e}")
        return False

def add_allowed_user(user_id: int):
    """Add a user to the allowed list."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('INSERT OR IGNORE INTO allowed_users (user_id) VALUES (?)', (user_id,))
        
        conn.commit()
        conn.close()
        logging.info(f"User {user_id} added to allowed list.")
        return True
    except Exception as e:
        logging.error(f"Error adding allowed user {user_id}: {e}")
        return False

def remove_allowed_user(user_id: int):
    """Remove a user from the allowed list."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM allowed_users WHERE user_id = ?', (user_id,))
        
        conn.commit()
        conn.close()
        logging.info(f"User {user_id} removed from allowed list.")
        return True
    except Exception as e:
        logging.error(f"Error removing allowed user {user_id}: {e}")
        return False

def is_user_allowed(user_id: int) -> bool:
    """Check if a user is in the allowed list."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT 1 FROM allowed_users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        conn.close()
        return result is not None
    except Exception as e:
        logging.error(f"Error checking if user {user_id} is allowed: {e}")
        return False

def get_all_allowed_users():
    """Get all allowed users."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id FROM allowed_users')
        users = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return users
    except Exception as e:
        logging.error(f"Error getting allowed users: {e}")
        return []
