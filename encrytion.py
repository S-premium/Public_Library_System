from cryptography.fernet import Fernet
from dotenv import load_dotenv
import os

load_dotenv()

key = os.getenv('EMAIL_ENCRYPTION_KEY')
email = input("Enter the plaintext email to encrypt: ")

enc = Fernet(key.encode()).encrypt(email.encode()).decode()
print("\nEncrypted value:")
print(enc)
print("\nRun this SQL:")
print(f"UPDATE users SET email_display = '{enc}' WHERE id = 66;")