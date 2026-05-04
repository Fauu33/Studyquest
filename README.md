# ⚡ StudyQuest – Belajar Jadi Game

Gamifikasi belajar untuk siswa SMP. Selesaikan quest, kumpulkan XP, naik level!

## 🚀 Cara Menjalankan

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Jalankan server
```bash
python run.py
```

### 3. Buka browser
```
http://localhost:5000
```

## 📁 Struktur Project

```
studyquest/
├── app/
│   ├── __init__.py     ← App factory & seed achievements
│   ├── routes.py       ← Semua URL endpoint
│   ├── models.py       ← Database models (User, Quest, Achievement)
│   ├── logic.py        ← Business logic (XP, level, streak, achievements)
│   ├── templates/      ← HTML templates (Jinja2)
│   └── static/         ← CSS, JS, assets
├── database/
│   └── db.sqlite3      ← Auto-dibuat saat pertama run
├── config.py           ← Konfigurasi app
├── run.py              ← Entry point
└── requirements.txt
```

## 🎮 Fitur

- **Quest System** – Tambah quest harian dengan difficulty Easy/Medium/Hard
- **XP & Level** – 7 level dari Pemula Sejati sampai Dewa Belajar
- **Streak** – Hitung hari berturut-turut belajar
- **Achievements** – 8 achievement untuk unlock
- **Animasi** – XP popup & level-up notification via AJAX
- **Auth** – Register & login dengan password terenkripsi

## ⚙️ Level System

| Level | XP Dibutuhkan | Title |
|-------|--------------|-------|
| 1     | 0            | Pemula Sejati |
| 2     | 100          | Penjelajah Muda |
| 3     | 250          | Petualang Aktif |
| 4     | 500          | Pahlawan Belajar |
| 5     | 900          | Master Ilmu |
| 6     | 1400         | Legenda Sekolah |
| 7     | 2000         | Dewa Belajar |

## 🔧 Tech Stack

- **Backend**: Python + Flask
- **Database**: SQLite + SQLAlchemy
- **Auth**: Flask-Login
- **Frontend**: HTML + CSS (custom) + vanilla JS
- **Font**: Nunito (Google Fonts)
