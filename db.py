import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file


def get_connection():

    try:

        conn = mysql.connector.connect(

            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE"),

            autocommit=False

        )

        return conn

    except Error as e:

        print("❌ DATABASE CONNECTION ERROR:", e)

        return None