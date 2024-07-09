import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///lft.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Google Drive API settings
    GOOGLE_CLIENT_SECRET_FILE = 'client_secret.json'
    GOOGLE_API_SCOPES = ['https://www.googleapis.com/auth/drive.file']

    # Microsoft OneDrive API settings
    MSAL_CLIENT_ID = os.environ.get('MSAL_CLIENT_ID') or 'your-msal-client-id'
    MSAL_CLIENT_SECRET = os.environ.get('MSAL_CLIENT_SECRET') or 'your-msal-client-secret'
    MSAL_AUTHORITY = 'https://login.microsoftonline.com/common'

    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB limit for file uploads

    # Session settings
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True