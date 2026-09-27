import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'super_secret_college_key_2024'
DATABASE = 'database.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Create Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                student_id TEXT,
                course TEXT,
                year TEXT,
                contact TEXT
            )
        ''')
        
        # Create Events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                venue TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                rules TEXT,
                total_seats INTEGER NOT NULL,
                available_seats INTEGER NOT NULL,
                organizer TEXT NOT NULL
            )
        ''')
        
        # Create Registrations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (event_id) REFERENCES events (id),
                UNIQUE(user_id, event_id)
            )
        ''')
        
        # Insert sample admin and student if not exists
        cursor.execute("SELECT * FROM users WHERE email='admin@college.edu'")
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO users (name, email, password, role)
                VALUES (?, ?, ?, ?)
            ''', ('System Admin', 'admin@college.edu', generate_password_hash('admin123'), 'admin'))
            
        cursor.execute("SELECT * FROM users WHERE email='student@college.edu'")
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO users (name, email, password, role, student_id, course, year, contact)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', ('John Doe', 'student@college.edu', generate_password_hash('student123'), 'student', 'CS2024001', 'Computer Science', '3rd Year', '1234567890'))
            
        # Insert sample events
        cursor.execute("SELECT * FROM events")
        if not cursor.fetchone():
            sample_events = [
                ('Tech Symposium 2024', '2024-11-15', '10:00 AM', 'Main Auditorium', 'Technical', 'Annual technical symposium with coding challenges and hackathons. Great prizes to be won!', 'Bring your own laptops. ID card mandatory.', 200, 200, 'CS Department'),
                ('Cultural Fest - Fiesta', '2024-12-05', '04:00 PM', 'Open Air Theatre', 'Cultural', 'Dance, music, and art festival to celebrate diversity and creativity.', 'Open to all students. Registration required for stage performances.', 500, 500, 'Cultural Committee'),
                ('AI Workshop', '2024-10-25', '09:00 AM', 'Lab 3, CS Block', 'Workshop', 'Hands-on workshop on modern AI and Machine Learning techniques using Python.', 'Basic Python knowledge required. Install dependencies before arriving.', 50, 50, 'AI Club')
            ]
            cursor.executemany('''
                INSERT INTO events (name, date, time, venue, category, description, rules, total_seats, available_seats, organizer)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', sample_events)
            
        db.commit()

# --- ROUTES ---
@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        db = get_db()
        user = db.cursor().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['role'] = user['role']
            flash('Logged in successfully!', 'success')
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid email or password', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

# --- STUDENT ROUTES ---
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Unauthorized access!', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/dashboard')
@login_required
def student_dashboard():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
        
    db = get_db()
    cursor = db.cursor()
    
    upcoming_events_count = cursor.execute("SELECT COUNT(*) FROM events WHERE date >= date('now')").fetchone()[0]
    user_regs_count = cursor.execute("SELECT COUNT(*) FROM registrations WHERE user_id = ? AND status = 'Registered'", (session['user_id'],)).fetchone()[0]
    
    recent_regs = cursor.execute('''
        SELECT e.name, e.date, e.venue, r.reg_date, r.id, e.id as event_id
        FROM registrations r
        JOIN events e ON r.event_id = e.id
        WHERE r.user_id = ? AND r.status = 'Registered'
        ORDER BY r.reg_date DESC LIMIT 3
    ''', (session['user_id'],)).fetchall()
    
    return render_template('student_dashboard.html', 
                           upcoming_count=upcoming_events_count, 
                           regs_count=user_regs_count,
                           recent_regs=recent_regs)

@app.route('/events')
@login_required
def events():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
        
    db = get_db()
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    date_filter = request.args.get('date', '')
    
    query = "SELECT * FROM events WHERE 1=1"
    params = []
    
    if search:
        query += " AND (name LIKE ? OR description LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])
        
    if category:
        query += " AND category = ?"
        params.append(category)
        
    if date_filter:
        query += " AND date = ?"
        params.append(date_filter)
        
    query += " ORDER BY date ASC"
    
    all_events = db.cursor().execute(query, params).fetchall()
    categories = db.cursor().execute("SELECT DISTINCT category FROM events").fetchall()
    
    return render_template('events.html', events=all_events, categories=[c['category'] for c in categories], current_cat=category, search=search, current_date=date_filter)

@app.route('/event/<int:event_id>')
@login_required
def event_details(event_id):
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
        
    db = get_db()
    event = db.cursor().execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        flash('Event not found', 'error')
        return redirect(url_for('events'))
        
    reg = db.cursor().execute("SELECT * FROM registrations WHERE user_id = ? AND event_id = ? AND status = 'Registered'", (session['user_id'], event_id)).fetchone()
    is_registered = True if reg else False
    
    return render_template('event_details.html', event=event, is_registered=is_registered)

@app.route('/register/<int:event_id>', methods=['POST'])
@login_required
def register_event(event_id):
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
        
    db = get_db()
    cursor = db.cursor()
    
    event = cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        flash('Event not found', 'error')
        return redirect(url_for('events'))
        
    if event['available_seats'] <= 0:
        flash('Sorry, this event is full!', 'error')
        return redirect(url_for('event_details', event_id=event_id))
        
    existing = cursor.execute("SELECT * FROM registrations WHERE user_id = ? AND event_id = ?", (session['user_id'], event_id)).fetchone()
    
    if existing:
        if existing['status'] == 'Cancelled':
            cursor.execute("UPDATE registrations SET status = 'Registered', reg_date = CURRENT_TIMESTAMP WHERE id = ?", (existing['id'],))
        else:
            flash('You are already registered for this event.', 'info')
            return redirect(url_for('event_details', event_id=event_id))
    else:
        cursor.execute("INSERT INTO registrations (user_id, event_id, status) VALUES (?, ?, 'Registered')", (session['user_id'], event_id))
        
    cursor.execute("UPDATE events SET available_seats = available_seats - 1 WHERE id = ?", (event_id,))
    db.commit()
    
    flash(f"Successfully registered for {event['name']}!", 'success')
    return redirect(url_for('my_registrations'))

@app.route('/cancel_registration/<int:reg_id>', methods=['POST'])
@login_required
def cancel_registration(reg_id):
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
        
    db = get_db()
    cursor = db.cursor()
    
    reg = cursor.execute("SELECT * FROM registrations WHERE id = ? AND user_id = ?", (reg_id, session['user_id'])).fetchone()
    if reg and reg['status'] == 'Registered':
        cursor.execute("UPDATE registrations SET status = 'Cancelled' WHERE id = ?", (reg_id,))
        cursor.execute("UPDATE events SET available_seats = available_seats + 1 WHERE id = ?", (reg['event_id'],))
        db.commit()
        flash('Registration cancelled successfully.', 'success')
    else:
        flash('Invalid registration.', 'error')
        
    return redirect(url_for('my_registrations'))

@app.route('/my_registrations')
@login_required
def my_registrations():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
        
    db = get_db()
    regs = db.cursor().execute('''
        SELECT r.id, e.name, e.date, e.venue, r.status, e.id as event_id
        FROM registrations r
        JOIN events e ON r.event_id = e.id
        WHERE r.user_id = ?
        ORDER BY r.reg_date DESC
    ''', (session['user_id'],)).fetchall()
    
    return render_template('registrations.html', registrations=regs)

@app.route('/profile')
@login_required
def profile():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
        
    db = get_db()
    user = db.cursor().execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    return render_template('profile.html', user=user)

# --- ADMIN ROUTES ---
@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    cursor = db.cursor()
    
    total_events = cursor.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    upcoming_events = cursor.execute("SELECT COUNT(*) FROM events WHERE date >= date('now')").fetchone()[0]
    total_regs = cursor.execute("SELECT COUNT(*) FROM registrations WHERE status = 'Registered'").fetchone()[0]
    total_students = cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'student'").fetchone()[0]
    
    events = cursor.execute('''
        SELECT e.*, 
        (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id AND r.status = 'Registered') as reg_count
        FROM events e
        ORDER BY date DESC
    ''').fetchall()
    
    return render_template('admin_dashboard.html', 
                           stats={
                               'total_events': total_events,
                               'upcoming_events': upcoming_events,
                               'total_regs': total_regs,
                               'total_students': total_students
                           },
                           events=events)

@app.route('/admin/event/add', methods=['POST'])
@admin_required
def add_event():
    db = get_db()
    cursor = db.cursor()
    
    name = request.form['name']
    date = request.form['date']
    time = request.form['time']
    venue = request.form['venue']
    category = request.form['category']
    description = request.form['description']
    rules = request.form['rules']
    total_seats = int(request.form['total_seats'])
    organizer = request.form['organizer']
    
    cursor.execute('''
        INSERT INTO events (name, date, time, venue, category, description, rules, total_seats, available_seats, organizer)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, date, time, venue, category, description, rules, total_seats, total_seats, organizer))
    db.commit()
    
    flash('Event added successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/event/delete/<int:event_id>', methods=['POST'])
