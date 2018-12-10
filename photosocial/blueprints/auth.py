from flask import Blueprint, redirect, url_for, flash, render_template
from flask_login import current_user, login_required, login_user, logout_user, login_fresh, confirm_login

from photosocial.emails import send_confirm_email, send_reset_password_email
from photosocial.forms.auth import RegisterForm, LoginForm, ForgetPasswordForm, ResetPasswordForm
from photosocial.models import User
from photosocial.extensions import db
from photosocial.utils import generate_token, validate_token, redirect_back
from photosocial.settings import Operations

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user is not None and user.validate_password(form.password.data):
            if login_user(user, form.remember_me.data):
                flash('登陆成功.', 'info')
                return redirect_back()
            else:
                flash('您的帐户被封禁了.', 'warning')
                return redirect(url_for('main.index'))
        flash('无效的邮箱或者密码.', 'warning')
    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('登出成功', 'success')
    return redirect(url_for('main.index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data.lower()  # 使用小写,避免同一个邮箱使用不同大小写注册
        username = form.username.data
        password = form.password.data
        user = User(name=name, email=email, username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        token = generate_token(user=user, operation='confirm')  # 创建令牌
        send_confirm_email(user=user, token=token)  # 发送验证邮件
        flash('验证邮件已发送，请检查你的收件箱', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@auth_bp.route('/confirm/<token>')
@login_required  # login_required 装饰器确保只有登陆的用户才可以访问对应的资源
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))

    if validate_token(user=current_user, token=token, operation=Operations.CONFIRM):
        flash('帐户认证成功', 'success')
        return redirect(url_for('main.index'))
    else:
        flash('无效或过期令牌', 'danger')
        return redirect(url_for('auth.resend_confirm_email'))  # 验证没通过,重定向到发送验证邮件的视图


@auth_bp.route('/resend-confirm-email')
@login_required
def resend_confirm_email():
    """发送验证邮件"""
    if current_user.cofirmed:
        return redirect(url_for('main.index'))

    token = generate_token(user=current_user, operation=Operations.CONFIRM)
    send_confirm_email(user=current_user, token=token)
    flash('新邮件已发送，请检查收件箱', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/forget-password', methods=['POST', 'GET'])
def forget_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = ForgetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            token = generate_token(user=user, operation=Operations.RESET_PASSWORD)
            send_reset_password_email(user=user, token=token)
            flash('密码重置邮件已发送，请检查您的收件箱', 'info')
            return redirect(url_for('auth.login'))
        flash('无效邮件', 'warning')
        return redirect(url_for('auth.forget_password'))
    return render_template('auth/reset_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = ResetPasswordForm()
    if form.validate_on_submit():  # 如果表单提交
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user is None:  # 判断这个邮箱是否存在
            return redirect(url_for('main.index'))

        if validate_token(user=user, token=token,
                          operation=Operations.RESET_PASSWORD, new_password=form.password.data):
            flash('密码已重置', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('无效或过期链接', 'danger')
            return redirect(url_for('auth.forget_password'))
    return render_template('auth/reset_password.html', form=form)


@auth_bp.route('/re-authenticate', methods=['GET', 'POST'])
@login_required
def re_authenticate():
    """当用户‘不新鲜’时访问带@fresh_login_required的视图时，重新认证"""
    if login_fresh():
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit() and current_user.validate_password(form.password.data):
        confirm_login()
        return redirect_back()
    return render_template('auth/login.html', form=form)
