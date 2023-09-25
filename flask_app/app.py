# -----------------------------------------------------------
# app.py
# Copyright (C) [2023-09-13] [黄延浩]
#
# Description: [A brief description of what the script does]
# Version: [Version Number, e.g., 1.0.0]
# Last Updated: [Last updated date, e.g., 2023-09-13]
# 1.完成爬虫
# 2.还需要完成增删改查
# 3.完成自定义数量爬虫
# 4.完成评论情感分析
# -----------------------------------------------------------
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from bs4 import BeautifulSoup
import requests
import json
from textblob import TextBlob
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy import or_
# 导入分页相关模块
from flask_sqlalchemy import SQLAlchemy
from flask import request
from functools import wraps
from flask import abort


# from book_scraper import get_books_from_homepage

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
app.secret_key = "hyh0731"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# 在 app 初始化后初始化 Flask-SQLAlchemy
# db.init_app(app)

##########################################################################
#用户登录注册
##########################################################################
# 管理员
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if current_user.role != 'admin':
            abort(403)  # 403 Forbidden，表示没有权限
        return f(*args, **kwargs)
    return decorated_function

# 用户数据库
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='user')  # 用户角色，可以是 'admin' 或 'user'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 初始化 Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            error = '用户名或密码不正确'
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # 验证用户名和密码长度
        if len(username) < 3 or len(username) > 20:
            error = '用户名长度应在3-20字符之间'
        elif len(password) < 8 or len(password) > 50:
            error = '密码长度应在8-50字符之间'
        elif password != confirm_password:
            error = '密码和确认密码不匹配'
        elif User.query.filter_by(username=username).first():
            error = '用户名已存在'
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('注册成功', 'success')
            return redirect(url_for('login'))

    return render_template('register.html', error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

######################################################################
#图书模型
######################################################################

# 定义图书模型
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), unique=True, nullable=False)
    author = db.Column(db.String(40), nullable=False)
    rating = db.Column(db.String(50), nullable=True)
    cover_url = db.Column(db.String(200))  # 添加封面URL字段
    comment = db.Column(db.String(500))  # 添加评论字段
    publisher = db.Column(db.String(100))
    subtitle = db.Column(db.String(100))
    translator = db.Column(db.String(100))
    publish_date = db.Column(db.String(20))
    pages = db.Column(db.Integer)
    price = db.Column(db.String(20))
    binding = db.Column(db.String(50))
    isbn = db.Column(db.String(50))
    # 你可以根据需要添加更多字段

#############################################################
#主页函数

# 主页视图函数，支持分页
@app.route('/')
@login_required
def index():
    form = DeleteAllBooksForm()
    page = request.args.get('page', 1, type=int)  # 获取页码参数，默认为第一页

    # 每页显示的图书数量
    per_page = 10

    query = request.args.get('query')
    if query:
        # 使用 filter 时应该链式调用 paginate 来进行分页，以及指定每页显示的数量
        books = Book.query.filter(or_(Book.title.contains(query), Book.author.contains(query))) \
            .paginate(page=page, per_page=per_page, error_out=False)
    else:
        books = Book.query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('index.html', books=books,form=form)

#######################################################################################
#编辑与删除

import json

