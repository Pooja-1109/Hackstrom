import mysql.connector
import bcrypt

conn = mysql.connector.connect(host='localhost', user='root', password='12345', database='knowledge_retention_db')
cur = conn.cursor()
cur.execute("SELECT password FROM users WHERE email='john@example.com'")
row = cur.fetchone()
print('hash', row)
print('check', bcrypt.checkpw(b'password', row[0].encode('utf-8')))
conn.close()