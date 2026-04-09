import sqlite3
import logging
import os
from config import DATA_DIR

DB_FOLDER = DATA_DIR
DB_NAME = os.path.join(DB_FOLDER, "bot_database.db")

def init_db():
    """Initialize the database and create tables if they don't exist."""
    if not os.path.exists(DB_FOLDER):
        os.makedirs(DB_FOLDER)
        
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

            CREATE TABLE IF NOT EXISTS export_packages (
                export_id TEXT PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                export_dir TEXT NOT NULL,
                export_slug TEXT NOT NULL,
                theme TEXT DEFAULT NULL,
                render_mode TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS meta_publish_jobs (
                job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                export_id TEXT NOT NULL,
                status TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(export_id) REFERENCES export_packages(export_id)
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


def save_export_package(
    export_id: str,
    chat_id: int,
    export_dir: str,
    export_slug: str,
    theme: str | None,
    render_mode: str | None,
):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO export_packages (export_id, chat_id, export_dir, export_slug, theme, render_mode)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(export_id) DO UPDATE SET
                chat_id = excluded.chat_id,
                export_dir = excluded.export_dir,
                export_slug = excluded.export_slug,
                theme = excluded.theme,
                render_mode = excluded.render_mode
            ''',
            (export_id, chat_id, export_dir, export_slug, theme, render_mode),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error saving export package {export_id}: {e}")
        return False


def get_export_package(export_id: str) -> dict | None:
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT export_id, chat_id, export_dir, export_slug, theme, render_mode, created_at
            FROM export_packages
            WHERE export_id = ?
            ''',
            (export_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return {
            "export_id": row[0],
            "chat_id": row[1],
            "export_dir": row[2],
            "export_slug": row[3],
            "theme": row[4],
            "render_mode": row[5],
            "created_at": row[6],
        }
    except Exception as e:
        logging.error(f"Error reading export package {export_id}: {e}")
        return None


def create_meta_publish_job(export_id: str, status: str, plan_json: str) -> int | None:
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO meta_publish_jobs (export_id, status, plan_json)
            VALUES (?, ?, ?)
            ''',
            (export_id, status, plan_json),
        )
        job_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return job_id
    except Exception as e:
        logging.error(f"Error creating meta publish job for export {export_id}: {e}")
        return None
