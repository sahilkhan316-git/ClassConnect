from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from flask_bcrypt import Bcrypt

app = Flask(__name__, static_folder='static')
CORS(app)
bcrypt = Bcrypt(app)
DB_PATH = 'database.sqlite'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Ensure static and templates directories exist
if not os.path.exists('static'):
    os.makedirs('static')

# Serve Static Files (Frontend UI)
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# --- API ENDPOINTS ---

@app.route('/api/teachers/register', methods=['POST'])
def register_teacher():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    subject = data.get('subject', '')
    
    if not all([name, email, password]):
        return jsonify({"error": "Name, email, and password are required"}), 400
        
    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO teachers (name, email, password_hash, subject) VALUES (?, ?, ?, ?)",
            (name, email, password_hash, subject)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 409
    finally:
        conn.close()
        
    return jsonify({"message": "Teacher registered successfully"}), 201

@app.route('/api/teachers/login', methods=['POST'])
def login_teacher():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not all([email, password]):
        return jsonify({"error": "Email and password are required"}), 400
        
    conn = get_db_connection()
    teacher = conn.execute("SELECT * FROM teachers WHERE email = ?", (email,)).fetchone()
    conn.close()
    
    if teacher and bcrypt.check_password_hash(teacher['password_hash'], password):
        # In a real app, use JWT. For simplicity here, we'll return the teacher ID.
        return jsonify({
            "message": "Login successful",
            "teacherId": teacher['id'],
            "name": teacher['name']
        }), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/teachers/<int:teacher_id>', methods=['PUT', 'GET'])
def teacher_profile(teacher_id):
    conn = get_db_connection()
    
    if request.method == 'GET':
        teacher = conn.execute(
            "SELECT id, name, email, location, resume_url, demo_lecture_url, subject FROM teachers WHERE id = ?",
            (teacher_id,)
        ).fetchone()
        conn.close()
        
        if teacher:
            return jsonify(dict(teacher)), 200
        return jsonify({"error": "Teacher not found"}), 404
        
    elif request.method == 'PUT':
        data = request.json
        location = data.get('location')
        resume_url = data.get('resume_url')
        demo_lecture_url = data.get('demo_lecture_url')
        subject = data.get('subject')
        
        conn.execute(
            """
            UPDATE teachers 
            SET location = COALESCE(?, location),
                resume_url = COALESCE(?, resume_url),
                demo_lecture_url = COALESCE(?, demo_lecture_url),
                subject = COALESCE(?, subject)
            WHERE id = ?
            """,
            (location, resume_url, demo_lecture_url, subject, teacher_id)
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "Profile updated successfully"}), 200

@app.route('/api/teachers/<int:teacher_id>/rate', methods=['POST'])
def rate_teacher(teacher_id):
    data = request.json
    rating = data.get('rating')
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({"error": "Rating must be an integer between 1 and 5"}), 400
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE teachers SET rating_sum = rating_sum + ?, rating_count = rating_count + 1 WHERE id = ?",
        (rating, teacher_id)
    )
    if c.rowcount == 0:
        conn.close()
        return jsonify({"error": "Teacher not found"}), 404
        
    conn.commit()
    conn.close()
    return jsonify({"message": "Rating submitted successfully"}), 200

@app.route('/api/students/register', methods=['POST'])
def register_student():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    
    if not all([name, email, password]):
        return jsonify({"error": "Name, email, and password are required"}), 400
        
    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO students (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 409
    finally:
        conn.close()
        
    return jsonify({"message": "Student registered successfully"}), 201

@app.route('/api/students/login', methods=['POST'])
def login_student():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not all([email, password]):
        return jsonify({"error": "Email and password are required"}), 400
        
    conn = get_db_connection()
    student = conn.execute("SELECT * FROM students WHERE email = ?", (email,)).fetchone()
    conn.close()
    
    if student and bcrypt.check_password_hash(student['password_hash'], password):
        return jsonify({
            "message": "Login successful",
            "studentId": student['id'],
            "name": student['name']
        }), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/messages', methods=['POST'])
def send_message():
    data = request.json
    sender_type = data.get('sender_type')
    sender_id = data.get('sender_id')
    receiver_type = data.get('receiver_type')
    receiver_id = data.get('receiver_id')
    content = data.get('content')
    
    if not all([sender_type, sender_id, receiver_type, receiver_id, content]):
        return jsonify({"error": "All fields are required"}), 400
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (sender_type, sender_id, receiver_type, receiver_id, content) VALUES (?, ?, ?, ?, ?)",
        (sender_type, sender_id, receiver_type, receiver_id, content)
    )
    message_id = c.lastrowid
    conn.commit()
    
    new_message = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    conn.close()
    
    return jsonify(dict(new_message)), 201

