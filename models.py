from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import secrets

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(80), nullable=False)
    email          = db.Column(db.String(120), unique=True, nullable=False)
    password_hash  = db.Column(db.String(256), nullable=False)
    role           = db.Column(db.String(10), default='student')
    level          = db.Column(db.Integer, default=1)
    xp             = db.Column(db.Integer, default=0)
    total_xp       = db.Column(db.Integer, default=0)
    total_done     = db.Column(db.Integer, default=0)
    hard_done      = db.Column(db.Integer, default=0)
    streak         = db.Column(db.Integer, default=0)
    best_streak    = db.Column(db.Integer, default=0)
    last_active    = db.Column(db.Date, nullable=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    quests              = db.relationship('Quest', backref='user', lazy=True, cascade='all, delete-orphan')
    user_achievements   = db.relationship('UserAchievement', backref='user', lazy=True, cascade='all, delete-orphan')
    memberships         = db.relationship('ClassroomMember', backref='user', lazy=True, cascade='all, delete-orphan')
    created_assignments = db.relationship('Assignment', backref='creator', lazy=True, foreign_keys='Assignment.teacher_id')
    submissions         = db.relationship('Submission', backref='student', lazy=True, foreign_keys='Submission.student_id')
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)
    def is_teacher(self): return self.role == 'teacher'
    def __repr__(self): return f'<User {self.name} [{self.role}]>'


class Classroom(db.Model):
    __tablename__ = 'classrooms'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    subject     = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    code        = db.Column(db.String(8), unique=True, nullable=False)
    teacher_id  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    teacher     = db.relationship('User', foreign_keys=[teacher_id])
    members     = db.relationship('ClassroomMember', backref='classroom', lazy=True, cascade='all, delete-orphan')
    assignments = db.relationship('Assignment', backref='classroom', lazy=True, cascade='all, delete-orphan')
    @staticmethod
    def generate_code():
        while True:
            code = secrets.token_hex(4).upper()
            if not Classroom.query.filter_by(code=code).first():
                return code
    def get_student_count(self): return ClassroomMember.query.filter_by(classroom_id=self.id).count()
    def __repr__(self): return f'<Classroom {self.name}>'


class ClassroomMember(db.Model):
    __tablename__ = 'classroom_members'
    id           = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    joined_at    = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('classroom_id', 'user_id'),)


class Assignment(db.Model):
    __tablename__ = 'assignments'
    id           = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    teacher_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title        = db.Column(db.String(200), nullable=False)
    description  = db.Column(db.Text, nullable=True)
    subject      = db.Column(db.String(80), nullable=False)
    difficulty   = db.Column(db.String(10), nullable=False, default='easy')
    xp_reward    = db.Column(db.Integer, nullable=False, default=10)
    due_date     = db.Column(db.Date, nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    submissions  = db.relationship('Submission', backref='assignment', lazy=True, cascade='all, delete-orphan')
    def is_overdue(self):
        return bool(self.due_date and date.today() > self.due_date)
    def __repr__(self): return f'<Assignment {self.title}>'


class Submission(db.Model):
    __tablename__ = 'submissions'
    id            = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    student_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_path     = db.Column(db.String(500), nullable=True)
    original_name = db.Column(db.String(300), nullable=True)
    file_type     = db.Column(db.String(20), nullable=True)
    note          = db.Column(db.Text, nullable=True)
    status        = db.Column(db.String(10), default='submitted')
    xp_awarded    = db.Column(db.Boolean, default=False)
    submitted_at  = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at   = db.Column(db.DateTime, nullable=True)
    __table_args__ = (db.UniqueConstraint('assignment_id', 'student_id'),)
    def __repr__(self): return f'<Submission a={self.assignment_id} s={self.student_id}>'


class Quest(db.Model):
    __tablename__ = 'quests'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title       = db.Column(db.String(200), nullable=False)
    subject     = db.Column(db.String(80), nullable=False)
    difficulty  = db.Column(db.String(10), nullable=False)
    xp_reward   = db.Column(db.Integer, nullable=False)
    status      = db.Column(db.String(10), default='pending')
    date        = db.Column(db.Date, default=date.today)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    def __repr__(self): return f'<Quest {self.title} [{self.status}]>'


class Achievement(db.Model):
    __tablename__ = 'achievements'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    icon        = db.Column(db.String(10), default='🏆')
    xp_reward   = db.Column(db.Integer, default=0)
    condition   = db.Column(db.String(100))
    user_achievements = db.relationship('UserAchievement', backref='achievement', lazy=True)
    def __repr__(self): return f'<Achievement {self.name}>'


class UserAchievement(db.Model):
    __tablename__ = 'user_achievements'
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    achievement_id  = db.Column(db.Integer, db.ForeignKey('achievements.id'), nullable=False)
    earned_at       = db.Column(db.DateTime, default=datetime.utcnow)
    def __repr__(self): return f'<UserAchievement user={self.user_id} ach={self.achievement_id}>'