@app.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
@admin_required
def edit_book(book_id):
    form = DeleteAllBooksForm()
    book = Book.query.get_or_404(book_id)

    if request.method == 'POST':
        # 更新图书信息
        book.title = request.form.get('title')
        book.author = request.form.get('author')
        book.rating = request.form.get('rating')
        book.cover_url = request.form.get('cover_url')

        # 获取用户编辑后的评论文本
        edited_comments_text = request.form.get('comment')
        edited_comments_list = [comment.strip() for comment in edited_comments_text.split('\n') if comment.strip()]
        # 转换为 JSON 格式并保存到数据库
        book.comment = json.dumps(edited_comments_list)

        book.publisher = request.form.get('publisher')
        book.subtitle = request.form.get('subtitle')
        book.translator = request.form.get('translator')
        book.publish_date = request.form.get('publish_date')
        book.pages = request.form.get('pages')
        book.price = request.form.get('price')
        book.binding = request.form.get('binding')
        book.isbn = request.form.get('isbn')

        try:
            db.session.commit()
            flash('Book updated successfully', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update book: {str(e)}', 'danger')

    # 在编辑页面中，将评论从 JSON 字符串转换为文本以供用户编辑
    comments_text = "\n".join(json.loads(book.comment)) if book.comment else ""

    return render_template('edit_book.html', book=book, comments=comments_text,form = form)



@app.route('/delete_book/<int:book_id>')
@admin_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    flash('Book deleted successfully', 'success')
    return redirect(url_for('index'))

################################################################################

# 爬虫url
@app.route('/crawl', methods=['GET', 'POST'])
@admin_required
def crawl():
    form = DeleteAllBooksForm()
    if request.method == 'POST':
        url = request.form.get('url')
        num_books = int(request.form.get('num_books'))  # 获取希望爬取的图书数量

        # 为了避免重复，我们创建了一个帮助函数
        def add_book_to_db(book_info):
            # 检查书是否已经在数据库中
            existing_book = Book.query.filter_by(title=book_info['title']).first()
            if existing_book:
                # 如果书已存在，可以选择更新或跳过
                flash(f"书籍 {book_info['title']} 已经存在。跳过...", "warning")
            else:
                # 如果书不存在，添加到数据库
                book = Book(**book_info)
                db.session.add(book)
                db.session.commit()

        if "https://book.douban.com/" == url:  # 判断是否为豆瓣读书主页
            books_info_list = get_books_from_homepage(url, num_books)
            for book_info in books_info_list:
                add_book_to_db(book_info)

            flash(f"已经成功存储了{len(books_info_list)}本书的信息到数据库中！", "success")
            return redirect(url_for('index'))
        else:
            book_info = get_book_info(url)
            add_book_to_db(book_info)
            flash("图书信息已成功存储到数据库！", "success")
            return redirect(url_for('index'))

    return render_template('crawl.html', form=form)


##############################################################################
# 上架新书

# 在您的 app.py 文件中添加以下路由和视图函数
import json


@app.route('/add_book', methods=['GET', 'POST'])
@admin_required
def add_book():
    form = DeleteAllBooksForm()
    if request.method == 'POST':
        # 从表单获取图书信息
        title = request.form.get('title')
        author = request.form.get('author')
        rating = request.form.get('rating')
        cover_url = request.form.get('cover_url')

        # 获取评论文本，按行拆分并去除空白字符
        comments_text = request.form.get('comment')
        comments_list = [comment.strip() for comment in comments_text.split('\n') if comment.strip()]

        publisher = request.form.get('publisher')
        subtitle = request.form.get('subtitle')
        translator = request.form.get('translator')
        publish_date = request.form.get('publish_date')
        pages = request.form.get('pages')
        price = request.form.get('price')
        binding = request.form.get('binding')
        isbn = request.form.get('isbn')

        # 创建新的图书对象并保存到数据库
        new_book = Book(
            title=title,
            author=author,
            rating=rating,
            cover_url=cover_url,
            comment=json.dumps(comments_list),  # 将评论列表转换为 JSON 字符串
            publisher=publisher,
            subtitle=subtitle,
            translator=translator,
            publish_date=publish_date,
            pages=pages,
            price=price,
            binding=binding,
            isbn=isbn
        )

        try:
            db.session.add(new_book)
            db.session.commit()
            flash('成功上架新书', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'上架图书失败: {str(e)}', 'danger')

    return render_template('add_book.html',form=form)


##############################################################################
# 在书籍详情页面中，增加对评论的情感分析

@app.route('/book/<int:book_id>')
def book_details(book_id):
    book = Book.query.get(book_id)
    if not book:
        flash("Book not found!", "danger")
        return redirect(url_for('index'))

    comments = json.loads(book.comment)  # 反序列化评论

    # 分析评论情感
    sentiments = [analyze_sentiment(comment) for comment in comments]
    print(sentiments)

    # 为每个评论计算情感分析分数
    sentiment_scores = [get_sentiment_score(comment) for comment in comments]

    positive_count = sentiments.count('好')
    neutral_count = sentiments.count('中')
    negative_count = sentiments.count('差')

    # 基于评论情感评估书籍
    if positive_count > neutral_count and positive_count > negative_count:
        book_evaluation = "好"
    elif negative_count > positive_count and negative_count > neutral_count:
        book_evaluation = "差"
    else:
        book_evaluation = "中"

    # 在视图函数中创建comments_with_sentiments的数据结构
    comments_with_sentiments = [{'comment': comment, 'sentiment': sentiment, 'sentiment_score': sentiment_scores[i]} for
                                i, (comment, sentiment) in enumerate(zip(comments, sentiments))]

    # 传递到模板
    return render_template('book_details.html', book=book, comments_with_sentiments=comments_with_sentiments,
                           evaluation=book_evaluation)

###############################################################################################################
#  具体的爬虫代码
# 爬虫代码
def get_book_info(url):
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36"
    }
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.content, 'html.parser')

    # 封面
    try:
        cover_url = soup.find('div', id='mainpic').find('img')['src']
    except AttributeError:
        cover_url = None
        print("Error: Couldn't find the book cover.")

    # 标题
    title = soup.find('span', property='v:itemreviewed').text

    # 作者
    author_span = None
    for span in soup.find_all('span'):
        if '作者' in span.text:
            author_span = span
            break

    if author_span:
        authors = [a.get_text().strip() for a in author_span.find_all('a')]
        author = ' / '.join(authors)
    else:
        author = "未知"

    # 评分
    rating_tag = soup.find('strong', class_='rating_num')
    if rating_tag and rating_tag.text.strip():
        rating = rating_tag.text.strip()
    else:
        rating = "暂无"

    # 评论
    comments_tags = soup.find_all('span', class_='short', limit=5)  # 获取前5条评论
    comment_list = [tag.text for tag in comments_tags] if comments_tags else ["暂无评论"]
    comment = json.dumps(comment_list)  # 序列化评论列表为字符串


    # 提取新的字段
    try:
        publisher = soup.find("span", class_="pl", string="出版社:").next_sibling.strip()
    except AttributeError:
        publisher = "未知"

    try:
        subtitle = soup.find("span", class_="pl", string="副标题:").next_sibling.strip()
    except AttributeError:
        subtitle = "未知"

    translator_span = soup.find("span", string=" 译者")
    translator = ' / '.join([a.text.strip() for a in translator_span.find_all('a')]) if translator_span else "未知"

    try:
        publish_date = soup.find("span", class_="pl", string="出版年:").next_sibling.strip()
    except AttributeError:
        publish_date = "未知"

    try:
        pages = int(soup.find("span", class_="pl", string="页数:").next_sibling.strip().replace('页', ''))
    except AttributeError:
        pages = None

    try:
        price = soup.find("span", class_="pl", string="定价:").next_sibling.strip()
    except AttributeError:
        price = "未知"

    try:
        binding = soup.find("span", class_="pl", string="装帧:").next_sibling.strip()
    except AttributeError:
        binding = "未知"

    try:
        isbn = soup.find("span", class_="pl", string="ISBN:").next_sibling.strip()
    except AttributeError:
        isbn = "未知"

    return {
        'title': title,
        'author': author,
        'rating': rating,
        'cover_url': cover_url,
        'comment': comment,
        'publisher': publisher,
        'subtitle': subtitle,
        'translator': translator,
        'publish_date': publish_date,
        'pages': pages,
        'price': price,
        'binding': binding,
        'isbn': isbn
    }

