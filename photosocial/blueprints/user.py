from flask import Blueprint, render_template, flash, redirect, current_app, request, url_for
from flask_login import login_required, current_user, logout_user, fresh_login_required

from photosocial.models import User, Photo, Collect
from photosocial.decorators import confirm_required, permission_required
from photosocial.utils import redirect_back, generate_token, validate_token, flash_errors
from photosocial.notifications import push_follow_notification
from photosocial.forms.user import EditProfileForm, ChangePasswordForm, ChangeEmailForm, NotificationSettingForm, \
    PrivacySettingForm, DeleteAccountForm, UploadAvatarForm, CropAvatarForm
from photosocial.extensions import db, avatars
from photosocial.settings import Operations
from photosocial.emails import send_confirm_email

user_bp = Blueprint('user', __name__)


@user_bp.route('/<username>')
def index(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user == current_user and user.locked:
        flash('您的账号已被锁定.', 'danger')

    if user == current_user and not user.active:
        logout_user()

    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['PHOTOSOCIAL_PHOTO_PER_PAGE']
    pagination = Photo.query.with_parent(user).order_by(Photo.timestamp.desc()).paginate(page, per_page)
    photos = pagination.items
    return render_template('user/index.html', user=user, pagination=pagination, photos=photos)


@user_bp.route('/<username>/collections')
def show_collections(username):
    """展示收藏"""
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['PHOTOSOCIAL_PHOTO_PER_PAGE']
    pagination = Collect.query.with_parent(user).order_by(Collect.timestamp.desc()).paginate(page, per_page)
    collects = pagination.items
    return render_template('user/collections.html', user=user, pagination=pagination, collects=collects)


@user_bp.route('/follow/<username>', methods=['POST'])
@login_required
@permission_required('FOLLOW')
def follow(username):
    """关注"""
    user = User.query.filter_by(username=username).first_or_404()
    if current_user.is_followed(user):
        flash('已经关注过', 'info')
        return redirect(url_for('user.index', username=username))
    current_user.follow(user)
    if user.receive_follow_notification:
        push_follow_notification(follower=current_user, receiver=user)
    return redirect_back()


@user_bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    """取消关注"""
    user = User.query.filter_by(username=username).first_or_404()
    if not current_user.is_followed(user):
        flash('没有关注他', 'info')
        return redirect(url_for('user.index', username=username))
    current_user.unfollow(user)
    return redirect_back()


@user_bp.route('/<username>/following')
def show_following(username):
    """展示关注的人"""
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['PHOTOSOCIAL_USER_PER_PAGE']
    pagination = user.following.paginate(page, per_page)
    follows = pagination.items
    return render_template('user/following.html', user=user, pagination=pagination, follows=follows)


@user_bp.route('/<username>/followers')
def show_followed(username):
    """展示粉丝"""
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['PHOTOSOCIAL_USER_PER_PAGE']
    pagination = user.followers.paginate(page, per_page)
    follows = pagination.items
    return render_template('user/followers.html', user=user, pagination=pagination, follows=follows)


@user_bp.route('/settings/profile', methods=['GET', 'POST'])
@login_required
@confirm_required
def edit_profile():
    """编辑资料"""
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.username = form.username.data
        current_user.website = form.website.data
        current_user.location = form.location.data
        current_user.bio = form.bio.data
        db.session.commit()
        flash('资料已更新', 'success')
        return redirect(url_for('user.index', username=current_user.username))
    form.name.data = current_user.name
    form.username.data = current_user.username
    form.website.data = current_user.website
    form.location.data = current_user.location
    form.bio.data = current_user.bio
    return render_template('user/settings/edit_profile.html', form=form)


@user_bp.route('/settings/avatar')
@login_required
@confirm_required
def change_avatar():
    """更换头像"""
    upload_form = UploadAvatarForm()
    crop_form = CropAvatarForm()
    return render_template('user/settings/change_avatar.html', upload_form=upload_form, crop_form=crop_form)


@user_bp.route('/settings/avatar/upload', methods=['POST'])
@login_required
@confirm_required
def upload_avatar():
    """上传头像"""
    form = UploadAvatarForm()
    if form.validate_on_submit():
        image = form.image.data  # 获取文件数据
        filename = avatars.save_avatar(image)  # avatars.save_avatar会自动处理文件名，并保存到配置变量AVATARS_SAVE_PATH路径下
        current_user.avatar_raw = filename  # 返回文件名
        db.session.commit()
        flash('图片上传成功，请裁剪', 'success')
    flash_errors(form)
    return redirect(url_for('user.change_avatar'))


@user_bp.route('/settings/avatar/crop', methods=['POST'])
@login_required
@confirm_required
def crop_avatar():
    """裁剪头像"""
    form = CropAvatarForm()
    if form.validate_on_submit():
        x = form.x.data
        y = form.y.data
        w = form.w.data
        h = form.h.data
        # avatars.crop_avatar会按照配置AVATARS_SIZE_TUPLE中的设置裁剪出三种尺寸的文件，然后按小到大排列
        filenames = avatars.crop_avatar(current_user.avatar_raw, x, y, w, h)
        current_user.avatar_s = filenames[0]
        current_user.avatar_m = filenames[1]
        current_user.avatar_l = filenames[2]
        db.session.commit()
        flash('头像更新成功', 'success')
    flash_errors(form)
    return redirect(url_for('user.change_avatar'))


@user_bp.route('/settings/change-password', methods=['GET', 'POST'])
@fresh_login_required   # 确保用户处于‘活跃’状态
@confirm_required
def change_password():
    """更换密码"""
    form = ChangePasswordForm()
    # 当表单通过验证并且旧密码也通过验证的时候
    if form.validate_on_submit() and current_user.validate_password(form.old_password.data):
        current_user.set_password(form.password.data)
        db.session.commit()
        flash('密码重置成功', 'success')
        return redirect(url_for('user.index', username=current_user.username))
    return render_template('user/settings/change_password.html', form=form)


@user_bp.route('/settings/change-email', methods=['GET', 'POST'])
@fresh_login_required
@confirm_required
def change_email_request():
    """发送更换邮箱验证邮件"""
    form = ChangeEmailForm()
    if form.validate_on_submit():
        # 创建令牌
        token = generate_token(user=current_user, operation=Operations.CHANGE_EMAIL, new_email=form.email.data.lower())
        send_confirm_email(to=form.email.data, user=current_user, token=token)
        flash('验证邮件已经发送，请查看邮箱', 'success')
        return redirect(url_for('user.index', username=current_user.username))
    return render_template('user/settings/change_email.html', form=form)


@user_bp.route('/change-email/<token>')
@login_required
@confirm_required
def change_email(token):
    """绑定新邮箱"""
    if validate_token(user=current_user, token=token, operation=Operations.CHANGE_EMAIL):
        flash('邮箱已更新', 'success')
        return redirect(url_for('user.index', userame=current_user.username))
    else:
        flash('无效或过期令牌', 'warning')
        return redirect(url_for('user.change_email_request'))


@user_bp.route('/settings/notification', methods=['GET', 'POST'])
@login_required
@confirm_required
def notification_setting():
    """消息提醒设置"""
    form = NotificationSettingForm()
    if form.validate_on_submit():
        current_user.receive_comment_notification = form.receive_comment_notification.data
        current_user.receive_collect_notification = form.receive_collect_notification.data
        current_user.receive_follow_notification = form.receive_follow_notification.data
        db.session.commit()
        flash('消息提醒设置已更新', 'success')
        return redirect(url_for('user.index', username=current_user.username))
    form.receive_collect_notification.data = current_user.receive_collect_notification
    form.receive_comment_notification.data = current_user.receive_comment_notification
    form.receive_follow_notification.data = current_user.receive_follow_notification
    return render_template('user/settings/edit_notification.html', form=form)


@user_bp.route('/settings/privacy', methods=['GET', 'POST'])
@login_required
@confirm_required
def privacy_setting():
    """收藏隐私"""
    form = PrivacySettingForm()
    if form.validate_on_submit():
        current_user.public_collections = form.public_collections.data
        db.session.commit()
        flash('收藏隐私更新', 'success')
        return redirect(url_for('user.index', username=current_user.username))
    form.public_collections.data = current_user.public_collections
    return render_template('user/settings/edit_privacy.html', form=form)


@user_bp.route('/settings/account/delete', methods=['GET', 'POST'])
@fresh_login_required
def delete_account():
    """删除帐户"""
    form = DeleteAccountForm()
    if form.validate_on_submit():
        db.session.delete(current_user._get_current_object())
        db.session.commit()
        flash('您是自由的，再见！', 'success')
        return redirect('main.index')
    return render_template('user/settings/delete_account.html', form=form)
