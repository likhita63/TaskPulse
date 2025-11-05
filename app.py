from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from flask import request, jsonify
from flask_socketio import SocketIO, emit
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
socketio = SocketIO(app, cors_allowed_origins="*")

# ---------------- DATABASE CONFIGURATION -----------------
db_config = {
    'host': 'localhost',
    'database': 'demo2',
    'user': 'postgres',
    'password': 'likhita1'
}
def get_db_connection():
    conn = psycopg2.connect(**db_config)
    return conn

def get_db_connection():
    return psycopg2.connect(**db_config)

def create_users_table():
    conn = get_db_connection()
    cur = conn.cursor()
   # cur.execute("DROP TABLE IF EXISTS tasks;")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


print("✅ Table 'tasks' recreated successfully with status column.")


def create_tasks_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            assigned_to VARCHAR(255),
            task_type VARCHAR(50),
            duration VARCHAR(50),
            status VARCHAR(20) DEFAULT 'todo'
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


create_users_table()
create_tasks_table()

# ---------------- AUTH ROUTES -----------------
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('home_page'))
    return redirect(url_for('login'))

@app.route('/index')
def index_page():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed_pw = generate_password_hash(password)

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                        (name, email, hashed_pw))
            conn.commit()
            flash("✅ Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            conn.rollback()
            flash("⚠️ Email already exists.", "danger")
        finally:
            cur.close()
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, password FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            flash("🎉 Login successful!", "success")
            return redirect(url_for('home_page'))
        else:
            flash("❌ Invalid email or password.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("👋 You have been logged out.", "info")
    return redirect(url_for('login'))

# ---------------- MAIN PAGES -----------------
@app.route('/home')
def home_page():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))
    return render_template('home.html', name=session['user_name'])

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))
    user = {
        'name': 'Ram',
        'bio': 'MCA Student',
        'email': 'ram@example.com',
        'phone': '+91 9876543210',
        'branch': 'Computer Applications',
        'project_name': 'NotifyNet Dashboard System',
        'project_status': 'In Progress',
        'project_goal': 'Create a smart college communication platform',
        'next_project': 'AI-powered Attendance Tracker'
    }
    return render_template('profile.html', user=user)

@app.route('/update_profile')
def update_profile():
    return "<h3>Update Profile Page (Coming Soon)</h3>"

# ---------------- PROJECT HEAD -----------------
@app.route('/project_head', methods=['GET', 'POST'])
def project_head():
    # --- Require login ---
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    # --- Project Head access gate ---
    if 'project_head_authenticated' not in session:
        session['project_head_authenticated'] = False

    error = None
    if not session['project_head_authenticated']:
        if request.method == 'POST' and 'password' in request.form:
            password = request.form['password']
            if password == '123':  # Project Head password
                session['project_head_authenticated'] = True
                flash("✅ Access granted! Welcome Project Head.", "success")
                return redirect(url_for('project_head'))
            else:
                error = "❌ Incorrect password"
        return render_template('password.html', error=error)

    # --- Database connection ---
    conn = get_db_connection()
    cur = conn.cursor()

    # --- Handle Task Form Submission ---
    if request.method == 'POST' and 'title' in request.form:
        task_id = request.form.get('task_id')
        title = request.form['title']
        assigned_to = request.form['assigned_to']
        task_type = request.form['task_type']
        duration = request.form['duration']
        status = request.form['status']  # <-- new field

        if task_id:  # Update existing task
            cur.execute("""
                UPDATE tasks
                SET title=%s, assigned_to=%s, task_type=%s, duration=%s, status=%s
                WHERE id=%s
            """, (title, assigned_to, task_type, duration, status, task_id))
            flash("✏️ Task updated successfully!", "success")
        else:  # Add new task
            cur.execute("""
                INSERT INTO tasks (title, assigned_to, task_type, duration, status)
                VALUES (%s,%s,%s,%s,%s)
            """, (title, assigned_to, task_type, duration, status))
            flash("✅ Task created successfully!", "success")
        conn.commit()

    # --- Fetch all tasks ---
    cur.execute("SELECT * FROM tasks ORDER BY id DESC")
    tasks = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('project_head.html', tasks=tasks)


@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id=%s", (task_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("🗑 Task deleted successfully!", "success")
    return redirect(url_for('project_head'))



# ---------------- FRONTEND / BACKEND / DATABASE -----------------
@app.route('/frontend')
def frontend():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, assigned_to, duration FROM tasks WHERE task_type='frontend'")
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('frontend.html', tasks=tasks)

@app.route('/backend')
def backend():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, assigned_to, duration FROM tasks WHERE task_type='backend'")
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('backend.html', tasks=tasks)

@app.route('/database')
def database():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    # Fetch only database tasks
    cur.execute("SELECT id, title, assigned_to, duration FROM tasks WHERE task_type='database'")
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('database.html', tasks=tasks)

# ---------------- KANBAN BOARD -----------------

@app.route('/kanban_board')
def kanban_board():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks ORDER BY id DESC")
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('kanban_board.html', tasks=tasks)