def get_books_from_homepage(homepage_url, num_books=20):
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36"
    }
    response = requests.get(homepage_url, headers=HEADERS)
    soup = BeautifulSoup(response.content, 'html.parser')

    book_links = soup.select('div.cover a[href^="https://book.douban.com/subject/"]')
    book_ids = [link['href'].split('/')[-2] for link in book_links]

    book_info_list = []
    for book_id in book_ids[:num_books]:  # 取前num_books本图书
        book_info = get_book_info(f"https://book.douban.com/subject/{book_id}/")
        book_info_list.append(book_info)

    return book_info_list

##########################################################################################

from hanlp_restful import HanLPClient
HanLP = HanLPClient('https://www.hanlp.com/api', auth='MjA5OEBiYnMuaGFubHAuY29tOlpRcktyN3A4R2ZDM3FGQ1g=', language='zh')
# 定义情感分析函数
def analyze_sentiment(text):
    try:
        sentiment_score = HanLP.sentiment_analysis(text) # 获取情感分数
        if sentiment_score > 0.65:
            return '好'
        elif sentiment_score > 0.35:
            return '中'
        else:
            return '差'
    except Exception as e:
        print(f"Error analyzing sentiment: {str(e)}")
        return 'Error'
def get_sentiment_score(comment):
    try:
        sentiment_score = HanLP.sentiment_analysis(comment) # 获取情感分数
        return sentiment_score
    except Exception as e:
        print(f"Error analyzing sentiment: {str(e)}")
        return 'Error'

##############################################################################################
# 删除全部
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import InputRequired, EqualTo


class DeleteAllBooksForm(FlaskForm):
    secret_key = StringField('密钥', validators=[InputRequired(), EqualTo('hyh0731')])
    submit = SubmitField('删除全部图书')

@app.route('/delete_all_books', methods=['GET', 'POST'])
@admin_required
def delete_all_books():

    form = DeleteAllBooksForm()

    if form.validate_on_submit():
        if form.secret_key.data == 'hyh0731':
            try:
                # 执行删除所有图书的操作
                Book.query.delete()
                db.session.commit()
                flash('已成功删除所有图书', 'success')
            except Exception as e:
                flash(f'删除图书时出错: {str(e)}', 'danger')
        else:
            flash('密钥错误，请重新输入', 'danger')

    return redirect(url_for('index'))

from flask_migrate import Migrate

migrate = Migrate(app, db)

if __name__ == '__main__':
    with app.app_context():
        # 创建数据库模型和进行数据库迁移
        db.create_all()
        # migrate.init_app(app)

        # # 查询要更新的用户
        # user_to_update = User.query.filter_by(username="admin").first()
        #
        # if user_to_update:
        #     # 更新用户角色
        #     user_to_update.role = 'admin'
        #
        #     # 提交更改到数据库
        #     db.session.commit()
        #     print('用户数据已成功更新')
        # else:
        #     print('未找到要更新的用户')

    app.run(debug=True)