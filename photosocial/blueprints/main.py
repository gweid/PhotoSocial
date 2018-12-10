import os

from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, \
    current_app, send_from_directory
from flask_login import current_user, login_required
from sqlalchemy.sql.expression import func

from photosocial.extensions import db
from photosocial.models import Photo, Tag, Comment, Collect, Notification, Follow, User
from photosocial.decorators import permission_required, confirm_required
from photosocial.utils import rename_image, resize_image, redirect_back, flash_errors
from photosocial.forms.main import DescriptionForm, TagForm, CommentForm
from photosocial.notifications import push_collect_notification, push_comment_notification

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        page = request.args.get('page', 1, type=int)
        per_page = current_app.config['PHOTOSOCIAL_PHOTO_PER_PAGE']
        # .join()联结查询
        pagination = Photo.query \
            .join(Follow, Follow.followed_id == Photo.author_id) \
            .filter(Follow.follower_id == current_user.id) \
            .order_by(Photo.timestamp.desc()) \
            .paginate(page, per_page)
        photos = pagination.items
    else:
        pagination = None
        photos = None
    tags = Tag.query.join(Tag.photos).group_by(Tag.id).order_by(func.count(Photo.id).desc()).limit(10)
    return render_template('main/index.html', pagination=pagination, photos=photos, tags=tags, Collect=Collect)


@main_bp.route('/explore')
def explore():
    """发现界面"""
    photos = Photo.query.order_by(func.random()).limit(9)
    return render_template('main/explore.html', photos=photos)


@main_bp.route('/about')
def about():
    """关于界面"""
    return render_template('main/about.html')


@main_bp.route('/upload', methods=['GET', 'POST'])
@login_required  # 验证登陆状态
@permission_required('UPLOAD')  # 验证权限
def upload():
    """上传图片"""
    if request.method == 'POST' and 'file' in request.files:
        f = request.files.get('file')  # 获取文件图片对象
        filename = rename_image(f.filename)  # 生成随机文件名
        f.save(os.path.join(current_app.config['PHOTOSOCIAL_UPLOAD_PATH'], filename))  # 保存图片
        filename_s = resize_image(f, filename, current_app.config['PHOTOSOCIAL_PHOTO_SIZE']['small'])
        filename_m = resize_image(f, filename, current_app.config['PHOTOSOCIAL_PHOTO_SIZE']['medium'])
        photo = Photo(
            filename=filename,
            filename_s=filename_s,
            filename_m=filename_m,
            author=current_user._get_current_object()
        )
        db.session.add(photo)
        db.session.commit()
    return render_template('main/upload.html')


@main_bp.route('/avatars/<path:filename>')
def get_avatar(filename):
    """获取头像"""
    return send_from_directory(current_app.config['AVATARS_SAVE_PATH'], filename)


@main_bp.route('/image/<path:filename>')
def get_image(filename):
    """获取图片"""
    return send_from_directory(current_app.config['PHOTOSOCIAL_UPLOAD_PATH'], filename)


@main_bp.route('/photo/<int:photo_id>')
def show_photo(photo_id):
    """展示图片"""
    photo = Photo.query.get_or_404(photo_id)

    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['PHOTOSOCIAL_COMMENT_PER_PAGE']
    pagination = Comment.query.with_parent(photo).order_by(Comment.timestamp.desc()).paginate(page, per_page)
    comments = pagination.items

    # 图片描述
    description_form = DescriptionForm()
    description_form.description.data = photo.description

    tag_form = TagForm()
    comment_form = CommentForm()

    return render_template('main/photo.html', photo=photo, comments=comments, description_form=description_form,
                           tag_form=tag_form, comment_form=comment_form, pagination=pagination)


@main_bp.route('/photo/n/<int:photo_id>')
def photo_next(photo_id):
    """下一张图片"""
    photo = Photo.query.get_or_404(photo_id)
    photo_n = Photo.query.with_parent(photo.author).filter(Photo.id < photo_id).order_by(Photo.id.desc()).first()
    if photo_n is None:
        flash('已经是最后一张图片', 'info')
        return redirect(url_for('main.show_photo', photo_id=photo.id))
    return redirect(url_for('main.show_photo', photo_id=photo_n.id))


@main_bp.route('/photo/p/<int:photo_id>')
def photo_previous(photo_id):
    """上一张图片"""
    photo = Photo.query.get_or_404(photo_id)
    photo_p = Photo.query.with_parent(photo.author).filter(Photo.id > photo_id).order_by(Photo.id.asc()).first()
    if photo_p is None:
        flash('已经是第一张了', 'info')
        return redirect(url_for('main.show_photo', photo_id=photo.id))
    return redirect(url_for('main.show_photo', photo_id=photo_p.id))


