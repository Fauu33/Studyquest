"""
logic.py — Business logic StudyQuest.
Semua perhitungan XP, level, streak, dan achievement ada di sini.
Routes.py HANYA memanggil fungsi dari sini → code tetap bersih.
"""

from datetime import date
from app import db
from app.models import User, Quest, Achievement, UserAchievement

# ─── LEVEL SYSTEM ────────────────────────────────────────────────────────────

LEVELS = [
    {'xp': 0,    'title': 'Pemula Sejati'},
    {'xp': 100,  'title': 'Penjelajah Muda'},
    {'xp': 250,  'title': 'Petualang Aktif'},
    {'xp': 500,  'title': 'Pahlawan Belajar'},
    {'xp': 900,  'title': 'Master Ilmu'},
    {'xp': 1400, 'title': 'Legenda Sekolah'},
    {'xp': 2000, 'title': 'Dewa Belajar'},
]

XP_REWARDS = {
    'easy':   10,
    'medium': 25,
    'hard':   50,
}


def get_level_info(total_xp: int) -> dict:
    """
    Hitung level, title, progress XP dari total XP user.
    Return: {level, title, prog, needed, pct}
    """
    level = 1
    prog = total_xp
    needed = LEVELS[1]['xp']

    for i in range(1, len(LEVELS)):
        if total_xp >= LEVELS[i]['xp']:
            level = i + 1
        else:
            prog   = total_xp - LEVELS[i - 1]['xp']
            needed = LEVELS[i]['xp'] - LEVELS[i - 1]['xp']
            break
    else:
        # Sudah max level
        prog   = total_xp - LEVELS[-1]['xp']
        needed = 0

    title = LEVELS[min(level - 1, len(LEVELS) - 1)]['title']
    pct   = round((prog / needed * 100) if needed > 0 else 100)

    return {
        'level':  level,
        'title':  title,
        'prog':   prog,
        'needed': needed,
        'pct':    pct,
    }


# ─── XP LOGIC ────────────────────────────────────────────────────────────────

def add_xp(user: User, amount: int) -> bool:
    """
    Tambah XP ke user. Return True kalau level naik.
    """
    old_level = get_level_info(user.total_xp)['level']
    user.xp       += amount
    user.total_xp += amount
    new_info       = get_level_info(user.total_xp)
    user.level     = new_info['level']
    return new_info['level'] > old_level


def get_xp_reward(difficulty: str) -> int:
    return XP_REWARDS.get(difficulty, 10)


# ─── STREAK LOGIC ────────────────────────────────────────────────────────────

def update_streak(user: User) -> None:
    """
    Hitung ulang streak berdasarkan last_active.
    Dipanggil setelah quest selesai.
    """
    today = date.today()

    if user.last_active == today:
        return  # Sudah dihitung hari ini

    if user.last_active is None:
        # Pertama kali
        user.streak = 1
    else:
        delta = (today - user.last_active).days
        if delta == 1:
            # Hari berturut-turut
            user.streak += 1
        elif delta > 1:
            # Streak putus
            user.streak = 1
        # delta == 0 sudah ditangani di atas

    user.last_active = today

    if user.streak > user.best_streak:
        user.best_streak = user.streak


# ─── QUEST LOGIC ─────────────────────────────────────────────────────────────

def complete_quest(user: User, quest: Quest) -> dict:
    """
    Proses penyelesaian quest:
    1. Update status quest
    2. Tambah XP
    3. Update streak
    4. Cek achievements baru
    Return dict hasil untuk ditampilkan di UI.
    """
    if quest.status != 'pending':
        return {'error': 'Quest sudah selesai atau dilewati.'}

    quest.status = 'completed'
    xp_gained    = quest.xp_reward

    user.total_done += 1
    if quest.difficulty == 'hard':
        user.hard_done += 1

    leveled_up = add_xp(user, xp_gained)
    update_streak(user)

    new_achievements = check_achievements(user)

    db.session.commit()

    level_info = get_level_info(user.total_xp)
    return {
        'xp_gained':        xp_gained,
        'leveled_up':       leveled_up,
        'new_level':        level_info['level'],
        'new_level_title':  level_info['title'],
        'new_achievements': new_achievements,
    }


def skip_quest(quest: Quest) -> None:
    quest.status = 'skipped'
    db.session.commit()


# ─── ACHIEVEMENT LOGIC ────────────────────────────────────────────────────────

def _build_context(user: User) -> dict:
    """Bangun context variabel untuk evaluasi kondisi achievement."""
    return {
        'total_done':  user.total_done,
        'total_xp':    user.total_xp,
        'best_streak': user.best_streak,
        'hard_done':   user.hard_done,
        'level':       user.level,
    }


def check_achievements(user: User) -> list[dict]:
    """
    Cek semua achievement yang belum diraih.
    Kalau kondisi terpenuhi → unlock & beri XP bonus.
    Return list achievement baru yang baru saja diraih.
    """
    earned_ids = {ua.achievement_id for ua in user.user_achievements}
    all_achievements = Achievement.query.all()
    ctx = _build_context(user)
    newly_earned = []

    for ach in all_achievements:
        if ach.id in earned_ids:
            continue
        try:
            unlocked = eval(ach.condition, {'__builtins__': {}}, ctx)  # noqa: S307
        except Exception:
            unlocked = False

        if unlocked:
            ua = UserAchievement(user_id=user.id, achievement_id=ach.id)
            db.session.add(ua)
            if ach.xp_reward > 0:
                add_xp(user, ach.xp_reward)
            newly_earned.append({'name': ach.name, 'icon': ach.icon})

    return newly_earned
