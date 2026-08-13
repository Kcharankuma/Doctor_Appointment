import os
import sqlite3
import smtplib
import threading 
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, url_for, flash, session

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
# GMAIL SMTP EMAIL NOTIFICATION (100% FREE)
# ==========================================
def send_email_notification(name, phone, patient_email, date, time_slot, reason):
    sender_email = os.environ.get("SENDER_EMAIL", "charankumark816@gmail.com").strip()
    sender_password = os.environ.get("SENDER_PASSWORD", "").strip()
    doctor_email = os.environ.get("DOCTOR_EMAIL", "charankumark816@gmail.com").strip()

    if not sender_password:
        print("❌ SENDER_PASSWORD missing in Environment Variables!")
        return

    # Build recipient list (Doctor + Patient)
    recipients = [doctor_email]
    if patient_email and patient_email != doctor_email:
        recipients.append(patient_email)

    try:
        msg = MIMEMultipart()
        msg['From'] = f"Primary Healthcare Center <{sender_email}>"
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = f"🏥 Appointment Confirmation: {name}"

        body = f"""Dear {name},

Your appointment has been booked successfully!

Booking Details:
- Date: {date}
- Session: {time_slot}
- Reason: {reason if reason else 'General Checkup'}
- Contact: {phone}

Thank you for choosing our clinic!

Dr. KAMMARI MAHESWARA ACHARI
Primary Healthcare Center, Gorukallu Village
        """
        msg.attach(MIMEText(body, 'plain'))

        # Connect to Gmail SMTP Server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipients, msg.as_string())
        server.quit()

        print(f"✅ Email sent successfully to: {recipients}")

    except Exception as e:
        print(f"⚠️ SMTP Email Error: {e}")

# ==========================================
# PUBLIC ROUTES
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
        patient_email = request.form.get('email')
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

        # Send Email in background thread (Doctor + Customer)
        email_thread = threading.Thread(
            target=send_email_notification, 
            args=(name, phone, patient_email, date, time_slot, reason)
        )
        email_thread.start()

        appointment_record = {
            "name": name,
            "phone": phone,
            "email": patient_email,
            "date": date,
            "time_slot": time_slot,
            "reason": reason
        }
        return render_template('success.html', info=CLINIC_INFO, data=appointment_record)

    return render_template('appointment.html', info=CLINIC_INFO)

# ==========================================
# DOCTOR ADMIN ROUTES
# ==========================================
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

@app.route('/admin/logout')
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)