@admin_required
def delete_event(event_id):
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("DELETE FROM registrations WHERE event_id = ?", (event_id,))
    cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
    db.commit()
    
    flash('Event deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/event/edit/<int:event_id>', methods=['POST'])
@admin_required
def edit_event(event_id):
    db = get_db()
    cursor = db.cursor()
    
    name = request.form['name']
    date = request.form['date']
    time = request.form['time']
    venue = request.form['venue']
    category = request.form['category']
    description = request.form['description']
    rules = request.form['rules']
    total_seats = int(request.form['total_seats'])
    organizer = request.form['organizer']
    
    event = cursor.execute("SELECT total_seats, available_seats FROM events WHERE id = ?", (event_id,)).fetchone()
    if event:
        diff = total_seats - event['total_seats']
        new_available = event['available_seats'] + diff
        if new_available < 0:
            new_available = 0
            
        cursor.execute('''
            UPDATE events SET 
                name=?, date=?, time=?, venue=?, category=?, description=?, rules=?, total_seats=?, available_seats=?, organizer=?
            WHERE id=?
        ''', (name, date, time, venue, category, description, rules, total_seats, new_available, organizer, event_id))
        db.commit()
        flash('Event updated successfully.', 'success')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/registrations')
@admin_required
def admin_registrations():
    db = get_db()
    search = request.args.get('search', '')
    
    query = '''
        SELECT r.id, u.name as student_name, u.student_id, e.name as event_name, r.status, r.reg_date
        FROM registrations r
        JOIN users u ON r.user_id = u.id
        JOIN events e ON r.event_id = e.id
        WHERE 1=1
    '''
    params = []
    
    if search:
        query += " AND (u.name LIKE ? OR u.student_id LIKE ? OR e.name LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
        
    query += " ORDER BY r.reg_date DESC"
    
    regs = db.cursor().execute(query, params).fetchall()
    return render_template('admin_registrations.html', registrations=regs, search=search)

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        print("Initializing database...")
        init_db()
    app.run(debug=True, port=5000)