@app.route('/api/messages', methods=['GET'])
def get_messages():
    user1_type = request.args.get('user1_type')
    user1_id = request.args.get('user1_id')
    user2_type = request.args.get('user2_type')
    user2_id = request.args.get('user2_id')
    
    if not all([user1_type, user1_id, user2_type, user2_id]):
        return jsonify({"error": "Missing parameters"}), 400
        
    conn = get_db_connection()
    messages = conn.execute("""
        SELECT * FROM messages 
        WHERE (sender_type = ? AND sender_id = ? AND receiver_type = ? AND receiver_id = ?)
           OR (sender_type = ? AND sender_id = ? AND receiver_type = ? AND receiver_id = ?)
        ORDER BY timestamp ASC
    """, (user1_type, user1_id, user2_type, user2_id, user2_type, user2_id, user1_type, user1_id)).fetchall()
    conn.close()
    
    return jsonify([dict(m) for m in messages]), 200

@app.route('/api/chats/<user_type>/<int:user_id>', methods=['GET'])
def get_chats(user_type, user_id):
    conn = get_db_connection()
    if user_type == 'teacher':
        partners = conn.execute("""
            SELECT DISTINCT s.id, s.name 
            FROM students s
            JOIN messages m ON (m.sender_type = 'student' AND m.sender_id = s.id AND m.receiver_type = 'teacher' AND m.receiver_id = ?)
                           OR (m.receiver_type = 'student' AND m.receiver_id = s.id AND m.sender_type = 'teacher' AND m.sender_id = ?)
        """, (user_id, user_id)).fetchall()
    elif user_type == 'student':
        partners = conn.execute("""
            SELECT DISTINCT t.id, t.name 
            FROM teachers t
            JOIN messages m ON (m.sender_type = 'teacher' AND m.sender_id = t.id AND m.receiver_type = 'student' AND m.receiver_id = ?)
                           OR (m.receiver_type = 'teacher' AND m.receiver_id = t.id AND m.sender_type = 'student' AND m.sender_id = ?)
        """, (user_id, user_id)).fetchall()
    else:
        conn.close()
        return jsonify({"error": "Invalid user_type"}), 400
        
    conn.close()
    return jsonify([dict(p) for p in partners]), 200

@app.route('/api/teachers', methods=['GET'])
def search_teachers():
    query = request.args.get('q', '').lower()
    location = request.args.get('location', '').lower()
    subject = request.args.get('subject', '').lower()
    
    conn = get_db_connection()
    c = conn.cursor()
    
    sql = """
        SELECT id, name, email, location, resume_url, demo_lecture_url, subject, 
               rating_sum, rating_count,
               CASE WHEN rating_count > 0 THEN CAST(rating_sum AS REAL) / rating_count ELSE 0 END as avg_rating
        FROM teachers WHERE 1=1
    """
    params = []
    
    if query:
        sql += " AND (LOWER(name) LIKE ? OR LOWER(subject) LIKE ?)"
        params.extend([f"%{query}%", f"%{query}%"])
    if location:
        sql += " AND LOWER(location) LIKE ?"
        params.append(f"%{location}%")
    if subject:
        sql += " AND LOWER(subject) LIKE ?"
        params.append(f"%{subject}%")
        
    sql += " ORDER BY avg_rating DESC, id ASC"
        
    teachers = c.execute(sql, params).fetchall()
    conn.close()
    
    return jsonify([dict(t) for t in teachers]), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
