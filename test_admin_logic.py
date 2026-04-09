import unittest
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))

import utils.database

class TestAdminPanel(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_bot_database.db"
        # Patch the DB_NAME in the module
        self.patcher = patch('utils.database.DB_NAME', self.test_db)
        self.patcher.start()
        
        # Initialize the test DB
        utils.database.init_db()
        self.test_user_id = 123456789

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_add_remove_user(self):
        # Ensure user is not allowed initially
        # We need to import the functions AFTER patching or access them through the module if they use the global variable
        # The functions in utils.database use DB_NAME global, so patching it on the module should work.
        
        from utils.database import add_allowed_user, remove_allowed_user, is_user_allowed, get_all_allowed_users

        self.assertFalse(is_user_allowed(self.test_user_id))

        # Add user
        self.assertTrue(add_allowed_user(self.test_user_id))
        self.assertTrue(is_user_allowed(self.test_user_id))
        
        # Check if in list
        users = get_all_allowed_users()
        self.assertIn(self.test_user_id, users)

        # Remove user
        self.assertTrue(remove_allowed_user(self.test_user_id))
        self.assertFalse(is_user_allowed(self.test_user_id))
        
        # Check if not in list
        users = get_all_allowed_users()
        self.assertNotIn(self.test_user_id, users)

if __name__ == '__main__':
    unittest.main()