@app.route('/update_task_status', methods=['POST'])
def update_task_status():
    data = request.get_json()
    task_id = data.get('id')
    new_status = data.get('status')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET status = %s WHERE id = %s", (new_status, task_id))
    conn.commit()
    cur.close()
    conn.close()

    # Notify all connected clients about the update
    socketio.emit('task_updated', {'id': task_id, 'status': new_status})

    return jsonify({'success': True})



@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    # --- Task Counts ---
    cur.execute("SELECT COUNT(*) FROM tasks;")
    total_tasks = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tasks WHERE status = 'inprogress';")
    in_progress = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Completed';")
    Completed = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users;")
    team_members = cur.fetchone()[0]

    cur.close()
    conn.close()
    print("DEBUG:", total_tasks, in_progress, Completed)

    return render_template(
        'dashboard.html',
        name=session.get('user_name', 'User'),
        total_tasks=total_tasks,
        in_progress=in_progress,
        completed=Completed,
        team_members=team_members
    )
@app.route('/skill_matrix')
def skill_matrix():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT member_name, skills FROM skill_matrix")
    skills = cur.fetchall()
    return render_template('skill_matrix.html', skills=skills)

@app.route('/add_skill', methods=['POST'])
def add_skill():
    skill = request.form['skill']
    level = request.form['level']
    conn = get_db_connection()

    cur = conn.cursor()
    cur.execute("INSERT INTO skill_matrix (user_id, skill_name, skill_level) VALUES (%s, %s, %s)",
                (session['user_id'], skill, level))
    conn.commit()
    return redirect(url_for('skill_matrix'))
@app.route('/smart_assignment')
def smart_assignment():
    task_title = request.args.get('task_title')
    task_type = request.args.get('task_type')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT member_name, skills FROM skill_matrix")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return jsonify({"recommended_member": "No members found in Skill Matrix"})

    members = [r[0] for r in rows]
    skills = [r[1] for r in rows]

    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform(skills + [task_title + " " + task_type])
    similarity = cosine_similarity(vectors[-1], vectors[:-1])

    best_match_index = np.argmax(similarity)
    recommended_member = members[best_match_index]

    return jsonify({"recommended_member": recommended_member})
@app.route('/ai_chat', methods=['POST'])
def ai_chat():
    data = request.get_json()
    user_message = data.get('message', '').lower()
    reply = "I'm your AI Project Assistant 🤖. You can ask me about your tasks, projects, dashboard, or deadlines."

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 🧠 Smart responses from DB
        if "pending" in user_message or "todo" in user_message:
            cursor.execute("SELECT title FROM tasks WHERE status ILIKE 'todo';")
            tasks = cursor.fetchall()
            if tasks:
                task_list = ", ".join([t['title'] for t in tasks])
                reply = f"You currently have {len(tasks)} pending task(s): {task_list}."
            else:
                reply = "Great job! You have no pending tasks. ✅"

        elif "progress" in user_message or "working" in user_message:
            cursor.execute("SELECT title FROM tasks WHERE status ILIKE 'inprogress';")
            tasks = cursor.fetchall()
            if tasks:
                task_list = ", ".join([t['title'] for t in tasks])
                reply = f"You have {len(tasks)} task(s) in progress: {task_list}."
            else:
                reply = "No tasks are currently in progress. 🚀"

        elif "completed" in user_message or "done" in user_message:
            cursor.execute("SELECT title FROM tasks WHERE status ILIKE 'completed';")
            tasks = cursor.fetchall()
            if tasks:
                task_list = ", ".join([t['title'] for t in tasks])
                reply = f"You’ve completed {len(tasks)} task(s): {task_list}. 🎉"
            else:
                reply = "No tasks marked completed yet. Keep going!"

        elif "deadline" in user_message or "due" in user_message:
            cursor.execute("""
                SELECT title, duration
                FROM tasks
                WHERE status ILIKE 'todo' OR status ILIKE 'inprogress'
                ORDER BY id DESC LIMIT 3;
            """)
            tasks = cursor.fetchall()
            if tasks:
                deadline_list = "\n".join([f"• {t['title']} → {t['duration']}" for t in tasks])
                reply = f"Here are your active tasks:\n{deadline_list}"
            else:
                reply = "No active tasks with deadlines. 🎯"

        # 👋 Friendly conversational responses
        elif any(word in user_message for word in ["hi", "hello", "hey"]):
            reply = "Hello 👋! I'm your AI Project Assistant. How can I help you today?"
        elif any(word in user_message for word in ["thank", "thanks"]):
            reply = "You're welcome 😊! Always here to assist."
        elif any(word in user_message for word in ["ok", "okay", "fine", "cool", "nice", "great", "good"]):
            reply = "👍 Glad to hear that! You can also ask me about your ongoing tasks or deadlines."
        elif "bye" in user_message:
            reply = "Goodbye 👋! Have a productive day ahead!"
        elif "help" in user_message:
            reply = "You can ask me:\n• Show pending tasks\n• Show in-progress tasks\n• Show completed tasks\n• What are my deadlines"

        cursor.close()
        conn.close()

    except Exception as e:
        print("❌ Database error:", e)
        reply = "I'm having trouble accessing your project data right now."

    return jsonify({"reply": reply})

# ---------------- RUN APP -----------------
if __name__ == '__main__':
    socketio.run(app, debug=True)
