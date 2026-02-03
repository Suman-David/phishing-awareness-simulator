from flask import Flask, render_template, request, redirect, url_for, send_file
from models import db, User, CampaignLog
from risk_engine import calculate_dynamic_risk
from datetime import datetime
from fpdf import FPDF
import io
import os

app = Flask(__name__)

# --- CONFIGURATION ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'phishsim.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'finalyearproject_secret_key'

db.init_app(app)

# --- ROUTES ---

@app.route('/')
def home():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    users = User.query.all()
    # Recalculate risk scores dynamically every time we view the dashboard
    for u in users:
        u.risk_score = calculate_dynamic_risk(u)
    db.session.commit()
    return render_template('dashboard.html', users=users)

@app.route('/reset/<int:user_id>')
def reset_user(user_id):
    # Delete all campaign logs for this user to reset their score
    CampaignLog.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    return redirect(url_for('dashboard'))

# --- FIXED PDF REPORT FUNCTION ---
@app.route('/download_report')
def download_report():
    # 1. Setup PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="PhishSim Security Audit Report", ln=1, align='C')
    pdf.ln(10)

    # 2. Table Header
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(60, 10, "Email", 1)
    pdf.cell(30, 10, "Dept", 1)
    pdf.cell(30, 10, "Risk Score", 1)
    pdf.cell(50, 10, "Last Device", 1)
    pdf.ln()

    # 3. Table Data
    pdf.set_font("Arial", size=10)
    users = User.query.all()
    for user in users:
        # Handle cases where history is empty
        last_device = user.history[-1].device_info if user.history else "N/A"
        # Shorten text if it's too long
        if len(last_device) > 25:
            last_device = last_device[:25] + '..'
        
        pdf.cell(60, 10, user.email, 1)
        pdf.cell(30, 10, user.department, 1)
        pdf.cell(30, 10, str(round(user.risk_score, 1)), 1)
        pdf.cell(50, 10, last_device, 1)
        pdf.ln()

    # 4. Save to Memory Buffer (Corrected for FPDF 1.7.2)
    # output(dest='S') returns the PDF as a string.
    # We encode it to 'latin-1' to handle binary data correctly.
    try:
        pdf_content = pdf.output(dest='S').encode('latin-1')
        pdf_buffer = io.BytesIO(pdf_content)
        pdf_buffer.seek(0)
        
        return send_file(
            pdf_buffer, 
            as_attachment=True, 
            download_name='Security_Report.pdf', 
            mimetype='application/pdf'
        )
    except Exception as e:
        return f"Error generating PDF: {str(e)}"

# --- ATTACK SIMULATION ROUTES ---

@app.route('/launch_attack/<int:user_id>')
def launch_attack(user_id):
    user = db.session.get(User, user_id)
    if not user: return "User not found", 404

    # Create a new log entry
    new_log = CampaignLog(user_id=user.id, campaign_name="Urgent Password Reset")
    db.session.add(new_log)
    db.session.commit()

    # Generate the tracking link
    tracking_link = url_for('phishing_link', log_id=new_log.id, _external=True)

    # Return a simulated email view
    return f"""
    <div style="font-family: Arial; text-align: center; margin-top: 50px; border: 1px solid #ccc; padding: 20px; width: 500px; margin: auto;">
        <h2>📧 Simulated Email</h2>
        <p><strong>To:</strong> {user.email}</p>
        <p><strong>From:</strong> security@goggle-support.com (Spoofed)</p>
        <p><strong>Subject:</strong> ⚠️ ACTION REQUIRED: Unauthorized Login Attempt</p>
        <hr>
        <p>We detected a login from Russia. If this wasn't you, click below:</p>
        <a href='{tracking_link}' style="background: #d9534f; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Secure My Account</a>
        <br><br>
        <small>(Internal Tracking ID: {new_log.id})</small>
    </div>
    """

@app.route('/track/<int:log_id>')
def phishing_link(log_id):
    # This acts as the "Listener"
    log = db.session.get(CampaignLog, log_id)
    if log and not log.clicked:
        log.clicked = True
        log.click_time = datetime.utcnow()
        
        # --- Device Fingerprinting (New) ---
        ua = request.headers.get('User-Agent', 'Unknown')
        if "Mobile" in ua: 
            log.device_info = "Mobile Device"
        elif "Windows" in ua: 
            log.device_info = "Windows PC"
        elif "Mac" in ua: 
            log.device_info = "Mac OS"
        else: 
            log.device_info = "Linux/Other"
        # -----------------------------------
        
        db.session.commit()
    
    # Redirect to the fake login page, passing the log_id so they can report it later
    return redirect(url_for('fake_login', log_id=log_id))

@app.route('/login/<int:log_id>', methods=['GET', 'POST'])
def fake_login(log_id):
    if request.method == 'POST':
        # If they submit the form (type password), they failed the test
        return redirect(url_for('education'))
    
    # Render the phishing page
    return render_template('phishing_page.html', log_id=log_id)

@app.route('/education')
def education():
    return render_template('education.html')

@app.route('/report_attack/<int:log_id>')
def report_attack(log_id):
    # If they click "Report", we mark it in the DB (Success)
    log = db.session.get(CampaignLog, log_id)
    if log:
        log.reported = True
        db.session.commit()
    return render_template('good_job.html')


# --- INITIALIZATION ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Check if users exist; if not, add them
        if not User.query.first():
            print("Seeding database with dummy users...")
            
            # List of users to add
            users = [
                User(email="alice@finance.com", department="Finance"),
                User(email="bob@it.com", department="IT"),
                User(email="carol@hr.com", department="HR"),
                User(email="david@sales.com", department="Sales"),       
                User(email="eve@marketing.com", department="Marketing"), 
                User(email="frank@company.com", department="Executive")  
            ]
            
            # Add all to session
            db.session.add_all(users)
            db.session.commit()
            print("Database initialized with 6 users!")
            
    app.run(debug=True)
