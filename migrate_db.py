from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User 모델 정의 (web_app.py와 동일하게 유지)
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

if __name__ == '__main__':
    with app.app_context():
        # 데이터베이스 파일이 없으면 생성
        db.create_all()
        print("데이터베이스가 성공적으로 초기화되었습니다.")
        print(f"데이터베이스 파일 경로: {os.path.abspath('instance/site.db')}")
