import pymysql
import os

def get_external_connection():
    return pymysql.connect(
        host=os.getenv("EXT_MYSQL_HOST"),
        user=os.getenv("EXT_MYSQL_USER"),
        password=os.getenv("EXT_MYSQL_PASSWORD"),
        database=os.getenv("EXT_MYSQL_DB"),
        port=int(os.getenv("EXT_MYSQL_PORT", 3306)),
        cursorclass=pymysql.cursors.DictCursor
    )
