from threading import Thread

from flask import current_app, render_template
from flask_mail import Message

from photosocial.extensions import mail


def _send_async_mail(app, message):
    with app.app_context():
        mail.send(message)


def send_mail(to, subject, template, **kwargs):
    message = Message(current_app.config['PHOTOSOCIAL_MAIL_SUBJECT_PREFIX'] + subject, recipients=[to])
    message.body = render_template(template + '.txt', **kwargs)
    message.html = render_template(template + '.html', **kwargs)
    app = current_app._get_current_object()
    thr = Thread(target=_send_async_mail, args=[app, message])
    thr.start()
    return thr


# 发送验证邮件
def send_confirm_email(user, token, to=None):
    send_mail(subject='邮件验证', to=to or user.email, template='emails/confirm', user=user, token=token)


# 发送重置密码邮件
def send_reset_password_email(user, token):
    send_mail(subject='重置密码', to=user.eamil, template='emails/reset_password', user=user, token=token)
