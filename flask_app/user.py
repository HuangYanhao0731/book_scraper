from flask import Flask
from app import  User  # 请替换为您的应用程序的导入路径
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# 配置数据库连接字符串，例如：
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'

# 初始化SQLAlchemy实例
db = SQLAlchemy(app)

app = Flask(__name__)
app.app_context().push()  # 创建应用上下文

# 查询要更新的用户
user_to_update = User.query.filter_by(username="admin").first()

if user_to_update:
    # 更新用户数据
    user_to_update.role = 'admin'

    # 提交更改到数据库
    db.session.commit()
    print('用户数据已成功更新')
else:
    print('未找到要更新的用户')
