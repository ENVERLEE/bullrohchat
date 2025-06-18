import os
import subprocess
import threading
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from database import OracleManager
from crawler import BlogCrawler
from embedder import Embedder

# Load environment variables

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')

load_dotenv()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # This is the login route name

# User class for Flask-Login (Oracle version)
class User(UserMixin):
    def __init__(self, id, username, email, is_premium=0):
        self.id = id
        self.username = username
        self.email = email
        self.is_premium = is_premium

@login_manager.user_loader
def load_user(user_id):
    db = OracleManager()
    user = db.get_user_by_id(user_id)
    db.close()
    if user:
        return User(user['id'], user['username'], user['email'], user.get('is_premium', 0))
    return None


# Global variable to store the subprocess reference
chatbot_process = None

def get_db_connection():
    return OracleManager()

# Routes

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        db = OracleManager()
        user = db.get_user_by_username(username)
        db.close()
        if user and check_password_hash(user['password'], password):
            user_obj = User(user['id'], user['username'], user['email'], user.get('is_premium', 0))
            login_user(user_obj, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('로그인에 실패했습니다. 아이디와 비밀번호를 확인해주세요.', 'danger')
    return render_template('login.html')

@app.route('/')
@login_required
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if password != confirm_password:
            flash('비밀번호가 일치하지 않습니다.', 'danger')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password)
        db = OracleManager()
        try:
            db.create_user(username, email, hashed_password)
            flash('회원가입이 완료되었습니다. 로그인해주세요.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('이미 존재하는 사용자 이름이나 이메일입니다.', 'danger')
        finally:
            db.close()
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# 프리미엄 업그레이드 예시
@app.route('/premium')
@login_required
def premium():
    db = OracleManager()
    db.upgrade_user_to_premium(current_user.id)
    db.close()
    flash('프리미엄 서비스가 활성화되었습니다!', 'success')
    return redirect(url_for('home'))

@app.route('/config')
@login_required
def config():
    return render_template('config.html')

@app.route('/config/chatbot', methods=['GET', 'POST'])
@login_required
def chatbot_config():
    db = get_db_connection()
    info = db.get_business_info()
    
    if request.method == 'POST':
        try:
            business_name = request.form.get('business_name', '')
            blog_url = request.form.get('blog_url', '')
            chatbot_personality = request.form.get('chatbot_personality', '')
            marketing_info = request.form.get('marketing_info', '')
            
            # Get existing info to preserve FAQs
            existing_info = db.get_business_info() or {}
            
            # Update with new values
            updated_info = {
                'business_name': business_name,
                'blog_url': blog_url,
                'chatbot_personality': chatbot_personality,
                'marketing_info': marketing_info,
                'faqs': existing_info.get('faqs', [])
            }
            
            db.save_business_info(updated_info)
            flash('챗봇 설정이 저장되었습니다.', 'success')
            return redirect(url_for('chatbot_config'))
        except Exception as e:
            flash(f'오류가 발생했습니다: {str(e)}', 'error')
    
    db.close()
    return render_template('chatbot_config.html', info=info)

@app.route('/config/faq', methods=['GET', 'POST'])
@login_required
def faq_management():
    db = get_db_connection()
    info = db.get_business_info() or {}
    faqs = info.get('faqs', [])
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            question = request.form.get('question')
            answer = request.form.get('answer')
            if question and answer:
                faqs.append({'q': question, 'a': answer})
        elif action == 'delete':
            index = int(request.form.get('index'))
            if 0 <= index < len(faqs):
                faqs.pop(index)
        
        # Update the FAQs in the database
        info['faqs'] = faqs
        db.save_business_info(info)
        return redirect(url_for('faq_management'))
    
    db.close()
    return render_template('faq_management.html', faqs=faqs)

@app.route('/config/crawler', methods=['GET', 'POST'])
@login_required
def crawler_config():
    if request.method == 'POST':
        max_posts = request.form.get('max_posts', '')
        # Save crawler configuration (you'll need to implement this)
        # For now, we'll just show a success message
        flash('크롤러 설정이 저장되었습니다.', 'success')
        return redirect(url_for('crawler_config'))
    
    # Get current configuration (you'll need to implement this)
    config = {'max_posts': 10}  # Default value
    return render_template('crawler_config.html', config=config)

@app.route('/crawl', methods=['POST'])
@login_required
def start_crawl():
    try:
        max_posts = request.form.get('max_posts', 10, type=int)
        
        # Run the crawler in a separate thread
        def run_crawler():
            try:
                db = get_db_connection()
                info = db.get_business_info()
                if not info or not info.get('blog_url'):
                    return
                
                crawler = BlogCrawler()
                embedder = Embedder()
                all_posts_meta = crawler.crawl_all_posts(info['blog_url'], max_posts=max_posts)
                
                if not all_posts_meta:
                    return
                
                for post_meta in all_posts_meta:
                    try:
                        content_data = crawler.crawl_post_content(post_meta['url'])
                        if not content_data:
                            continue
                            
                        # Process and save the post
                        # (This is a simplified version - you might want to add more error handling)
                        content_for_embedding = content_data.get('content', '')
                        chunks = embedder.split_text(content_for_embedding)
                        embeddings = embedder.embed_texts(chunks)
                        chunks_with_embeddings = [{"chunk_text": text, "embedding": emb.tolist()} for text, emb in zip(chunks, embeddings)]
                        
                        # Generate a hash for the content
                        import hashlib
                        content_hash = hashlib.sha256(content_for_embedding.encode('utf-8')).hexdigest()
                        
                        db.upsert_post_with_chunks(post_meta['url'], post_meta['title'], content_hash, chunks_with_embeddings)
                    except Exception as e:
                        print(f"Error processing post {post_meta['url']}: {str(e)}")
                        continue
                
                crawler.close()
            except Exception as e:
                print(f"Error in crawler thread: {str(e)}")
            finally:
                if 'db' in locals():
                    db.close()
        
        # Start the crawler in a separate thread
        thread = threading.Thread(target=run_crawler)
        thread.daemon = True
        thread.start()
        
        return jsonify({'status': 'started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/start_chatbot', methods=['POST'])
@login_required
def start_chatbot():
    global chatbot_process
    
    # If chatbot is already running, return its status
    if chatbot_process and chatbot_process.poll() is None:
        return jsonify({'status': 'already_running'})
    
    try:
        # Start the chatbot as a subprocess
        chatbot_process = subprocess.Popen(
            ['python', 'main.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Start a thread to monitor the process
        def monitor_process():
            chatbot_process.communicate()
        
        thread = threading.Thread(target=monitor_process)
        thread.daemon = True
        thread.start()
        
        return jsonify({'status': 'started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/stop_chatbot', methods=['POST'])
@login_required
def stop_chatbot():
    global chatbot_process
    
    if chatbot_process and chatbot_process.poll() is None:
        try:
            chatbot_process.terminate()
            chatbot_process.wait(timeout=5)
            return jsonify({'status': 'stopped'})
        except subprocess.TimeoutExpired:
            chatbot_process.kill()
            return jsonify({'status': 'force_stopped'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    return jsonify({'status': 'not_running'})

@app.route('/ask', methods=['POST'])
@login_required
def ask_question():
    data = request.get_json()
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    try:
        # Here you would typically call your chatbot service
        # For now, we'll just return a mock response
        return jsonify({
            'answer': f'This is a response to: {question}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
