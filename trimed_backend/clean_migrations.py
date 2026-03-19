#!/usr/bin/env python
"""
Nettoyer la table django_migrations
"""
import psycopg2

config = {
    'host': 'localhost',
    'port': '5432',
    'database': 'Trimedh_BD',
    'user': 'admin_Trimedh',
    'password': 'root'
}

try:
    conn = psycopg2.connect(**config)
    conn.autocommit = True
    cursor = conn.cursor()
    
    print("[INFO] Nettoyage de la table django_migrations...")
    
    # Supprimer toutes les migrations
    cursor.execute("DELETE FROM django_migrations;")
    
    print("[OK] Table django_migrations nettoyée")
    
    cursor.close()
    conn.close()
    
    print("\n[NEXT] Exécutez maintenant:")
    print("  python manage.py migrate --fake")
    
except Exception as e:
    print(f"[ERROR] {e}")
