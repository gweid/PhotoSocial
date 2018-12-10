from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class DescriptionForm(FlaskForm):
    """图片描述表单"""
    description = TextAreaField('图片描述', validators=[Optional(), Length(0, 500)])
    submit = SubmitField('确定')


class TagForm(FlaskForm):
    tag = StringField('添加标签(使用空格分隔可以添加多个标签)', validators=[Optional(), Length(0, 64)])
    submit = SubmitField('确定')


class CommentForm(FlaskForm):
    body = TextAreaField('', validators=[DataRequired()])
    submit = SubmitField('确定')
