# ========================================
# Python Backend for Knowledge Retention System
# Flask + MySQL
# ========================================

import os
import mysql.connector
from mysql.connector import Error
from flask import Flask, request, jsonify
from flask_cors import CORS
import bcrypt
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# ========================================
# MYSQL CONNECTION
# ========================================
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '12345'),
            database=os.getenv('DB_NAME', 'knowledge_retention_db')
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# ========================================
# HELPER FUNCTIONS
# ========================================

def generate_token(user_id):
    payload = {
        'userId': user_id,
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    token = jwt.encode(payload, os.getenv('JWT_SECRET', 'your_secret_key'), algorithm='HS256')
    return token

def verify_token(token):
    try:
        payload = jwt.decode(token, os.getenv('JWT_SECRET', 'your_secret_key'), algorithms=['HS256'])
        return payload['userId']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def calculate_next_review(review_count):
    intervals = [1, 3, 7, 14, 30]  # days
    interval = intervals[min(review_count, len(intervals) - 1)]
    next_date = datetime.now() + timedelta(days=interval)
    return next_date

def update_retention_stats(user_id, topic):
    connection = get_db_connection()
    if not connection:
        return

    try:
        cursor = connection.cursor(dictionary=True)

        # Get all takeaways for this user and topic
        cursor.execute(
            "SELECT * FROM takeaways WHERE userId = %s AND topic = %s",
            (user_id, topic)
        )
        takeaways = cursor.fetchall()

        if not takeaways:
            cursor.execute("DELETE FROM retention_stats WHERE userId = %s AND topic = %s", (user_id, topic))
            connection.commit()
            return

        total_takeaways = len(takeaways)
        remembered_count = sum(t['successCount'] for t in takeaways)
        total_reviews = sum(t['reviewCount'] for t in takeaways)
        retention_percentage = round((remembered_count / total_reviews) * 100, 2) if total_reviews > 0 else 0

        # Insert or update retention stats
        cursor.execute("""
            INSERT INTO retention_stats (userId, topic, totalTakeaways, rememberedCount, totalReviews, retentionPercentage, lastUpdated)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
            totalTakeaways = VALUES(totalTakeaways),
            rememberedCount = VALUES(rememberedCount),
            totalReviews = VALUES(totalReviews),
            retentionPercentage = VALUES(retentionPercentage),
            lastUpdated = NOW()
        """, (user_id, topic, total_takeaways, remembered_count, total_reviews, retention_percentage))

        connection.commit()

    except Error as e:
        print(f"Error updating retention stats: {e}")
    finally:
        cursor.close()
        connection.close()

# ========================================
# MIDDLEWARE
# ========================================

def token_required(f):
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No token provided'}), 401

        if not token.startswith('Bearer '):
            return jsonify({'error': 'Invalid token format'}), 401

        token = token.split(' ')[1]
        user_id = verify_token(token)

        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401

        request.user_id = user_id
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# ========================================
# AUTHENTICATION ROUTES
# ========================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({'error': 'Missing required fields'}), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor()

        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({'error': 'Email already registered'}), 400

        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Insert new user
        cursor.execute(
            "INSERT INTO users (name, email, password, dailyGoal, createdAt) VALUES (%s, %s, %s, %s, NOW())",
            (name, email, hashed_password.decode('utf-8'), 10)
        )

        user_id = cursor.lastrowid
        token = generate_token(user_id)

        connection.commit()

        return jsonify({
            'message': 'User registered successfully',
            'token': token,
            'user': {
                'id': user_id,
                'name': name,
                'email': email
            }
        }), 201

    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            return jsonify({'error': 'Invalid credentials'}), 401

        token = generate_token(user['id'])

        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email']
            }
        })

    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/auth/forgot', methods=['POST'])
@app.route('/forgot', methods=['POST'])  # legacy support
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    new_password = data.get('new_password')

    if not email or not new_password:
        return jsonify({'error': 'Email and new password are required'}), 400

    if len(new_password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cursor.execute(
            "UPDATE users SET password = %s, updatedAt = NOW() WHERE id = %s",
            (hashed_password, user['id'])
        )
        connection.commit()

        return jsonify({'message': 'Password reset successfully'})

    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

# ========================================
# TAKEAWAY CRUD ROUTES
# ========================================

@app.route('/api/takeaways', methods=['GET'])
@token_required
def get_takeaways():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM takeaways WHERE userId = %s ORDER BY nextReview ASC",
            (request.user_id,)
        )
        takeaways = cursor.fetchall()

        return jsonify(takeaways)

    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/takeaways/due', methods=['GET'])
@token_required
def get_due_takeaways():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM takeaways WHERE userId = %s AND nextReview <= NOW() ORDER BY nextReview ASC",
            (request.user_id,)
        )
        due_takeaways = cursor.fetchall()

        return jsonify(due_takeaways)

    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/takeaways/<int:takeaway_id>', methods=['GET'])
