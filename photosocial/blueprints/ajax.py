from flask import Blueprint, render_template, jsonify
from flask_login import current_user

from photosocial.models import User, Photo, Notification
from photosocial.notifications import push_collect_notification, push_follow_notification

ajax_bp = Blueprint('ajax', __name__)


@ajax_bp.route('/profile/<int:user_id>')
def get_profile(user_id):
    """返回用户资料"""
    user = User.query.get_or_404(user_id)
    return render_template('main/profile_popup.html', user=user)


@ajax_bp.route('/collectors-count/<int:photo_id>')
def collectors_count(photo_id):
    """图片收藏者数量"""
    photo = Photo.query.get_or_404(photo_id)
    count = len(photo.collectors)
    return jsonify(count=count)


@ajax_bp.route('/notifications-count')
def notifications_count():
    """未读消息数量"""
    if not current_user.is_authenticated:
        return jsonify(message='Login required.'), 403

    count = Notification.query.with_parent(current_user).filter_by(is_read=False).count()
    return jsonify(count=count)


@ajax_bp.route('/followers-count/<int:user_id>')
def followers_count(user_id):
    """粉丝数量"""
    user = User.query.get_or_404(user_id)
    count = user.followers.count() - 1  # 减去自己
    return jsonify(count=count)


@ajax_bp.route('/collect/<int:photo_id>', methods=['POST'])
def collect(photo_id):
    """收藏"""
    if not current_user.is_authenticated:
        return jsonify(message='请先登陆.'), 403
    if not current_user.confirmed:
        return jsonify(message='请先验证邮箱.'), 400
    if not current_user.can('COLLECT'):
        return jsonify(message='没有权限.'), 403

    photo = Photo.query.get_or_404(photo_id)
    if current_user.is_collecting(photo):
        return jsonify(message='已经收藏过.'), 400

    current_user.collect(photo)
    if current_user != photo.author and photo.author.receive_collect_notification:
        push_collect_notification(collector=current_user, photo_id=photo_id, receiver=photo.author)
    return jsonify(message='收藏成功.')


@ajax_bp.route('/uncollect/<int:photo_id>', methods=['POST'])
def uncollect(photo_id):
    """取消收藏"""
    if not current_user.is_authenticated:
        return jsonify(message='请先登陆.'), 403

    photo = Photo.query.get_or_404(photo_id)
    if not current_user.is_collecting(photo):
        return jsonify(message='没有收藏过.'), 400

    current_user.uncollect(photo)
    return jsonify(message='收藏取消.')


@ajax_bp.route('/follow/<username>', methods=['POST'])
def follow(username):
    """关注"""
    if not current_user.is_authenticated:
        return jsonify(message='请先登录.'), 403  # jsonify生成json相应格式，并返回提示消息
    if not current_user.confirmed:
        return jsonify(message='请先验证邮箱.'), 400
    if not current_user.can('FOLLOW'):
        return jsonify(message='没有权限.'), 403

    user = User.query.filter_by(username=username).first_or_404()
    if current_user.is_followed(user):
        return jsonify(message='已经关注过.'), 400

    current_user.follow(user)
    if user.receive_collect_notification:
        push_follow_notification(follower=current_user, receiver=user)
    return jsonify(message='关注成功.')


@ajax_bp.route('/unfollow/<username>', methods=['POST'])
def unfollow(username):
    """取消关注"""
    if not current_user.is_authenticated:
        return jsonify(message='请先登陆.'), 403

    user = User.query.filter_by(username=username).first_or_404()
    if not current_user.is_followed(user):
        return jsonify(message='还没有关注他/她.'), 400

    current_user.unfollow(user)
    return jsonify(message='关注取消.')
