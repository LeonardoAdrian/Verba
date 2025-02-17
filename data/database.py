import psycopg2
from contextlib import contextmanager
dbname = 'ventas'
user = 'postgres'
password = 'admin'
host = 'localhost'  # o la dirección IP de tu servidor PostgreSQL
port = '5432'
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