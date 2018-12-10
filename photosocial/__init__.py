import os

import click
from flask import Flask, render_template
from flask_login import current_user
from flask_wtf.csrf import CSRFError

from photosocial.blueprints.admin import admin_bp
from photosocial.blueprints.auth import auth_bp
from photosocial.blueprints.ajax import ajax_bp
from photosocial.blueprints.main import main_bp
from photosocial.blueprints.user import user_bp
from photosocial.models import User, Photo, Tag, Follow, Comment, Collect, Notification
from photosocial.extensions import bootstrap, db, dropzone, mail, csrf, login_manager, moment, whooshee, avatars
from photosocial.settings import config
from photosocial.models import Role


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'development')

    app = Flask('photosocial')

    app.config.from_object(config[config_name])

    register_extensions(app)
    register_blueprints(app)
    register_commands(app)
    register_errorhandlers(app)
    register_shell_context(app)
    register_template_context(app)

    return app


def register_extensions(app):
    bootstrap.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    dropzone.init_app(app)
    moment.init_app(app)
    whooshee.init_app(app)
    avatars.init_app(app)
    csrf.init_app(app)


def register_blueprints(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(ajax_bp, url_prefix='/ajax')


def register_shell_context(app):
    @app.shell_context_processor
    def make_shell_context():
        return dict(db=db, User=User, Photo=Photo, Tag=Tag,
                    Follow=Follow, Collect=Collect, Comment=Comment,
                    Notification=Notification)


def register_template_context(app):
    @app.context_processor
    def make_template_context():
        if current_user.is_authenticated:
            notification_count = Notification.query.with_parent(current_user).filter_by(is_read=False).count()
        else:
            notification_count = None
        return dict(notification_count=notification_count)


def register_errorhandlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return render_template('errors/400.html'), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return render_template('errors/413.html'), 413

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return render_template('errors/400.html', description=e.description), 500


def register_commands(app):
    @app.cli.command()
    @click.option('--drop', is_flag=True, help='Create after drop.')
    def initdb(drop):
        if drop:
            click.confirm('此操作将删除数据库，是否继续？', abort=True)
            db.drop_all()
            click.echo('删除表.')
        db.create_all()
        click.echo('初始化数据库.')

    @app.cli.command()
    def init():
        click.echo('初始化数据库...')
        db.create_all()

        click.echo('初始化角色和权限...')
        Role.init_role()

        click.echo('完成.')

    @app.cli.command()
    @click.option('--user', default=10, help='用户数量，默认为10.')
    @click.option('--follow', default=30, help='关注数量，默认为30.')
    @click.option('--photo', default=30, help='图片数量，默认为30.')
    @click.option('--tag', default=20, help='标签数量，默认为20.')
    @click.option('--collect', default=50, help='收藏数量，默认为50.')
    @click.option('--comment', default=100, help='评论数量，默认为100.')
    def forge(user, follow, photo, tag, collect, comment):
        from photosocial.fakes import fake_admin, fake_comment, fake_follow, fake_photo, fake_tag, fake_user, \
            fake_collect

        db.drop_all()
        db.create_all()

        click.echo('初始化角色和权限...')
        Role.init_role()
        click.echo('生成管理员...')
        fake_admin()
        click.echo('生成 %d 用户...' % user)
        fake_user(user)
        click.echo('生成 %d 关注...' % follow)
        fake_follow(follow)
        click.echo('生成 %d 标签...' % tag)
        fake_tag(tag)
        click.echo('生成 %d 图片...' % photo)
        fake_photo(photo)
        click.echo('生成 %d 收藏...' % photo)
        fake_collect(collect)
        click.echo('生成 %d 评论...' % comment)
        fake_comment(comment)
        click.echo('完成.')
