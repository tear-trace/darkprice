[app]
title = 战利品价格查询
package.name = darkprice
package.domain = org.darkprice
source.main = dadPriceInquiry.py
source.dir = .
source.include_exts = py,png,json
version = 1.0
version.code = 1
icon.filename = icon.png
requirements = python3,kivy,certifi,chardet,idna,urllib3,requests
android.permissions = INTERNET,ACCESS_NETWORK_STATE
orientation = portrait
fullscreen = 0
android.minapi = 21
android.api = 33
android.ndk = 25
android.build_tools = "33.0.2"
output_dir = bin
debug = 0
# 路径改为【项目本地】的p4a文件夹，不再使用家目录
p4a.source_dir = ./.buildozer/android/platform/python-for-android