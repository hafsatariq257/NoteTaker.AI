import os
import json
import requests
import whisper
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime
from functools import wraps

# .env loading
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'notetaker-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notetaker.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# -----------------------------------------
# CONFIG & MODELS LOADING
# -----------------------------------------
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'

print("Loading Whisper Model... Please wait.")
whisper_model = whisper.load_model("base") 
print("Whisper Loaded Successfully!")

# -----------------------------------------
# DATABASE MODELS
# -----------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    meetings = db.relationship('Meeting', backref='owner', lazy=True)

class Meeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), default='Untitled Session')
    transcript = db.Column(db.Text)
    summary = db.Column(db.Text)
    action_items = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# -----------------------------------------
# HELPERS
# -----------------------------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def generate_summary_and_actions(transcript):
    if not GROQ_API_KEY:
        print("CRITICAL: GROQ_API_KEY missing!")
        return None
    
    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}', 
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': 'llama3-8b-8192',
        'messages': [
            {
                'role': 'system', 
                'content': 'You are NoteTaker.ai. Return ONLY a valid JSON object. Keys: "title", "summary", and "action_items". No extra text.' 
            },
            {'role': 'user', 'content': f'Summarize this accurately: {transcript[:8000]}'} 
        ],
        'response_format': { "type": "json_object" }
    }
    
    try:
        # timeout=None handles long essays without crashing
        res = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=None)
        res.raise_for_status()
        
        raw_content = res.json()['choices'][0]['message']['content']
        return json.loads(raw_content)
        
    except Exception as e:
        print(f"AI ERROR LOG: {e}")
        words = transcript.split()
        fallback_title = " ".join(words[:5]) + "..." if len(words) > 5 else "NoteTaker Session"
        
        return {
            "title": fallback_title,
            "summary": "NoteTaker.ai is processing your content. The full transcript is saved below.",
            "action_items": ["Review transcript for details"]
        }

# -----------------------------------------
# ROUTES
# -----------------------------------------
@app.route('/')
def landing(): 
    # Directly rendering landing page as requested
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        flash("Invalid credentials.", "error")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        if User.query.filter_by(email=request.form.get('email')).first():
            flash("Email exists!", "error")
            return redirect(url_for('signup'))
        new_user = User(name=request.form.get('name'), email=request.form.get('email'), 
                        password=generate_password_hash(request.form.get('password')))
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = db.session.get(User, session['user_id'])
    meetings = Meeting.query.filter_by(user_id=user.id).order_by(Meeting.created_at.desc()).all()
    return render_template('dashboard.html', user=user, meetings=meetings)

@app.route('/meeting/<int:meeting_id>')
@login_required
def view_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    if meeting.user_id != session['user_id']:
        return "Access Denied", 403
    try:
        action_items = json.loads(meeting.action_items)
    except:
        action_items = []
    return render_template('meeting_details.html', meeting=meeting, action_items=action_items)

@app.route('/settings')
@login_required
def settings():
    user = db.session.get(User, session['user_id'])
    return render_template('settings.html', user=user)

@app.route('/new-meeting')
@login_required
def new_meeting():
    return render_template('new_meeting.html')

@app.route('/upload-audio', methods=['POST'])
@login_required
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({'success': False, 'error': 'No file'})
    
    audio_file = request.files['audio']
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_file.filename)
    audio_file.save(file_path)

    try:
        result = whisper_model.transcribe(file_path)
        os.remove(file_path)
        return jsonify({'success': True, 'transcript': result['text']})
    except Exception as e:
        if os.path.exists(file_path): os.remove(file_path)
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete-meeting/<int:meeting_id>', methods=['POST'])
@login_required
def delete_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    if meeting.user_id == session['user_id']:
        db.session.delete(meeting)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Unauthorized'}), 403

@app.route('/process-live', methods=['POST'])
@login_required
def process_live():
    data = request.get_json()
    transcript = data.get('transcript', '').strip()
    if not transcript:
        return jsonify({'success': False, 'error': 'Empty transcript'})

    ai_result = generate_summary_and_actions(transcript)
    
    new_m = Meeting(
        user_id=session['user_id'],
        title=ai_result.get('title', 'Quick Session'),
        transcript=transcript,
        summary=ai_result.get('summary', 'Summary currently unavailable.'),
        action_items=json.dumps(ai_result.get('action_items', []))
    )
    db.session.add(new_m)
    db.session.commit()
    return jsonify({'success': True, 'meeting_id': new_m.id})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)