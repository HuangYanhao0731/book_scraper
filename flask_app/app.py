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

# from book_scraper import get_books_from_homepage

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
app.secret_key = "hyh0731"
db = SQLAlchemy(app)

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

# 创建主页视图函数
@app.route('/')
def index():
    books = Book.query.all()
    return render_template('index.html', books=books)


# 爬虫
@app.route('/crawl', methods=['GET', 'POST'])
def crawl():
    if request.method == 'POST':
        url = request.form.get('url')

        # 为了避免重复，我们创建了一个帮助函数
        def add_book_to_db(book_info):
            # 检查书是否已经在数据库中
            existing_book = Book.query.filter_by(title=book_info['title']).first()
            if existing_book:
                # 如果书已存在，可以选择更新或跳过
                flash(f"Book {book_info['title']} already exists. Skipping...", "warning")
            else:
                # 如果书不存在，添加到数据库
                book = Book(**book_info)
                db.session.add(book)
                db.session.commit()

        if "https://book.douban.com/" == url:  # 判断是否为豆瓣读书主页
            books_info_list = get_books_from_homepage(url)
            for book_info in books_info_list:
                add_book_to_db(book_info)

            flash(f"已经成功存储了{len(books_info_list)}本书的信息到数据库中！", "success")
            return redirect(url_for('index'))
        else:
            book_info = get_book_info(url)
            add_book_to_db(book_info)
            flash("图书信息已成功存储到数据库！", "success")
            return redirect(url_for('index'))

    return render_template('crawl.html')

@app.route('/search')
def search():
    # ... 具体实现
    return render_template('search_results.html')

# 查看图书详细
@app.route('/book/<int:book_id>')
def book_details(book_id):
    book = Book.query.get(book_id)
    if not book:
        flash("Book not found!", "danger")
        return redirect(url_for('index'))
    return render_template('book_details.html', book=book)

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
    comment = [tag.text for tag in comments_tags] if comments_tags else ["暂无评论"]


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

def get_books_from_homepage(homepage_url, num_books=30):
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

if __name__ == '__main__':
    with app.app_context():
        # 创建数据库模型
        db.create_all()
    app.run(debug=True)