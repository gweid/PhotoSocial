"""存储装饰器"""
from functools import wraps

from flask import Markup, redirect, flash, url_for, abort
from flask_login import current_user


# 这个装饰器用来禁止未验证用户访问某些视图
def confirm_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.confirmed:
            message = Markup(
                '请验证您的帐号'
                '没有收到验证邮件？'
                '<a class="alert-link" href="%s">重新发送验证邮件</a>' % url_for('auth.resend_confirm_email')
            )
            flash(message, 'warning')
            return redirect(url_for('main.index'))
        return func(*args, **kwargs)

    return decorated_function


# 用来禁止没有权限的用户访问某些视图
def permission_required(permission_name):
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission_name):
                abort(403)
            return func(*args, **kwargs)

        return decorated_function

    return decorator


# 检查是否是管理员的装饰器
def admin_required(func):
    return permission_required('ADMINISTER')(func)
