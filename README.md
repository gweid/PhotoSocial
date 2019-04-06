# MyBlog
--基于Python Flask与BootStrap搭建的图片分享网（学习）
------Python版本：3.6.3

# 使用方法：
## 1、安装集成Virtualenv的pipenv
pip install pipenv

## 2、进入文件夹 PhotoSocial

## 3、为当前项目创建虚拟环境
pipenv install --dev

## 4、激活虚拟环境
pipenv shell

## 5、为当前项目创建一些虚拟数据
flask forge

## 6、运行
flask run

注：默认生成的虚拟数据的虚拟管理员
虚拟初始管理员账号：admin@weidu.com 密码：weidu006

# 当不需要虚拟数据测试时，可以直接生成干净的博客界面
## 1、激活虚拟环境
pipenv shell

## 2、清空当前数据库
flask initdb --drop

## 3、创建管理员账号
flask init

## 4、运行
flask run
