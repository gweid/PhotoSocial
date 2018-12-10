"""创建虚拟数据"""
import os
import random

from PIL import Image
from faker import Faker
from flask import current_app
from sqlalchemy.exc import IntegrityError

from photosocial.extensions import db
from photosocial.models import User, Photo, Tag, Comment, Notification

fake = Faker('zh_CN')


def fake_admin():
    """创建虚拟管理员"""
    admin = User(
        name='Weidu',
        username='Gweid',
        email='admin@weidu.com',
        bio=fake.sentence(),
        location='Shenzhen',
        confirmed=True
    )
    admin.set_password('weidu006')
    notification = Notification(message='您好，欢迎来到维度，分享您的每一瞬间！', receiver=admin)
    db.session.add(notification)
    db.session.add(admin)
    db.session.commit()


def fake_user(count=10):
    """创建虚拟用户"""
    for i in range(count):
        user = User(
            name=fake.name(),
            confirmed=True,
            username=fake.user_name(),
            bio=fake.sentence(),
            location=fake.city(),
            website=fake.url(),
            member_since=fake.date_this_decade(),
            email=fake.email()
        )
        user.set_password('123456')
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()


def fake_follow(count=30):
    """虚拟跟随关系"""
    for i in range(count):
        user = User.query.get(random.randint(1, User.query.count()))
        user.follow(User.query.get(random.randint(1, User.query.count())))
    db.session.commit()


def fake_tag(count=20):
    """虚拟标签"""
    for i in range(count):
        tag = Tag(
            name=fake.word()
        )
        db.session.add(tag)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()


def fake_photo(count=30):
    """虚拟图片"""
    upload_path = current_app.config['PHOTOSOCIAL_UPLOAD_PATH']
    for i in range(count):
        print(i)

        filename = 'random_%d.jpg' % i
        r = lambda: random.randint(128, 255)
        img = Image.new(mode='RGB', size=(800, 800), color=(r(), r(), r()))
        img.save(os.path.join(upload_path, filename))

        photo = Photo(
            description=fake.text(),
            filename=filename,
            filename_s=filename,
            filename_m=filename,
            timestamp=fake.date_time_this_year(),
            author=User.query.get(random.randint(1, User.query.count()))
        )

        # 为图片添加标签
        for j in range(random.randint(1, 5)):
            tag = Tag.query.get(random.randint(1, Tag.query.count()))
            if tag not in photo.tags:
                photo.tags.append(tag)
        db.session.add(photo)
    db.session.commit()


def fake_collect(count=50):
    """虚拟收藏"""
    for i in range(count):
        user = User.query.get(random.randint(1, User.query.count()))
        user.collect(Photo.query.get(random.randint(1, Photo.query.count())))
    db.session.commit()


def fake_comment(count=100):
    """虚拟评论"""
    for i in range(count):
        comment = Comment(
            author=User.query.get(random.randint(1, User.query.count())),
            body=fake.sentence(),
            timestamp=fake.date_time_this_year(),
            photo=Photo.query.get(random.randint(1, Photo.query.count()))
        )
        db.session.add(comment)
    db.session.commit()