@main_bp.route('/delete/photo/<int:photo_id>', methods=['POST'])
@login_required
def delete_photo(photo_id):
    """删除图片"""
    photo = Photo.query.get_or_404(photo_id)
    if current_user != photo.author and not current_user.can('MODERATE'):
        abort(403)  # 如果不是作者本人或者不拥有管理员权限，则返回（403）错误

    db.session.delete(photo)
    db.session.commit()
    flash('图片删除', 'info')

    photo_n = Photo.query.with_parent(photo.author).filter(Photo.id < photo_id).order_by(Photo.id.desc()).first()
    if request.args.get('candelete') == 'photo':
        return redirect(url_for('user.index', username=photo.author.username))
    else:
        if photo_n is None:  # 如果没有下一张图片则寻找上一张
            photo_p = Photo.query.with_parent(photo.author).filter(Photo.id > photo_id).order_by(Photo.id.asc()).first()
            if photo_p is None:  # 如果没有上一张，返回用户主页
                return redirect(url_for('user.index', username=photo.author.username))
            return redirect(url_for('main.show_photo', photo_id=photo_p.id))
        return redirect(url_for('main.show_photo', photo_id=photo_n.id))


@main_bp.route('/report/photo/<int:photo_id>', methods=['POST'])
@login_required
@confirm_required
def report_photo(photo_id):
    """举报图片函数"""
    photo = Photo.query.get_or_404(photo_id)
    photo.flag += 1
    db.session.commit()
    flash('举报成功', 'success')
    return redirect(url_for('main.show_photo', photo_id=photo.id))


@main_bp.route('/photo/<int:photo_id>/description', methods=['GET', 'POST'])
@login_required
def edit_description(photo_id):
    """编辑图片描述"""
    photo = Photo.query.get_or_404(photo_id)
    if current_user != photo.author and not current_user.can('MODERATE'):
        abort(403)

    form = DescriptionForm()
    if form.validate_on_submit():
        photo.description = form.description.data
        db.session.commit()
        flash('图片描述更新成功', 'success')

    flash_errors(form)
    return redirect(url_for('main.show_photo', photo_id=photo.id))


@main_bp.route('/photo/<int:photo_id>/tag/new', methods=['POST'])
@login_required
def new_tag(photo_id):
    """添加标签"""
    photo = Photo.query.get_or_404(photo_id)
    if current_user != photo.author:
        abort(403)

    form = TagForm()
    if form.validate_on_submit():
        for name in form.tag.data.split():
            tag = Tag.query.filter_by(name=name).first()
            if tag is None:  # 如果标签不存在，则添加
                tag = Tag(name=name)
                db.session.add(tag)
                db.session.commit()
            if tag not in photo.tags:
                photo.tags.append(tag)
                db.session.commit()
        flash('标签添加成功', 'success')

    flash_errors(form)
    return redirect(url_for('main.show_photo', photo_id=photo.id))


@main_bp.route('/delete/tag/<int:photo_id>/<int:tag_id>', methods=['POST'])
@login_required
def delete_tag(photo_id, tag_id):
    """删除标签"""
    photo = Photo.query.get_or_404(photo_id)
    tag = Tag.query.get_or_404(tag_id)
    if current_user != photo.author:
        abort(403)

    # 这里只是删除图片与标签的关联，不会从数据库删除标签
    photo.tags.remove(tag)
    db.session.commit()

    # 如果标签不再与任何图片关联，则删除标签
    if not tag.photos:
        db.session.delete(tag)
        db.session.commit()

    flash('标签已删除', 'success')
    return redirect(url_for('main.show_photo', photo_id=photo.id))


@main_bp.route('/tag/<int:tag_id>', defaults={'order': 'by_time'})
@main_bp.route('/tag/<int:tag_id>/<order>')
def show_tag(tag_id, order):
    """展示标签"""
    tag = Tag.query.get_or_404(tag_id)
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['PHOTOSOCIAL_PHOTO_PER_PAGE']
    pagination = Photo.query.with_parent(tag).order_by(Photo.timestamp.desc()).paginate(page, per_page)
    photos = pagination.items
    order_rule = '按时间排序'  # 排序规则

    if order == 'by_collects':
        photos.sort(key=lambda x: len(x.collectors), reverse=True)
        order_rule = '按收藏排序'
    return render_template('main/tag.html', tag=tag, photos=photos, pagination=pagination, order_rule=order_rule)


@main_bp.route('/report/comment/<int:comment_id>', methods=['POST'])
@login_required
@confirm_required
def report_comment(comment_id):
    """举报评论"""
    comment = Comment.query.get_or_404(comment_id)
    comment.flag += 1
    db.session.commit()
    flash('评论举报成功', 'success')
    return redirect(url_for('main.show_photo', photo_id=comment.photo_id))


@main_bp.route('/photo/<int:photo_id>/comment/new', methods=['POST'])
@login_required
@permission_required('COMMENT')
def new_comment(photo_id):
    """新建评论"""
    photo = Photo.query.get_or_404(photo_id)
    page = request.args.get('page', 1, type=int)
    form = CommentForm()
    if form.validate_on_submit():
        body = form.body.data
        author = current_user._get_current_object()
        comment = Comment(body=body, author=author, photo=photo)

        replied_id = request.args.get('reply')
        if replied_id:  # 如果得到参数'reply'，则说明是回复
            comment.replied = Comment.query.get_or_404(replied_id)
            if comment.replied.author.receive_comment_notification:
                push_comment_notification(photo_id=photo.id, receiver=comment.replied.author)
        db.session.add(comment)
        db.session.commit()
        flash('评论成功', 'success')

        if current_user != photo.author and photo.author.receive_comment_notification:
            push_comment_notification(photo_id, receiver=photo.author, page=page)

    flash_errors(form)
    return redirect(url_for('main.show_photo', photo_id=photo.id, page=page) + '#comments')


