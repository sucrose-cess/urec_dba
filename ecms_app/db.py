import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",          # Your MySQL Workbench username
        password="NewStrongPassword123!",          # Your MySQL Workbench password
        database="ecms_db"
    )