@token_required
def get_takeaway(takeaway_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM takeaways WHERE id = %s AND userId = %s",
            (takeaway_id, request.user_id)
        )
        takeaway = cursor.fetchone()

        if not takeaway:
            return jsonify({'error': 'Takeaway not found'}), 404

        return jsonify(takeaway)

    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/takeaways', methods=['POST'])
@token_required
def create_takeaway():
    data = request.get_json()
    text = data.get('text')
    topic = data.get('topic')
    source = data.get('source')

    if not text or not topic:
        return jsonify({'error': 'Text and topic required'}), 400

    next_review = datetime.now() + timedelta(days=1)

    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            INSERT INTO takeaways (userId, text, topic, source, intervalDays, nextReview, successCount, failureCount, reviewCount, createdAt)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (request.user_id, text, topic, source, 1, next_review, 0, 0, 0))

        takeaway_id = cursor.lastrowid
        update_retention_stats(request.user_id, topic)

        cursor.execute("SELECT * FROM takeaways WHERE id = %s", (takeaway_id,))
        new_takeaway = cursor.fetchone()

        connection.commit()

        return jsonify(new_takeaway), 201

    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/takeaways/<int:takeaway_id>', methods=['PUT'])
@token_required
def update_takeaway(takeaway_id):
    data = request.get_json()
    text = data.get('text')
    topic = data.get('topic')
    source = data.get('source')

    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        # Get old takeaway to check if topic changed
        cursor.execute("SELECT topic FROM takeaways WHERE id = %s AND userId = %s", (takeaway_id, request.user_id))
        old_takeaway = cursor.fetchone()

        if not old_takeaway:
            return jsonify({'error': 'Takeaway not found'}), 404

        cursor.execute(
            "UPDATE takeaways SET text = %s, topic = %s, source = %s, updatedAt = NOW() WHERE id = %s AND userId = %s",
            (text, topic, source, takeaway_id, request.user_id)
        )

        if cursor.rowcount == 0:
            return jsonify({'error': 'Takeaway not found'}), 404

        # Update retention stats for both old and new topics if topic changed
        if old_takeaway['topic'] != topic:
            update_retention_stats(request.user_id, old_takeaway['topic'])
        update_retention_stats(request.user_id, topic)

        cursor.execute("SELECT * FROM takeaways WHERE id = %s", (takeaway_id,))
        updated_takeaway = cursor.fetchone()

        connection.commit()

        return jsonify(updated_takeaway)

    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/takeaways/<int:takeaway_id>', methods=['DELETE'])
@token_required
def delete_takeaway(takeaway_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        # Get takeaway topic before deletion
        cursor.execute("SELECT topic FROM takeaways WHERE id = %s AND userId = %s", (takeaway_id, request.user_id))
        takeaway = cursor.fetchone()

        if not takeaway:
            return jsonify({'error': 'Takeaway not found'}), 404

        cursor.execute("DELETE FROM takeaways WHERE id = %s AND userId = %s", (takeaway_id, request.user_id))

        if cursor.rowcount == 0:
            return jsonify({'error': 'Takeaway not found'}), 404

        update_retention_stats(request.user_id, takeaway['topic'])

        connection.commit()

        return jsonify({'message': 'Takeaway deleted'})

    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

# ========================================
# REVIEW ROUTES
# ========================================

@app.route('/api/takeaways/<int:takeaway_id>/review', methods=['POST'])
@token_required
def review_takeaway(takeaway_id):
    data = request.get_json()
    remembered = data.get('remembered')

    if remembered is None:
        return jsonify({'error': 'Remembered field required'}), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        # Get current takeaway
        cursor.execute("SELECT * FROM takeaways WHERE id = %s AND userId = %s", (takeaway_id, request.user_id))
        takeaway = cursor.fetchone()

        if not takeaway:
            return jsonify({'error': 'Takeaway not found'}), 404

        # Update counts
        new_review_count = takeaway['reviewCount'] + 1
        new_success_count = takeaway['successCount'] + 1 if remembered else takeaway['successCount']
        new_failure_count = takeaway['failureCount'] if remembered else takeaway['failureCount'] + 1

        # Calculate next review
        next_review = calculate_next_review(new_review_count)
        interval_days = (next_review - datetime.now()).days

        # Update takeaway
        cursor.execute("""
            UPDATE takeaways SET
            successCount = %s, failureCount = %s, reviewCount = %s,
            nextReview = %s, intervalDays = %s, lastReviewedAt = NOW(), updatedAt = NOW()
            WHERE id = %s AND userId = %s
        """, (new_success_count, new_failure_count, new_review_count, next_review, interval_days, takeaway_id, request.user_id))

        # Insert review history
        cursor.execute(
            "INSERT INTO review_history (takeawayId, userId, remembered, reviewedAt) VALUES (%s, %s, %s, NOW())",
            (takeaway_id, request.user_id, remembered)
        )

        # Update retention stats
        update_retention_stats(request.user_id, takeaway['topic'])

        # Get updated takeaway
        cursor.execute("SELECT * FROM takeaways WHERE id = %s", (takeaway_id,))
        updated_takeaway = cursor.fetchone()

        connection.commit()

        return jsonify({
            'message': 'Review recorded',
            'takeaway': updated_takeaway
        })

    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

# ========================================
# RETENTION STATS ROUTES
# ========================================

@app.route('/api/retention/score', methods=['GET'])
@token_required
def get_retention_score():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT * FROM takeaways WHERE userId = %s", (request.user_id,))
        takeaways = cursor.fetchall()

        total_remembered = sum(t['successCount'] for t in takeaways)
        total_reviews = sum(t['reviewCount'] for t in takeaways)
        overall_percentage = round((total_remembered / total_reviews) * 100, 2) if total_reviews > 0 else 0

        return jsonify({
            'totalTakeaways': len(takeaways),
            'totalRemembered': total_remembered,
            'totalReviews': total_reviews,
            'overallPercentage': overall_percentage
        })

    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/retention/by-topic', methods=['GET'])
@token_required
def get_retention_by_topic():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM retention_stats WHERE userId = %s ORDER BY retentionPercentage DESC",
            (request.user_id,)
        )
        stats = cursor.fetchall()

        return jsonify(stats)

    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

