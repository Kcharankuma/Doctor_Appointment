import os
import re
import sqlite3
import requests
from datetime import datetime, date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)

# SECURITY: Secret key for session management (Change this to a random string)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "clinic_production_secret_key_998877")

# ADMIN SECURITY: Password to access the doctor dashboard
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "doctor123")  # Change 'doctor123' to your desired password

# ==========================================
# 1. CLINIC DETAILS (Customize as needed)
# ==========================================
CLINIC_INFO = {
    "doctor_name": "Dr. [Father's Name]",
    "qualification": "RMP (Registered Medical Practitioner)",
    "clinic_name": "Primary Health Clinic",
    "experience": "15+ Years of Dedicated Healthcare",
    "phone": "+91 98765 43210",
    "address": "Main Road, Near Bus Stand, Town Name",
    "timings": "Morning: 9:00 AM - 1:00 PM | Evening: 5:00 PM - 9:00 PM (Mon - Sat)"
}

# ==========================================
# 2. SMS SERVICE (Fast2SMS for India)
# ==========================================
FAST2SMS_API_KEY = os.environ.get("FAST2SMS_API_KEY", "YOUR_FAST2SMS_API_KEY_HERE")

def send_sms_notification(patient_phone, patient_name, date_str, time_slot):
    """Dispatches transactional SMS via Fast2SMS."""
    if FAST2SMS_API_KEY == "YOUR_FAST2SMS_API_KEY_HERE":
        print("⚠️ Fast2SMS API Key not configured. Skipping SMS dispatch.")
        return

    try:
        url = "https://www.fast2sms.com/dev/bulkV2"
        message = (
            f"Hello {patient_name}, your appointment at {CLINIC_INFO['clinic_name']} "
            f"is confirmed for {date_str} ({time_slot}). Address: {CLINIC_INFO['address']}."
        )
        
        payload = {
            "message": message,
            "language": "english",
            "route": "q",
            "numbers": patient_phone.strip()
        }
        headers = {
            'authorization': FAST2SMS_API_KEY,
            'Content-Type': "application/x-www-form-urlencoded"
        }
        response = requests.post(url, data=payload, headers=headers, timeout=5)
        print("📲 SMS Service Response:", response.text)
    except Exception as e:
        print(f"⚠️ SMS Error: {e}")

# ==========================================
# 3. DATABASE SETUP & INDEXING
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Create indexes for high-speed searches
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON appointments(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_phone ON appointments(phone)')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 4. AUTHENTICATION DECORATOR
# ==========================================
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# 5. ROUTES
# ==========================================

@app.route('/')
def home():
    return render_template('index.html', info=CLINIC_INFO)

@app.route('/services')
def services():
    services_list = [
        {"title": "General Health Consultation", "desc": "Diagnosis and treatment for seasonal illness, fever, cold, and viral infections."},
        {"title": "First Aid & Wound Care", "desc": "Immediate dressing, injury management, and minor surgical procedures."},
        {"title": "BP & Diabetes Checkup", "desc": "Routine screening and ongoing blood pressure/sugar management."},
        {"title": "Preventive Care Counseling", "desc": "Routine health advice and preventive checkups for family members."}
    ]
    return render_template('services.html', info=CLINIC_INFO, services=services_list)

@app.route('/appointment', methods=['GET', 'POST'])
def book_appointment():
    if request.method == 'POST':
        patient_name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        date_str = request.form.get('date', '').strip()
        time_slot = request.form.get('time_slot', '').strip()
        reason = request.form.get('reason', '').strip()

        # --- VALIDATION 1: Patient Name ---
        if not patient_name or len(patient_name) < 3 or not re.match(r"^[A-Za-z\s]+$", patient_name):
            return render_template('appointment.html', info=CLINIC_INFO, error_msg="Invalid Name! Please use letters only (min 3 characters).")

        # --- VALIDATION 2: Phone Number ---
        if not phone or not re.match(r"^[6-9]\d{9}$", phone):
            return render_template('appointment.html', info=CLINIC_INFO, error_msg="Invalid Phone Number! Enter a valid 10-digit Indian mobile number.")

        # --- VALIDATION 3: Date Check (No Past Dates) ---
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if selected_date < date.today():
                return render_template('appointment.html', info=CLINIC_INFO, error_msg="Invalid Date! You cannot book an appointment for a past date.")
        except ValueError:
            return render_template('appointment.html', info=CLINIC_INFO, error_msg="Please select a valid booking date.")

        # --- VALIDATION 4: Reason / Symptoms ---
        if not reason or len(reason) < 5 or not re.search(r"[a-zA-Z]{3,}", reason):
            return render_template('appointment.html', info=CLINIC_INFO, error_msg="Please enter a valid symptom/reason (min 5 characters).")

        # --- SAVE TO DATABASE ---
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO appointments (name, phone, date, time_slot, reason) VALUES (?, ?, ?, ?, ?)",
            (patient_name, phone, date_str, time_slot, reason)
        )
        conn.commit()
        conn.close()

        # --- TRIGGER SMS ---
        send_sms_notification(phone, patient_name, date_str, time_slot)

        appointment_record = {
            "name": patient_name,
            "phone": phone,
            "date": date_str,
            "time_slot": time_slot,
            "reason": reason
        }
        return render_template('success.html', info=CLINIC_INFO, data=appointment_record)

    return render_template('appointment.html', info=CLINIC_INFO)

# ==========================================
# 6. DOCTOR ADMIN DASHBOARD & SECURITY
# ==========================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = "Invalid Password. Please try again."
    return render_template('admin.html', login_mode=True, error=error, info=CLINIC_INFO)

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    search_query = request.args.get('search', '').strip()
    conn = get_db_connection()
    cursor = conn.cursor()

    if search_query:
        query = "SELECT * FROM appointments WHERE name LIKE ? OR phone LIKE ? ORDER BY date ASC, id DESC"
        bookings = cursor.execute(query, (f'%{search_query}%', f'%{search_query}%')).fetchall()
    else:
        query = "SELECT * FROM appointments ORDER BY date ASC, id DESC"
        bookings = cursor.execute(query).fetchall()

    conn.close()
    return render_template('admin.html', login_mode=False, bookings=bookings, search_query=search_query, info=CLINIC_INFO)

@app.route('/delete/<int:booking_id>', methods=['POST'])
@admin_required
def delete_appointment(booking_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
