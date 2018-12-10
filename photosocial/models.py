import os
from datetime import datetime

from flask import current_app
from flask_login import UserMixin
from flask_avatars import Identicon
from werkzeug.security import generate_password_hash, check_password_hash

from photosocial.extensions import db, whooshee

# 权限与角色多对多关联表
roles_permissions = db.Table('roles_permissions',
                             db.Column('role_id', db.Integer, db.ForeignKey('role.id')),
                             db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'))
                             )


class Permission(db.Model):
    """权限"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)
    roles = db.relationship('Role', secondary=roles_permissions, back_populates='permissions')


class Role(db.Model):
    """角色，权限与角色是多对多，角色与用户是一对多"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)
    permissions = db.relationship('Permission', secondary=roles_permissions, back_populates='roles')
    users = db.relationship('User', back_populates='role')

    @staticmethod
    def init_role():
        roles_permissions_map = {
            # 'Guest': [], 表示访客,不需要存储到数据库，所以注释掉
            # 'Blokced': [], 表示被封禁用户,不能登录,不需要存储到数据库，所以注释掉
            'Locked': ['FOLLOW', 'COLLECT'],  # 被锁定用户
            'User': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD'],  # 普通登陆用户
            'Moderator': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD', 'MODERATE'],  # 协助管理员
            'Administrator': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD', 'MODERATE', 'ADMINISTER']  # 超级管理员
        }
        for role_name in roles_permissions_map:
            role = Role.query.filter_by(name=role_name).first()
            if role is None:
                role = Role(name=role_name)
                db.session.add(role)
            role.permissions = []
            for permission_name in roles_permissions_map[role_name]:
                permission = Permission.query.filter_by(name=permission_name).first()
                if permission is None:
                    permission = Permission(name=permission_name)
                    db.session.add(permission)
                role.permissions.append(permission)
        db.session.commit()


class Collect(db.Model):
    """收藏关系关联模型"""
    collector_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    collected_id = db.Column(db.Integer, db.ForeignKey('photo.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    collector = db.relationship('User', back_populates='collections', lazy='joined')  # 收藏者,lazy='joined'表示预加载
    collected = db.relationship('Photo', back_populates='collectors', lazy='joined')  # 被收藏图片


class Follow(db.Model):
    """关注模型表"""
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)  # 关注者id
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)  # 被关注者id
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # 两个都指向user.id,所以用foreign_keys明确指定对应字段
    follower = db.relationship('User', foreign_keys=[follower_id], back_populates='following', lazy='joined')  # 我关注的
    followed = db.relationship('User', foreign_keys=[followed_id], back_populates='followers', lazy='joined')  # 关注我的