# ========================================
# SEARCH ROUTES
# ========================================

@app.route('/api/search', methods=['GET'])
@token_required
def search_takeaways():
    query = request.args.get('q')

    if not query:
        return jsonify({'error': 'Search query required'}), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM takeaways WHERE userId = %s AND (text LIKE %s OR topic LIKE %s OR source LIKE %s)",
            (request.user_id, f'%{query}%', f'%{query}%', f'%{query}%')
        )
        takeaways = cursor.fetchall()

        return jsonify(takeaways)

    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

# ========================================
# ANALYTICS ROUTES
# ========================================

@app.route('/api/analytics/history', methods=['GET'])
@token_required
def get_review_history():
    limit = request.args.get('limit', 50, type=int)

    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT rh.*, t.text, t.topic
            FROM review_history rh
            JOIN takeaways t ON rh.takeawayId = t.id
            WHERE rh.userId = %s
            ORDER BY rh.reviewedAt DESC
            LIMIT %s
        """, (request.user_id, limit))

        history = cursor.fetchall()

        return jsonify(history)

    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/analytics/stats', methods=['GET'])
@token_required
def get_analytics_stats():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        # Get total takeaways
        cursor.execute("SELECT COUNT(*) as count FROM takeaways WHERE userId = %s", (request.user_id,))
        total_takeaways = cursor.fetchone()['count']

        # Get total reviews
        cursor.execute("SELECT COUNT(*) as count FROM review_history WHERE userId = %s", (request.user_id,))
        total_reviews = cursor.fetchone()['count']

        # Get unique topics
        cursor.execute("SELECT COUNT(DISTINCT topic) as count FROM takeaways WHERE userId = %s", (request.user_id,))
        topics = cursor.fetchone()['count']

        # Get average success rate
        cursor.execute(
            "SELECT AVG(remembered) * 100 as rate FROM review_history WHERE userId = %s",
            (request.user_id,)
        )
        result = cursor.fetchone()
        average_success_rate = round(result['rate'], 2) if result['rate'] else 0

        stats = {
            'totalTakeaways': total_takeaways,
            'totalReviews': total_reviews,
            'topics': topics,
            'averageSuccessRate': average_success_rate
        }

        return jsonify(stats)

    except Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

# ========================================
# START SERVER
# ========================================
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print("🚀 Starting Python Flask Backend...")
    print(f"📊 Connecting to MySQL database: knowledge_retention_db")
    print(f"🔑 MySQL Password: {os.getenv('DB_PASSWORD', '12345')}")
    print(f"🌐 Server will run on http://localhost:{port}")
    print("\n📚 API Endpoints:")
    print("   POST   /api/auth/register")
    print("   POST   /api/auth/login")
    print("   POST   /forgot")
    print("   GET    /api/takeaways")
    print("   POST   /api/takeaways")
    print("   GET    /api/takeaways/:id")
    print("   PUT    /api/takeaways/:id")
    print("   DELETE /api/takeaways/:id")
    print("   POST   /api/takeaways/:id/review")
    print("   GET    /api/retention/score")
    print("   GET    /api/retention/by-topic")
    print("   GET    /api/search?q=keyword")
    print("   GET    /api/analytics/history")
    print("   GET    /api/analytics/stats")

    app.run(debug=True, host='0.0.0.0', port=port)