@main_bp.route('/set-comment/<int:photo_id>', methods=['POST'])
@login_required
@confirm_required
def set_comment(photo_id):
    """开启或者关闭评论"""
    photo = Photo.query.get_or_404(photo_id)
    if current_user != photo.author:
        abort(403)

    if photo.can_comment:
        photo.can_comment = False
        flash('评论关闭', 'info')
    else:
        photo.can_comment = True
        flash('评论开启', 'success')
    db.session.commit()
    return redirect(url_for('main.show_photo', photo_id=photo.id))


@main_bp.route('/reply/comment/<comment_id>')
@login_required
@permission_required('COMMENT')
def reply_comment(comment_id):
    """回复"""
    comment = Comment.query.get_or_404(comment_id)
    return redirect(
        url_for('main.show_photo', photo_id=comment.photo_id, reply=comment_id,
                author=comment.author.name) + '#comment-form')


@main_bp.route('/delete/comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    """删除评论"""
    comment = Comment.query.get_or_404(comment_id)
    if current_user != comment.author and current_user != comment.photo.author and not current_user.can('MODERATE'):
        abort(403)
    db.session.delete(comment)
    db.session.commit()
    flash('评论已删除', 'success')
    return redirect(url_for('main.show_photo', photo_id=comment.photo_id))


@main_bp.route('/collect/<int:photo_id>', methods=['POST'])
@login_required
@permission_required('COLLECT')
def collect(photo_id):
    """收藏"""
    photo = Photo.query.get_or_404(photo_id)
    if current_user.is_collecting(photo):
        flash('图片已经收藏过.', 'info')
        return redirect(url_for('main.show_photo', photo_id=photo_id))

    current_user.collect(photo)
    if current_user != photo.author and photo.author.receive_collect_notification:
        push_collect_notification(collector=current_user, photo_id=photo_id, receiver=photo.author)
    return redirect_back()


@main_bp.route('/uncollect/<int:photo_id>', methods=['POST'])
@login_required
def uncollect(photo_id):
    """取消收藏"""
    photo = Photo.query.get_or_404(photo_id)
    if not current_user.is_collecting(photo):
        flash('没有收藏过图片.', 'info')
        return redirect(url_for('main.show_photo', photo_id=photo_id))

    current_user.uncollect(photo)
    return redirect_back()


@main_bp.route('/photo/<int:photo_id>/collectors')
def show_collectors(photo_id):
    """展示收藏者"""
    photo = Photo.query.get_or_404(photo_id)
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['PHOTOSOCIAL_USER_PER_PAGE']
    pagination = Collect.query.with_parent(photo).order_by(Collect.timestamp.asc()).paginate(page, per_page)
    collects = pagination.items
    return render_template('main/collectors.html', collects=collects, photo=photo, pagination=pagination)


@main_bp.route('/notifications')
def show_notifications():
    """展示消息通知"""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['PHOTOSOCIAL_NOTIFICATION_PER_PAGE']
    notifications = Notification.query.with_parent(current_user)
    filter_rule = request.args.get('filter')
    if filter_rule == 'unread':
        notifications = notifications.filter_by(is_read=False)

    pagination = notifications.order_by(Notification.timestamp.desc()).paginate(page, per_page)
    notifications = pagination.items
    return render_template('main/notifications.html', notifications=notifications, pagination=pagination)


@main_bp.route('/notification/read/<int:notification_id>', methods=['POST'])
@login_required
def read_notification(notification_id):
    """将未读消息标记为已读"""
    notification = Notification.query.get_or_404(notification_id)
    if current_user != notification.receiver:
        return abort(403)
    notification.is_read = True
    db.session.commit()
    flash('标记为已读', 'success')
    return redirect(url_for('main.show_notifications'))


@main_bp.route('/notifications/read/all', methods=['POST'])
@login_required
def read_all_notification():
    """将全部消息标记为已读"""
    for notification in current_user.notifications:
        notification.is_read = True
    db.session.commit()
    flash('全部标记为已读', 'success')
    return redirect(url_for('main.show_notifications'))


@main_bp.route('/search')
def search():
    """搜索"""
    q = request.args.get('q', '')
    if q == '':
        flash('请输入与图片、标签或者用户相关的信息', 'warning')
        return redirect_back()

    category = request.args.get('category', 'photo')
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['PHOTOSOCIAL_SEARCH_RESULT_PER_PAGE']
    if category == 'user':
        pagination = User.query.whooshee_search(q).paginate(page, per_page)
    elif category == 'tag':
        pagination = Tag.query.whooshee_search(q).paginate(page, per_page)
    else:
        pagination = Photo.query.whooshee_search(q).paginate(page, per_page)
    results = pagination.items
    return render_template('main/search.html', q=q, pagination=pagination, results=results, category=category)
