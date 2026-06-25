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
android.permissions = INTERNET,ACCESS_NETWORK_STATE
orientation = portrait
fullscreen = 0
requirements = python3==3.12.7,kivy==2.2.1,certifi,chardet,idna,urllib3,requests
android.ndk = 26b
android.api = 33
android.minapi = 23          # 提高到23，提高 Python 3.12 兼容性
android.archs = arm64-v8a    # 仅编译64位，先保证通过
android.build_tools = "33.0.2"
output_dir = bin
debug = 0
p4a.source_dir = ./.buildozer/android/platform/python-for-android
android.accept_sdk_license = True