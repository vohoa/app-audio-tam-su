"""
Script to migrate main.py from API to Database
"""
import re

# Read the original file
with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace imports
content = content.replace(
    'from api_service import APIService',
    'from database_service import DatabaseService'
)

content = content.replace(
    'from login_dialog import LoginDialog',
    '# from login_dialog import LoginDialog  # Not needed with local database'
)

# Replace class references
content = re.sub(
    r'api_service:\s*APIService',
    'db_service: DatabaseService',
    content
)

content = re.sub(
    r'self\.api_service\s*=\s*APIService\(\)',
    'self.db_service = DatabaseService()',
    content
)

# Replace all api_service references to db_service
content = re.sub(
    r'\bself\.api_service\b',
    'self.db_service',
    content
)

content = re.sub(
    r'\bapi_service\s*=\s*self\.api_service',
    'db_service=self.db_service',
    content
)

content = re.sub(
    r'\bapi_service\b(?!=)',
    'db_service',
    content
)

# Comment out login dialog calls
content = re.sub(
    r'(\s+)# Show login dialog before loading data\s+self\.show_login_dialog\(\)',
    r'\1# Login not needed with local database\n\1# self.show_login_dialog()\n\1self.load_stories()  # Load stories immediately',
    content
)

content = re.sub(
    r'(\s+)def show_login_dialog\(self\):',
    r'\1def show_login_dialog(self):\n\1    """DEPRECATED: Not needed with local database"""\n\1    return  # No-op',
    content,
    count=1
)

content = re.sub(
    r'(\s+)logout_action = account_menu\.addAction\(\'🚪 Đăng Xuất\'\)\s+logout_action\.triggered\.connect\(self\.logout\)',
    r'\1# Logout not needed with local database\n\1# logout_action = account_menu.addAction(\'🚪 Đăng Xuất\')\n\1# logout_action.triggered.connect(self.logout)',
    content
)

# Write the modified content
with open('main_migrated.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Migration completed! Check main_migrated.py")
print("\nChanges made:")
print("1. Replaced APIService with DatabaseService")
print("2. Replaced api_service with db_service throughout")
print("3. Commented out login dialog")
print("4. Commented out logout action")
