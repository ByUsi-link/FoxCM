from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from datetime import datetime
import json
import os
import random
import string
import uuid

app = Flask(__name__)
app.secret_key = 'FoxCM_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads/videos'
app.config['COVER_FOLDER'] = 'static/uploads/covers'
USER_DATA_FILE = 'data/user.json'
VIDEO_DATA_FILE = 'data/foxcm-sp.json'
ADMIN = False

# 允许的文件扩展名
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov'}
ALLOWED_COVER_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}

# 随机生成文件名
def generate_random_filename(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# 检查文件扩展名
def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# 加载用户数据
def load_users():
    try:
        with open(USER_DATA_FILE, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# 保存用户数据
def save_users(users):
    with open(USER_DATA_FILE, 'w') as file:
        json.dump(users, file, indent=4)

# 加载视频数据
def load_videos():
    try:
        with open(VIDEO_DATA_FILE, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# 保存视频数据
def save_videos(videos):
    with open(VIDEO_DATA_FILE, 'w') as file:
        json.dump(videos, file, indent=4)

# 查找用户 by ID
def find_user_by_id(user_id):
    users = load_users()
    return next((user for user in users if user['id'] == user_id), None)

# 查找用户 by username
def find_user_by_username(username):
    users = load_users()
    return next((user for user in users if user['username'] == username), None)

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    videos = load_videos()
    random.shuffle(videos)  # 随机打乱视频列表
    return render_template('index.html', videos=videos)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()

        if find_user_by_username(username):
            flash('用户名已存在！')
            return redirect(url_for('register'))

        new_user = {
            "id": len(users) + 1,
            "username": username,
            "password": password,
            "is_admin": ADMIN
        }
        users.append(new_user)
        save_users(users)

        flash('注册成功，请登录！')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = find_user_by_username(username)

        if user and user['password'] == password:
            session['logged_in'] = True
            session['user_id'] = user['id']
            flash('登录成功！')
            return redirect(url_for('index'))
        flash('用户名或密码错误！')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('已注销登录！')
    return redirect(url_for('login'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        video_file = request.files['video']
        cover_file = request.files['cover']
        title = request.form['title']
        description = request.form.get('description', '')

        if not video_file or not cover_file or not title:
            flash('视频文件、封面和标题是必填项！')
            return redirect(url_for('upload'))

        # 验证视频文件
        if not allowed_file(video_file.filename, ALLOWED_VIDEO_EXTENSIONS):
            flash('视频格式不支持！支持格式：mp4, avi, mov')
            return redirect(url_for('upload'))

        # 验证封面文件
        if not allowed_file(cover_file.filename, ALLOWED_COVER_EXTENSIONS):
            flash('封面格式不支持！支持格式：jpg, jpeg, png')
            return redirect(url_for('upload'))

        # 保存视频文件
        video_filename = str(uuid.uuid4()) + '.' + video_file.filename.rsplit('.', 1)[1]
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
        video_file.save(video_path)

        # 保存封面文件
        cover_filename = str(uuid.uuid4()) + '.' + cover_file.filename.rsplit('.', 1)[1]
        cover_path = os.path.join(app.config['COVER_FOLDER'], cover_filename)
        cover_file.save(cover_path)

        # 获取上传者信息
        user = find_user_by_id(session['user_id'])
        uploader_username = user['username'] if user else '未知用户'

        # 获取当前时间
        upload_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 创建视频数据
        video_data = {
            "video_filename": video_filename,
            "cover_filename": cover_filename,
            "title": title,
            "description": description,
            "uploader": uploader_username,
            "upload_time": upload_time,
            "user_id": session['user_id'],
            "play_count": 0  # 初始化播放次数
        }

        # 保存视频数据
        videos = load_videos()
        videos.append(video_data)
        save_videos(videos)

        flash('视频上传成功！')
        return redirect(url_for('index'))

    return render_template('upload.html')

@app.route('/play/<video_filename>')
def play(video_filename):
    videos = load_videos()
    # 查找匹配的视频
    video = next((v for v in videos if v['video_filename'] == video_filename), None)
    if video:
        # 更新播放次数
        video['play_count'] += 1
        save_videos(videos)
        return render_template('play.html', video=video)
    flash('视频不存在！')
    return redirect(url_for('index'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    user = find_user_by_id(session['user_id'])
    if not user or not user.get('is_admin'):
        flash('只有管理员可以访问该页面！')
        return redirect(url_for('index'))
    
    users = load_users()
    videos = load_videos()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'delete_user':
            user_id_to_delete = int(request.form.get('user_id'))
            users = [u for u in users if u['id'] != user_id_to_delete]
            save_users(users)
            flash('用户删除成功！')
            return redirect(url_for('admin'))
        elif action == 'delete_video':
            video_filename_to_delete = request.form.get('video_filename')
            videos = [v for v in videos if v['video_filename'] != video_filename_to_delete]
            save_videos(videos)
            # 删除视频文件和封面文件
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename_to_delete)
            cover_path = os.path.join(app.config['COVER_FOLDER'], next((v['cover_filename'] for v in videos if v['video_filename'] == video_filename_to_delete), ''))
            if os.path.exists(video_path):
                os.remove(video_path)
            if os.path.exists(cover_path):
                os.remove(cover_path)
            flash('视频删除成功！')
            return redirect(url_for('admin'))

    return render_template('admin.html', users=users, videos=videos)

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    if not query:
        flash("请输入搜索内容！", "info")
        return redirect(url_for('index'))
    
    # 加载视频数据
    videos = load_videos()
    
    # 简单关键字匹配，支持标题和描述的搜索
    search_results = [
        video for video in videos 
        if query.lower() in video['title'].lower() or query.lower() in video['description'].lower()
    ]
    
    # 渲染搜索结果页面
    return render_template('search_results.html', query=query, videos=search_results)

# 初始化目录和文件
if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['COVER_FOLDER'], exist_ok=True)
    os.makedirs('data', exist_ok=True)
    if not os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'w') as file:
            json.dump([], file)
    if not os.path.exists(VIDEO_DATA_FILE):
        with open(VIDEO_DATA_FILE, 'w') as file:
            json.dump([], file)
    app.run(host='0.0.0.0', port=6544, debug=True)