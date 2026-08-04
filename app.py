import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = "rmp_clinic_secure_key"

CLINIC_INFO = {
    "doctor_name": "Dr.KAMMARI MAHESWARA ACHARI",
    "qualification": "RMP (Registered Medical Practitioner)",
    "clinic_name": "Primary Healthcare Center",
    "experience": "25+ Years of Dedicated Community Care",
    "phone": "+91 7075575715",
    "address": "Gorukallu Village, Near Bus Stand, Nandyal Andhra Pradesh India-518501",
    "timings": "Morning: 9:00 AM - 12:30 PM | Evening: 5:00 PM - 9:00 PM (Mon - Sat)"
}

# Database Initialization
def init_db():
    conn = sqlite3.connect('clinic.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            date TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'Pending'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html', info=CLINIC_INFO)

@app.route('/services')
def services():
    services_list = [
        {"title": "General Health Consultation", "desc": "Diagnosis and treatment for common illnesses, fever, cold, and viral infections."},
        {"title": "First Aid & Emergency Care", "desc": "Immediate dressing, wound care, and minor injury management."},
        {"title": "Blood Pressure & Diabetes Monitoring", "desc": "Regular screening and routine checkups for chronic condition management."},
        {"title": "Basic Preventive Care", "desc": "General wellness advice, health counseling, and preventive health checks."}
    ]
    return render_template('services.html', info=CLINIC_INFO, services=services_list)

@app.route('/appointment', methods=['GET', 'POST'])
def book_appointment():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        date = request.form.get('date')
        time_slot = request.form.get('time_slot')
        reason = request.form.get('reason')

        # Save to SQLite Database
        conn = sqlite3.connect('clinic.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO appointments (name, phone, date, time_slot, reason)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, phone, date, time_slot, reason))
        conn.commit()
        conn.close()

        appointment_record = {
            "name": name,
            "phone": phone,
            "date": date,
            "time_slot": time_slot,
            "reason": reason
        }
        return render_template('success.html', info=CLINIC_INFO, data=appointment_record)

    return render_template('appointment.html', info=CLINIC_INFO)

# Doctor Login
# Doctor Login
@app.route('/login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # CHANGE YOUR CREDENTIALS HERE:
        if username == "Doctor" and password == "Charan@816":
            session['logged_in'] = True
            return redirect(url_for('doctor_dashboard'))
        else:
            flash("Invalid credentials! Please try again.", "danger")

    return render_template('login.html', info=CLINIC_INFO)

# Doctor Dashboard with Database Fetch
@app.route('/dashboard')
def doctor_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('doctor_login'))

    conn = sqlite3.connect('clinic.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, phone, date, time_slot, reason, status FROM appointments ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()

    appointments = [
        {"id": row[0], "name": row[1], "phone": row[2], "date": row[3], "time_slot": row[4], "reason": row[5], "status": row[6]}
        for row in rows
    ]
    return render_template('dashboard.html', info=CLINIC_INFO, appointments=appointments)

# Complete or Delete Appointment
@app.route('/appointment/delete/<int:app_id>')
def delete_appointment(app_id):
    if not session.get('logged_in'):
        return redirect(url_for('doctor_login'))

    conn = sqlite3.connect('clinic.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM appointments WHERE id = ?', (app_id,))
    conn.commit()
    conn.close()
    
    flash("Appointment marked as completed/removed.", "success")
    return redirect(url_for('doctor_dashboard'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)