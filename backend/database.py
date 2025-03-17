import sqlite3

def get_connection():
    return sqlite3.connect("f1_data_full_2025.db", check_same_thread=False)
