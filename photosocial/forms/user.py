from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, TextAreaField, PasswordField, BooleanField, SubmitField, HiddenField, ValidationError
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional, Regexp

from photosocial.models import User


class EditProfileForm(FlaskForm):
    """资料表单"""
    name = StringField('昵称', validators=[DataRequired(), Length(1, 30)])
    username = StringField('用户名', validators=[DataRequired(), Length(1.20),
                                              Regexp('^[a-zA-Z0-9]*$', message='应为大小写字母和数字')])
    website = StringField('站点', validators=[Optional(), Length(0, 255)])
    location = StringField('位置', validators=[Optional(), Length(0, 50)])
    bio = TextAreaField('简介', validators=[Optional(), Length(0, 120)])
    submit = SubmitField('确定')

    # 为支持用户名更改，需要查询是否重复
    def validate_username(self, field):
        if field.data != current_user.username:
            if User.query.filter_by(userbame=field.data).first():
                raise ValidationError('这个名字已被使用')


class UploadAvatarForm(FlaskForm):
    """上传头像"""
    image = FileField('上传头像(<= 3M)',
                      validators=[FileRequired(), FileAllowed(['jpg', 'png'], '图片应为.jpg或者.png格式')])
    submit = SubmitField('确定')


class CropAvatarForm(FlaskForm):
    """裁剪头像"""
    x = HiddenField()
    y = HiddenField()
    w = HiddenField()
    h = HiddenField()
    submit = SubmitField('裁剪更新')


class ChangePasswordForm(FlaskForm):
    """更换密码"""
    old_password = StringField('原始密码', validators=[DataRequired()])
    password = StringField('新密码', validators=[DataRequired(), Length(8, 128), EqualTo('password2')])
    password2 = StringField('重复密码', validators=[DataRequired()])
    submit = SubmitField('确定')


class ChangeEmailForm(FlaskForm):
    """更换邮箱"""
    email = StringField('新邮箱', validators=[DataRequired(), Length(1, 254), Email()])
    submit = SubmitField('确定')


class NotificationSettingForm(FlaskForm):
    """消息提醒设置"""
    receive_comment_notification = BooleanField('新评论')
    receive_follow_notification = BooleanField('新粉丝')
    receive_collect_notification = BooleanField('新收藏')
    submit = SubmitField('确定')


class PrivacySettingForm(FlaskForm):
    """隐私设置"""
    public_collections = BooleanField('公开收藏')
    submit = SubmitField('确定')


class DeleteAccountForm(FlaskForm):
    """删除帐户"""
    username = StringField('用户名', validators=[DataRequired(), Length(1, 20)])
    submit = SubmitField('确定')

    # 验证眼删除用户的用户名与原来用户名是否一致
    def validate_username(self, field):
        if field.data != current_user.userrname:
            raise ValidationError('用户名错误')
