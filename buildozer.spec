[app]
# APP桌面名称
title = 战利品价格查询
# 唯一包名，不能中文/空格
package.name = darkprice
package.domain = org.darkprice
# 主程序
source.main = dadPriceInquiry.py
source.dir = .
source.include_exts = py,png,json
# 版本
version = 1.0
version.code = 1
# APP图标
icon.filename = icon.png
# Python依赖（requests必须，联网拉取GitHub价格）
requirements = python3,kivy,certifi,chardet,idna,urllib3,requests
# 安卓权限：必须开启网络
android.permissions = INTERNET,ACCESS_NETWORK_STATE
# 锁定竖屏
orientation = portrait
fullscreen = 0
# Android编译版本
android.minapi = 21
android.api = 33
android.ndk = 25
# 输出目录
output_dir = bin
# 关闭调试日志（Release包）
debug = 0