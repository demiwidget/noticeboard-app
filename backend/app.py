from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# Database configuration
db_path = os.path.join(os.path.dirname(__file__), 'noticeboard.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='Medium') # High, Medium, Low
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'priority': self.priority,
            'created_at': self.created_at.isoformat()
        }

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    assignee = db.Column(db.String(50), nullable=False)
    due_time = db.Column(db.String(50))
    priority = db.Column(db.String(20), default='Medium')
    status = db.Column(db.String(20), default='Pending')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'assignee': self.assignee,
            'due_time': self.due_time,
            'priority': self.priority,
            'status': self.status
        }

# Routes
@app.route('/api/notices', methods=['GET'])
def get_notices():
    notices = Notice.query.order_by(Notice.created_at.desc()).all()
    return jsonify([n.to_dict() for n in notices])

@app.route('/api/notices', methods=['POST'])
def add_notice():
    data = request.json
    new_notice = Notice(
        title=data['title'],
        content=data['content'],
        priority=data.get('priority', 'Medium')
    )
    db.session.add(new_notice)
    db.session.commit()
    return jsonify(new_notice.to_dict()), 201

@app.route('/api/notices/<int:id>', methods=['DELETE'])
def delete_notice(id):
    notice = Notice.query.get_or_404(id)
    db.session.delete(notice)
    db.session.commit()
    return '', 204

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    tasks = Task.query.all()
    return jsonify([t.to_dict() for t in tasks])

@app.route('/api/tasks', methods=['POST'])
def add_task():
    data = request.json
    new_task = Task(
        title=data['title'],
        assignee=data['assignee'],
        due_time=data.get('due_time'),
        priority=data.get('priority', 'Medium')
    )
    db.session.add(new_task)
    db.session.commit()
    return jsonify(new_task.to_dict()), 201

@app.route('/api/tasks/<int:id>', methods=['DELETE'])
def delete_task(id):
    task = Task.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    return '', 204

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    host = os.environ.get('NOTICEBOARD_HOST', '0.0.0.0')
    port = int(os.environ.get('NOTICEBOARD_PORT', '5000'))
    debug = os.environ.get('FLASK_DEBUG', '').lower() in {'1', 'true', 'yes'}
    app.run(host=host, port=port, debug=debug, use_reloader=False)
