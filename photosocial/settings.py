import os
import sys

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

WIN = sys.platform.startswith('win')
if WIN:
    prefix = 'sqlite:///'
else:
    prefix = 'sqlite:////'


class Operations:
    CONFIRM = 'confirm'
    RESET_PASSWORD = 'reset-password'
    CHANGE_EMAIL = 'change-email'


class BaseConfig:
    PHOTOSOCIAL_ADMIN_EMAIL = os.getenv('PHOTOSOCIAL_ADMIN', 'admin@weidu.com')
    PHOTOSOCIAL_PHOTO_PER_PAGE = 12
    PHOTOSOCIAL_COMMENT_PER_PAGE = 15
    PHOTOSOCIAL_USER_PER_PAGE = 20
    PHOTOSOCIAL_NOTIFICATION_PER_PAGE = 20
    PHOTOSOCIAL_SEARCH_RESULT_PER_PAGE = 20
    PHOTOSOCIAL_MANAGE_PHOTO_PER_PAGE = 20
    PHOTOSOCIAL_MANAGE_USER_PER_PAGE = 30
    PHOTOSOCIAL_MANAGE_TAG_PER_PAGE = 50
    PHOTOSOCIAL_MANAGE_COMMENT_PER_PAGE = 30
    PHOTOSOCIAL_UPLOAD_PATH = os.path.join(basedir, 'uploads')  # 图片保存的位置
    PHOTOSOCIAL_MAIL_SUBJECT_PREFIX = '[维度图片社交]'

    PHOTOSOCIAL_PHOTO_SIZE = {'small': 400, 'medium': 800}  # 两种图片尺寸对应的大小
    PHOTOSOCIAL_PHOTO_SUFFIX = {  # 两种大小图片对应的文件名后缀
        PHOTOSOCIAL_PHOTO_SIZE['small']: '_s',
        PHOTOSOCIAL_PHOTO_SIZE['medium']: '_m',
    }

    # 头像相关配置
    AVATARS_SAVE_PATH = os.path.join(PHOTOSOCIAL_UPLOAD_PATH, 'avatars')
    AVATARS_SIZE_TUPLE = (30, 100, 200)

    SECRET_KEY = os.getenv('SECRET_KEY', 'secret string')

    # 上传文件大小超过3MB将返回413错误响应(服务器端)
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024

    BOOTSTRAP_SERVE_LOCAL = True

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # flask_mail配置
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_POST = 465
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = ('PHOTOSOCIAL_ADMIN', MAIL_USERNAME)

    # flask_dropzone配置
    DROPZONE_ALLOWED_FILE_TYPE = 'image'
    DROPZONE_MAX_FILE_SIZE = 3
    DROPZONE_MAX_FILES = 30
    DROPZONE_ENABLE_CSRF = True
    DROPZONE_DEFAULT_MESSAGE = '文件类型为图片，最多一次上传30张'

    # 全文搜索索引长度配置
    WHOOSHEE_MIN_STRING_LEN = 1


class DevelopmentConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = prefix + os.path.join(basedir, 'data-dev.db')
    REDIS_URL = "redis://localhost"


class ProductionConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', prefix + os.path.join(basedir, 'data.db'))


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}
