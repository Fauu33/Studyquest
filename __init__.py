import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
login_manager.login_message = 'Login dulu ya!'

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure upload folder exists
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from app.routes import main
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()
        _seed_achievements()

    return app

def _seed_achievements():
    from app.models import Achievement
    if Achievement.query.count() > 0:
        return
    defaults = [
        Achievement(name='First Quest!',       description='Selesaikan quest pertamamu',          icon='🌟', xp_reward=20,  condition='total_done>=1'),
        Achievement(name='100 XP Club',        description='Kumpulkan 100 XP pertamamu',           icon='💯', xp_reward=0,   condition='total_xp>=100'),
        Achievement(name='On Fire!',           description='Streak 3 hari berturut-turut',         icon='🔥', xp_reward=30,  condition='best_streak>=3'),
        Achievement(name='Seminggu Penuh',     description='Streak 7 hari berturut-turut',         icon='📅', xp_reward=70,  condition='best_streak>=7'),
        Achievement(name='Quest Hunter',       description='Selesaikan 10 quest',                  icon='🎯', xp_reward=50,  condition='total_done>=10'),
        Achievement(name='Berani Susah',       description='Selesaikan 1 quest Hard',              icon='💀', xp_reward=25,  condition='hard_done>=1'),
        Achievement(name='Setengah Jalan',     description='Capai level 5',                        icon='⚡', xp_reward=100, condition='level>=5'),
        Achievement(name='500 XP Legend',      description='Kumpulkan 500 XP total',               icon='👑', xp_reward=0,   condition='total_xp>=500'),
    ]
    db.session.add_all(defaults)
    db.session.commit()