@whooshee.register_model('name', 'username')
class User(db.Model, UserMixin):
    """存储用户信息"""
    id = db.Column(db.Integer, primary_key=True)
    # 用户资料
    username = db.Column(db.String(20), index=True, unique=True)
    email = db.Column(db.String(254), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(30))
    website = db.Column(db.String(254))
    bio = db.Column(db.String(120))
    location = db.Column(db.String(50))
    member_since = db.Column(db.DateTime, default=datetime.utcnow)

    # 头像
    avatar_s = db.Column(db.String(64))
    avatar_m = db.Column(db.String(64))
    avatar_l = db.Column(db.String(64))
    avatar_raw = db.Column(db.String(64))  # 用户上传的头像原来的文件名

    # 用户状态
    confirmed = db.Column(db.Boolean, default=False)  # 邮箱是否已认证
    locked = db.Column(db.Boolean, default=False)  # 用户是否被锁定
    active = db.Column(db.Boolean, default=True)  # 用户是正常还是被封禁

    public_collections = db.Column(db.Boolean, default=True)  # 收藏是否公开可见
    receive_follow_notification = db.Column(db.Boolean, default=True)
    receive_comment_notification = db.Column(db.Boolean, default=True)
    receive_collect_notification = db.Column(db.Boolean, default=True)

    # 角色权限
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    role = db.relationship('Role', back_populates='users')

    photos = db.relationship('Photo', back_populates='author', cascade='all')  # 图片
    comments = db.relationship('Comment', back_populates='author', cascade='all')  # 评论
    collections = db.relationship('Collect', back_populates='collector', cascade='all')  # 收藏
    # 关注
    following = db.relationship('Follow', foreign_keys=[Follow.follower_id], back_populates='follower', lazy='dynamic',
                                cascade='all')
    followers = db.relationship('Follow', foreign_keys=[Follow.followed_id], back_populates='followed', lazy='dynamic',
                                cascade='all')
    notifications = db.relationship('Notification', back_populates='receiver', cascade='all')  # 消息

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        self.generate_avatar()
        self.follow(self)  # 自己关注自己，为了在用户关注动态中显示自己的动态，所以有必要设置自己关注自己
        self.set_role()

    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password)

    def validate_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)

    def set_role(self):
        """设置角色"""
        if self.role is None:
            # 如果注册的邮箱也与本地配置的管理员邮箱一致，则将其设置为管理员
            if self.email == current_app.config['PHOTOSOCIAL_ADMIN_EMAIL']:
                self.role = Role.query.filter_by(name='Administrator').first()
            else:  # 否则，都是普通用户
                self.role = Role.query.filter_by(name='User').first()
            db.session.commit()

    def generate_avatar(self):
        avatar = Identicon()
        filenames = avatar.generate(text=self.username)  # generate返回三个尺寸的头像文件的文件名，由小到大排列
        self.avatar_s = filenames[0]
        self.avatar_m = filenames[1]
        self.avatar_l = filenames[2]
        db.session.commit()

    def collect(self, photo):
        """收藏"""
        if not self.is_collecting(photo):
            collect = Collect(collector=self, collected=photo)
            db.session.add(collect)
            db.session.commit()

    def uncollect(self, photo):
        """取消收藏"""
        collect = Collect.query.with_parent(self).filter_by(collected_id=photo.id).first()
        if collect:
            db.session.delete(collect)
            db.session.commit()

    def is_collecting(self, photo):
        """判断是否收藏"""
        return Collect.query.with_parent(self).filter_by(collected_id=photo.id).first() is not None

    def follow(self, user):
        """关注"""
        if not self.is_followed(user):
            follow = Follow(follower=self, followed=user)
            db.session.add(follow)
            db.session.commit()

    def unfollow(self, user):
        """取消关注"""
        follow = self.following.filter_by(followed_id=user.id).first()
        if follow:
            db.session.delete(follow)
            db.session.commit()

    def is_followed(self, user):
        """判断是否关注"""
        if user.id is None:
            return False
        return self.following.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        """判断是否被关注"""
        return self.followers.filter_by(follower_id=user.id).first() is not None

    def lock(self):
        """用户锁定"""
        self.locked = True
        self.role = Role.query.filter_by(name='Locked').first()
        db.session.commit()

    def unlock(self):
        """解除用户锁定"""
        self.locked = False
        self.role = Role.query.filter_by(name='User').first()
        db.session.commit()

    @property
    def is_active(self):
        """为了禁止被封禁用户登陆，重写继承自UserMixin类中的is_active"""
        return self.active

    def block(self):
        """用户封禁"""
        self.active = False
        db.session.commit()

    def unblock(self):
        """解除用户封禁"""
        self.active = True
        db.session.commit()

    @property
    def is_admin(self):
        return self.role.name == 'Administrator'

    def can(self, permission_name):
        permission = Permission.query.filter_by(name=permission_name).first()
        return permission is not None and self.role is not None and permission in self.role.permissions


tagging = db.Table('tagging',
                   db.Column('photo_id', db.Integer, db.ForeignKey('photo.id')),
                   db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
                   )


@whooshee.register_model('description')
class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(500))  # 存储图片的描述
    filename = db.Column(db.String(64))
    filename_s = db.Column(db.String(64))
    filename_m = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    flag = db.Column(db.Integer, default=0)  # 存储被举报的次数
    can_comment = db.Column(db.Boolean, default=True)  # 开启或者关闭评论

    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User', back_populates='photos')

    tags = db.relationship('Tag', secondary=tagging, back_populates='photos')
    comments = db.relationship('Comment', back_populates='photo', cascade='all')
    collectors = db.relationship('Collect', back_populates='collected', cascade='all')


@whooshee.register_model('name')
class Tag(db.Model):
    """存储标签"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)

    photos = db.relationship('Photo', secondary=tagging, back_populates='tags')


class Comment(db.Model):
    """存储评论"""
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow(), index=True)
    flag = db.Column(db.Integer, default=0)  # 举报的次数

    photo_id = db.Column(db.Integer, db.ForeignKey('photo.id'))
    photo = db.relationship('Photo', back_populates='comments')

    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User', back_populates='comments')

    # 回复
    replied_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    replies = db.relationship('Comment', back_populates='replied', cascade='all')
    replied = db.relationship('Comment', back_populates='replies', remote_side=[id])


class Notification(db.Model):
    """存储消息"""
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    receiver = db.relationship('User', back_populates='notifications')


# 图片删除事件监听函数
@db.event.listens_for(Photo, 'after_delete', named=True)
def delete_photos(**kwargs):
    """这个是把保存到本地的图片删除，与删除数据库不一样"""
    target = kwargs['target']
    for filename in [target.filename, target.filename_s, target.filename_m]:
        if filename is not None:
            path = os.path.join(current_app.config['PHOTOSOCIAL_UPLOAD_PATH'], filename)
            if os.path.exists(path):  # 判断目标文件路径是否存在
                os.remove(path)


# 头像删除事件监听函数
@db.event.listens_for(User, 'after_delete', named=True)
def delete_avatars(**kwargs):
    target = kwargs['target']
    for filename in [target.avatar_s, target.avatar_m, target.avatar_l, target.avatar_raw]:
        if filename is not None:
            path = os.path.join(current_app.config['AVATARS_SAVE_PATH'], filename)
            if os.path.exists(path):
                os.remove(path)
