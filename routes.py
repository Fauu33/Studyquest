import os, uuid
from datetime import date, datetime
from flask import (Blueprint, render_template, redirect, url_for,
                   request, flash, jsonify, current_app, send_from_directory, abort)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.models import (User, Quest, Achievement, UserAchievement,
                        Classroom, ClassroomMember, Assignment, Submission)
from app import logic

main = Blueprint('main', __name__)

SUBJECTS = [
    'Matematika', 'Bahasa Indonesia', 'Bahasa Inggris',
    'IPA', 'IPS', 'PKn', 'Agama', 'Seni Budaya',
    'Penjas', 'Informatika', 'Lainnya',
]

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def allowed_file(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    cfg = current_app.config['ALLOWED_EXTENSIONS']
    for ftype, exts in cfg.items():
        if ext in exts:
            return ftype
    return None

def save_upload(file):
    """Save uploaded file, return (stored_filename, original_name, file_type)."""
    original = secure_filename(file.filename)
    ftype = allowed_file(original)
    if not ftype:
        return None, None, None
    ext = original.rsplit('.', 1)[-1].lower()
    stored = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    file.save(os.path.join(upload_dir, stored))
    return stored, original, ftype


# ─── AUTH ─────────────────────────────────────────────────────────────────────

@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role     = request.form.get('role', 'student')
        if role not in ('teacher', 'student'):
            role = 'student'
        if not name or not email or not password:
            flash('Semua field wajib diisi!', 'error')
            return render_template('login.html', mode='register')
        if User.query.filter_by(email=email).first():
            flash('Email sudah terdaftar.', 'error')
            return render_template('login.html', mode='register')
        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        role_label = 'Guru' if role == 'teacher' else 'Murid'
        flash(f'Selamat datang, {name}! Akun {role_label} berhasil dibuat 🚀', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('login.html', mode='register')


@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user     = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('Email atau password salah.', 'error')
    return render_template('login.html', mode='login')


@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

@main.route('/')
@login_required
def dashboard():
    if current_user.is_teacher():
        # Teacher: show their classrooms
        classrooms = Classroom.query.filter_by(teacher_id=current_user.id).all()
        return render_template('dashboard_teacher.html', classrooms=classrooms)
    else:
        # Student: show personal quests + assignments
        today        = date.today()
        today_quests = Quest.query.filter_by(user_id=current_user.id, date=today).all()
        level_info   = logic.get_level_info(current_user.total_xp)
        # Get assignments from joined classrooms
        membership_ids = [m.classroom_id for m in current_user.memberships]
        assignments = []
        if membership_ids:
            assignments = Assignment.query.filter(
                Assignment.classroom_id.in_(membership_ids)
            ).order_by(Assignment.created_at.desc()).all()
        # Get student's submissions
        sub_map = {s.assignment_id: s for s in current_user.submissions}
        return render_template('dashboard.html',
                               quests=today_quests,
                               level_info=level_info,
                               today=today,
                               assignments=assignments,
                               sub_map=sub_map)


# ─── CLASSROOM ────────────────────────────────────────────────────────────────

@main.route('/classroom/create', methods=['GET', 'POST'])
@login_required
def create_classroom():
    if not current_user.is_teacher():
        flash('Hanya guru yang bisa membuat kelas!', 'error')
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        name    = request.form.get('name', '').strip()
        subject = request.form.get('subject', 'Lainnya')
        desc    = request.form.get('description', '').strip()
        if not name:
            flash('Nama kelas tidak boleh kosong!', 'error')
            return render_template('classroom_create.html', subjects=SUBJECTS)
        cls = Classroom(
            name=name, subject=subject, description=desc,
            code=Classroom.generate_code(), teacher_id=current_user.id
        )
        db.session.add(cls)
        db.session.commit()
        flash(f'Kelas "{name}" berhasil dibuat! Kode kelas: {cls.code} 🎉', 'success')
        return redirect(url_for('main.classroom_detail', cls_id=cls.id))
    return render_template('classroom_create.html', subjects=SUBJECTS)


@main.route('/classroom/join', methods=['GET', 'POST'])
@login_required
def join_classroom():
    if current_user.is_teacher():
        flash('Guru tidak bisa bergabung sebagai murid!', 'error')
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        cls  = Classroom.query.filter_by(code=code).first()
        if not cls:
            flash('Kode kelas tidak ditemukan!', 'error')
            return render_template('classroom_join.html')
        already = ClassroomMember.query.filter_by(
            classroom_id=cls.id, user_id=current_user.id).first()
        if already:
            flash('Kamu sudah bergabung di kelas ini!', 'error')
            return redirect(url_for('main.dashboard'))
        member = ClassroomMember(classroom_id=cls.id, user_id=current_user.id)
        db.session.add(member)
        db.session.commit()
        flash(f'Berhasil bergabung ke kelas "{cls.name}"! 🎓', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('classroom_join.html')


@main.route('/classroom/<int:cls_id>')
@login_required
def classroom_detail(cls_id):
    cls = Classroom.query.get_or_404(cls_id)
    # Access check
    if current_user.is_teacher():
        if cls.teacher_id != current_user.id:
            abort(403)
    else:
        member = ClassroomMember.query.filter_by(
            classroom_id=cls_id, user_id=current_user.id).first()
        if not member:
            abort(403)

    assignments = Assignment.query.filter_by(classroom_id=cls_id)\
        .order_by(Assignment.created_at.desc()).all()
    members = ClassroomMember.query.filter_by(classroom_id=cls_id).all()

    sub_map = {}
    if not current_user.is_teacher():
        subs = Submission.query.filter_by(student_id=current_user.id).all()
        sub_map = {s.assignment_id: s for s in subs}

    # For teacher: submission counts
    assign_sub_counts = {}
    if current_user.is_teacher():
        for a in assignments:
            assign_sub_counts[a.id] = Submission.query.filter_by(assignment_id=a.id).count()

    return render_template('classroom_detail.html',
                           cls=cls,
                           assignments=assignments,
                           members=members,
                           sub_map=sub_map,
                           assign_sub_counts=assign_sub_counts)


# ─── ASSIGNMENTS ──────────────────────────────────────────────────────────────

@main.route('/classroom/<int:cls_id>/assignment/add', methods=['GET', 'POST'])
@login_required
def add_assignment(cls_id):
    cls = Classroom.query.get_or_404(cls_id)
    if not current_user.is_teacher() or cls.teacher_id != current_user.id:
        abort(403)
    if request.method == 'POST':
        title      = request.form.get('title', '').strip()
        desc       = request.form.get('description', '').strip()
        subject    = request.form.get('subject', 'Lainnya')
        difficulty = request.form.get('difficulty', 'easy')
        due_str    = request.form.get('due_date', '').strip()
        if not title:
            flash('Judul tugas tidak boleh kosong!', 'error')
            return render_template('assignment_add.html', cls=cls, subjects=SUBJECTS)
        due_date = None
        if due_str:
            try:
                due_date = datetime.strptime(due_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        xp = logic.get_xp_reward(difficulty)
        a = Assignment(
            classroom_id=cls_id, teacher_id=current_user.id,
            title=title, description=desc, subject=subject,
            difficulty=difficulty, xp_reward=xp, due_date=due_date
        )
        db.session.add(a)
        db.session.commit()
        flash(f'Tugas "{title}" berhasil ditambahkan! 📝', 'success')
        return redirect(url_for('main.classroom_detail', cls_id=cls_id))
    return render_template('assignment_add.html', cls=cls, subjects=SUBJECTS)


@main.route('/assignment/<int:assign_id>')
@login_required
def assignment_detail(assign_id):
    a = Assignment.query.get_or_404(assign_id)
    cls = a.classroom
    if current_user.is_teacher():
        if cls.teacher_id != current_user.id:
            abort(403)
        submissions = Submission.query.filter_by(assignment_id=assign_id)\
            .order_by(Submission.submitted_at.desc()).all()
        return render_template('assignment_detail_teacher.html', a=a, cls=cls, submissions=submissions)
    else:
        member = ClassroomMember.query.filter_by(classroom_id=cls.id, user_id=current_user.id).first()
        if not member:
            abort(403)
        my_sub = Submission.query.filter_by(assignment_id=assign_id, student_id=current_user.id).first()
        return render_template('assignment_detail_student.html', a=a, cls=cls, my_sub=my_sub)


@main.route('/assignment/<int:assign_id>/submit', methods=['POST'])
@login_required
def submit_assignment(assign_id):
    if current_user.is_teacher():
        abort(403)
    a = Assignment.query.get_or_404(assign_id)
    cls = a.classroom
    member = ClassroomMember.query.filter_by(classroom_id=cls.id, user_id=current_user.id).first()
    if not member:
        abort(403)
    existing = Submission.query.filter_by(assignment_id=assign_id, student_id=current_user.id).first()
    if existing:
        flash('Kamu sudah mengumpulkan tugas ini!', 'error')
        return redirect(url_for('main.assignment_detail', assign_id=assign_id))

    file = request.files.get('submission_file')
    note = request.form.get('note', '').strip()

    if not file or file.filename == '':
        flash('Pilih file untuk dikumpulkan!', 'error')
        return redirect(url_for('main.assignment_detail', assign_id=assign_id))

    stored, original, ftype = save_upload(file)
    if not stored:
        flash('Tipe file tidak didukung! Gunakan gambar, video, atau dokumen.', 'error')
        return redirect(url_for('main.assignment_detail', assign_id=assign_id))

    sub = Submission(
        assignment_id=assign_id,
        student_id=current_user.id,
        file_path=stored,
        original_name=original,
        file_type=ftype,
        note=note,
        status='submitted'
    )
    db.session.add(sub)

    # Award XP immediately on submission
    logic.add_xp(current_user, a.xp_reward)
    sub.xp_awarded = True
    current_user.total_done += 1
    logic.update_streak(current_user)
    logic.check_achievements(current_user)

    db.session.commit()
    flash(f'Tugas berhasil dikumpulkan! +{a.xp_reward} XP 🎉', 'success')
    return redirect(url_for('main.assignment_detail', assign_id=assign_id))


@main.route('/submission/<int:sub_id>/review', methods=['POST'])
@login_required
def review_submission(sub_id):
    if not current_user.is_teacher():
        abort(403)
    sub = Submission.query.get_or_404(sub_id)
    if sub.assignment.classroom.teacher_id != current_user.id:
        abort(403)
    action = request.form.get('action')
    if action in ('approved', 'revision'):
        sub.status = action
        sub.reviewed_at = datetime.utcnow()
        db.session.commit()
        label = 'disetujui ✅' if action == 'approved' else 'diminta revisi 🔄'
        flash(f'Pengumpulan {label}', 'success')
    return redirect(url_for('main.assignment_detail', assign_id=sub.assignment_id))


@main.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


# ─── ORIGINAL QUEST ROUTES ────────────────────────────────────────────────────

@main.route('/add', methods=['GET', 'POST'])
@login_required
def add_quest():
    if request.method == 'POST':
        title      = request.form.get('title', '').strip()
        subject    = request.form.get('subject', 'Lainnya')
        difficulty = request.form.get('difficulty', 'easy')
        if not title:
            flash('Nama quest tidak boleh kosong!', 'error')
            return render_template('add_quest.html', subjects=SUBJECTS)
        if difficulty not in ('easy', 'medium', 'hard'):
            difficulty = 'easy'
        xp_reward = logic.get_xp_reward(difficulty)
        quest = Quest(
            user_id=current_user.id, title=title, subject=subject,
            difficulty=difficulty, xp_reward=xp_reward, date=date.today(),
        )
        db.session.add(quest)
        db.session.commit()
        flash(f'Quest "{title}" ditambahkan! 🎯', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('add_quest.html', subjects=SUBJECTS)


@main.route('/complete/<int:quest_id>', methods=['POST'])
@login_required
def complete_quest(quest_id):
    quest = Quest.query.filter_by(id=quest_id, user_id=current_user.id).first_or_404()
    result = logic.complete_quest(current_user, quest)
    if 'error' in result:
        flash(result['error'], 'error')
        return redirect(url_for('main.dashboard'))
    msg = f'+{result["xp_gained"]} XP! '
    if result['leveled_up']:
        msg += f'⚡ LEVEL UP! Kamu sekarang Level {result["new_level"]} – {result["new_level_title"]}!'
    if result['new_achievements']:
        for ach in result['new_achievements']:
            msg += f' | {ach["icon"]} Achievement baru: {ach["name"]}!'
    flash(msg, 'success')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        level_info = logic.get_level_info(current_user.total_xp)
        return jsonify({**result, 'level_info': level_info,
                        'streak': current_user.streak,
                        'total_xp': current_user.total_xp})
    return redirect(url_for('main.dashboard'))


@main.route('/skip/<int:quest_id>', methods=['POST'])
@login_required
def skip_quest(quest_id):
    quest = Quest.query.filter_by(id=quest_id, user_id=current_user.id).first_or_404()
    logic.skip_quest(quest)
    return redirect(url_for('main.dashboard'))


@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        new_name = request.form.get('name', '').strip()
        if new_name:
            current_user.name = new_name
            db.session.commit()
            flash('Nama berhasil diubah!', 'success')
        return redirect(url_for('main.profile'))
    level_info = logic.get_level_info(current_user.total_xp)
    return render_template('profile.html', level_info=level_info)


@main.route('/achievements')
@login_required
def achievements():
    all_ach    = Achievement.query.all()
    earned_ids = {ua.achievement_id for ua in current_user.user_achievements}
    ach_list   = [{'ach': a, 'earned': a.id in earned_ids} for a in all_ach]
    earned_count = len(earned_ids)
    return render_template('achievements.html',
                           ach_list=ach_list,
                           earned_count=earned_count,
                           total_count=len(all_ach))
