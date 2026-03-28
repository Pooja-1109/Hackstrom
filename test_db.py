#!/usr/bin/env python3
"""
Test script to check MySQL database contents
"""

import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

def check_database():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '12345'),
            database=os.getenv('DB_NAME', 'knowledge_retention_db')
        )

        cursor = connection.cursor(dictionary=True)

        # Check users
        cursor.execute("SELECT id, name, email FROM users")
        users = cursor.fetchall()
        print("👥 Users in database:")
        for user in users:
            print(f"   ID: {user['id']}, Name: {user['name']}, Email: {user['email']}")

        # Check takeaways
        cursor.execute("SELECT COUNT(*) as count FROM takeaways")
        result = cursor.fetchone()
        print(f"📚 Total takeaways: {result['count']}")

        # Check retention stats
        cursor.execute("SELECT COUNT(*) as count FROM retention_stats")
        result = cursor.fetchone()
        print(f"📊 Total retention stats: {result['count']}")

        # Check review history
        cursor.execute("SELECT COUNT(*) as count FROM review_history")
        result = cursor.fetchone()
        print(f"📈 Total review history: {result['count']}")

        # Check user stats
        cursor.execute("SELECT COUNT(*) as count FROM user_stats")
        result = cursor.fetchone()
        print(f"📊 Total user stats: {result['count']}")

    except Error as e:
        print(f"❌ Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    check_database()