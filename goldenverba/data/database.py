import psycopg2
from contextlib import contextmanager
import os
dbname = os.getenv('DB_NAME') 
user = os.getenv('DB_USER')
password = os.getenv('DB_PASSWORD')
host = os.getenv('DB_HOST')
port = os.getenv('DB_PORT')
class DatabaseConnection:
    _instance = None
        
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance.config = {
                'dbname': dbname,
                'user': user,
                'password': password,
                'host':host,
            }
        return cls._instance
    
    @contextmanager
    def get_connection(self):
        conn = psycopg2.connect(**self.config)
        try:
            yield conn
        finally:
            conn.close()