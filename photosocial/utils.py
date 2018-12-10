"""存储辅助函数"""
import os
import uuid

import PIL
from PIL import Image
from urllib.parse import urlparse, urljoin
from flask import request, redirect, url_for, current_app, flash
from itsdangerous import BadSignature, SignatureExpired
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from photosocial.extensions import db
from photosocial.models import User
from photosocial.settings import Operations


def generate_token(user, operation, expire_in=None, **kwargs):
    """创建令牌"""
    s = Serializer(current_app.config['SECRET_KEY'], expire_in)
    data = {'id': user.id, 'operation': operation}
    data.update(**kwargs)
    return s.dumps(data)


def validate_token(user, token, operation, new_password=None):
    """验证令牌"""
    s = Serializer(current_app.config['SECRET_KEY'])

    try:
        data = s.loads(token)  # 从负载(Payload)中提取数据
    except (SignatureExpired, BadSignature):  # 分别表示签名过期和签名不匹配
        return False

    if operation != data.get('operation') or user.id != data.get('id'):
        return False

    if operation == Operations.CONFIRM:
        user.confirmed = True  # 认证
    elif operation == Operations.RESET_PASSWORD:
        user.set_pasword(new_password)  # 重置密码
    elif operation == Operations.CHANGE_EMAIL:  # 更换邮箱
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if User.query.filter_by(email=new_email).first() is not None:
            return False
        user.email = new_email
    else:
        return False

    db.session.commit()
    return True


def rename_image(old_filename):
    """对图片重命名"""
    ext = os.path.splitext(old_filename)[1]
    new_filename = uuid.uuid4().hex + ext
    return new_filename


def resize_image(image, filename, base_width):
    """图片尺寸"""
    filename, ext = os.path.splitext(filename)
    img = Image.open(image)
    if img.size[0] <= base_width:
        return filename + ext
    w_percent = (base_width / float(img.size[0]))
    h_size = int((float(img.size[1]) * float(w_percent)))
    img = img.resize((base_width, h_size), PIL.Image.ANTIALIAS)

    filename += current_app.config['PHOTOSOCIAL_PHOTO_SUFFIX'][base_width] + ext
    img.save(os.path.join(current_app.config['PHOTOSOCIAL_UPLOAD_PATH'], filename), optimize=True, quality=85)
    return filename


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def redirect_back(default='main.index', **kwargs):
    for target in request.args.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return redirect(target)
        return redirect(url_for(default, **kwargs))


def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                error
            ))
