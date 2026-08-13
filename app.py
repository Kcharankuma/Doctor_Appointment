import os
import sqlite3
import smtplib
import threading 
from email.mime.text import MIMEText
from flask import Flask, render_template, request, redirect, url_for, flash, session

# Fetch credentials from Environment Variables
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "charankumark816@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "dtnjsustgcsrehdf").replace(" ", "")
DOCTOR_EMAIL = os.environ.get("DOCTOR_EMAIL", "charankumark310@gmail.com")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "rmp_clinic_secure_key")

CLINIC_INFO = {
    "doctor_name": "Dr. KAMMARI MAHESWARA ACHARI",
    "qualification": "RMP (RURAL Medical Practitioner)",
    "clinic_name": "Primary Healthcare Center",
    "experience": "25+ Years of Dedicated Community Care",
    "phone": "+91 7075575715",
    "address": "Gorukallu Village, Near Bus Stand, Nandyal, Andhra Pradesh, India-518501",
    "timings": "Morning: 9:00 AM - 1:00 PM | Evening: 5:00 PM - 9:00 PM (Mon - Sat)"
}

# ==========================================
# DATABASE HELPER FUNCTIONS
# ==========================================
def get_db_connection():
    conn = sqlite3.connect('clinic.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            date TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Initialize DB on server start
init_db()

# ==========================================
# EMAIL NOTIFICATION (ASYNC THREAD)
# ==========================================
def send_email_notification(name, phone, date, time_slot, reason):
    try:
        subject = f"🏥 New Appointment: {name}"
        body = f"""
        New Patient Appointment Booked!

        Patient Name: {name}
        Phone Number: {phone}
        Date: {date}
        Session: {time_slot}
        Reason: {reason if reason else 'General Consultation'}
        """
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = DOCTOR_EMAIL

        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        server.ehlo()
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, DOCTOR_EMAIL, msg.as_string())
        server.close()
        print("Email notification sent successfully!")
    except Exception as e:
        print("Email notification failed:", e)

# ==========================================
# ROUTES
# ==========================================
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
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO appointments (name, phone, date, time_slot, reason, status)
            VALUES (?, ?, ?, ?, ?, 'Pending')
        ''', (name, phone, date, time_slot, reason))
        conn.commit()
        conn.close()

        # Send Email in background thread
        email_thread = threading.Thread(
            target=send_email_notification, 
            args=(name, phone, date, time_slot, reason)
        )
        email_thread.start()

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
@app.route('/login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == "Doctor" and password == "Charan@816":
            session['logged_in'] = True
            return redirect(url_for('doctor_dashboard'))
        else:
            flash("Invalid credentials! Please try again.", "danger")

    return render_template('login.html', info=CLINIC_INFO)

# Doctor Dashboard
@app.route('/dashboard')
def doctor_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('doctor_login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, phone, date, time_slot, reason, status FROM appointments ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()

    appointments = [
        {
            "id": row['id'], 
            "name": row['name'], 
            "phone": row['phone'], 
            "date": row['date'], 
            "time_slot": row['time_slot'], 
            "reason": row['reason'], 
            "status": row['status']
        }
        for row in rows
    ]
    return render_template('dashboard.html', info=CLINIC_INFO, appointments=appointments)

# Delete Appointment
@app.route('/appointment/delete/<int:app_id>')
def delete_appointment(app_id):
    if not session.get('logged_in'):
        return redirect(url_for('doctor_login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM appointments WHERE id = ?', (app_id,))
    conn.commit()
    conn.close()
    
    flash("Appointment marked as completed.", "success")
    return redirect(url_for('doctor_dashboard'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)