import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///vm_portal.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ProxMox configurazione
    PROXMOX_HOST = os.getenv('PROXMOX_HOST', '192.168.56.15')
    PROXMOX_USER = os.getenv('PROXMOX_USER', 'root@pam')
    PROXMOX_PASSWORD = os.getenv('PROXMOX_PASSWORD', '')
    PROXMOX_VERIFY_SSL = os.getenv('PROXMOX_VERIFY_SSL', 'False').lower() == 'true'
