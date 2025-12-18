#!/usr/bin/env python3
"""
Script per inizializzare il database e creare utenti di test
"""

from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def init_database():
    """Inizializza il database e crea utenti di test"""
    with app.app_context():
        # Crea tutte le tabelle
        db.create_all()
        print("Database inizializzato")
        
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin'),
                is_admin=True,
                email='admin@example.com'
            )
            db.session.add(admin)
            print("Utente admin creato (username: admin, password: admin)")
        else:
            print("ℹUtente admin già esistente")
        
        # Crea utente di test normale
        test_user = User.query.filter_by(username='user1').first()
        if not test_user:
            test_user = User(
                username='user1',
                password_hash=generate_password_hash('user1'),
                is_admin=False,
                email='user1@example.com'
            )
            db.session.add(test_user)
            print("Utente di test creato (username: user1, password: user1)")
        else:
            print("Utente di test già esistente")
        
        db.session.commit()
        print()
        print("=" * 50)
        print("Utenti disponibili:")
        print("  Admin: username='admin', password='admin'")
        print("  User:  username='user1', password='user1'")
        print("=" * 50)

if __name__ == '__main__':
    init_database()
