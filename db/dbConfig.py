import mysql.connector
from mysql.connector import Error

def get_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",      
            password="",      
            database="fliqzworld" 
        )
        if connection.is_connected():
            print("Connection Established!!", connection)
        return connection
    except Error as e:
        print("DB connection error:", e)
        return None
