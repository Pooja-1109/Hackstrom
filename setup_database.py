#!/usr/bin/env python3
"""
MySQL Database Setup Script
Connects to MySQL and runs the setup SQL
"""

import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_connection():
    """Test MySQL connection"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '12345')
        )

        if connection.is_connected():
            db_info = connection.get_server_info()
            print("✅ Connected to MySQL Server version", db_info)
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE();")
            record = cursor.fetchone()
            print("✅ Connected to database:", record)
            return connection

    except Error as e:
        print("❌ Error connecting to MySQL:", e)
        return None

def setup_database():
    """Setup the knowledge retention database"""
    connection = test_connection()
    if not connection:
        return False

    try:
        cursor = connection.cursor()

        # Create database if it doesn't exist
        cursor.execute("CREATE DATABASE IF NOT EXISTS knowledge_retention_db")
        print("✅ Database 'knowledge_retention_db' created or already exists")

        # Switch to the database
        cursor.execute("USE knowledge_retention_db")

        # Read and execute the SQL setup file
        with open('mysql-setup.sql', 'r', encoding='utf-8') as file:
            sql_script = file.read()

        # Execute the entire script at once
        try:
            # Execute multi-statement script
            for result in cursor.execute(sql_script, multi=True):
                if result:
                    print(f"✅ Executed statement, affected rows: {result.rowcount}")
            print("✅ Executed SQL script successfully")
        except Error as e:
            print(f"⚠️  Error executing script: {e}")
            # Try to execute statements one by one as fallback
            statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
            print(f"📝 Found {len(statements)} statements to execute")
            for i, statement in enumerate(statements[:10]):  # Show first 10
                print(f"   Statement {i+1}: {statement[:50]}...")
            for statement in statements:
                try:
                    cursor.execute(statement)
                    print("✅ Executed SQL statement")
                except Error as e:
                    print(f"⚠️  Skipped statement: {e}")

        connection.commit()
        print("✅ Database setup completed successfully!")

        # Verify tables were created
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print("📋 Created tables:")
        for table in tables:
            print(f"   - {table[0]}")

        return True

    except Error as e:
        print("❌ Error setting up database:", e)
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("✅ MySQL connection closed")

if __name__ == "__main__":
    print("🔧 Setting up MySQL database for Knowledge Retention System...")
    print(f"📊 Host: {os.getenv('DB_HOST', 'localhost')}")
    print(f"👤 User: {os.getenv('DB_USER', 'root')}")
    print(f"🔑 Password: {'*' * len(os.getenv('DB_PASSWORD', '12345'))}")

    success = setup_database()

    if success:
        print("\n🎉 Database setup complete! You can now run the Python backend:")
        print("   python backend-server.py")
    else:
        print("\n❌ Database setup failed. Please check your MySQL configuration.")