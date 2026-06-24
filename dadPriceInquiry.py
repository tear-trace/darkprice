# -*- coding: utf-8 -*-
# ========== Windows/Android 跨平台适配头部（无外部字体依赖） ==========
import os
import sys
import time
import json
import threading
from functools import partial
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Kivy 环境检测
ANDROID = False
try:
    from android import mActivity
    ANDROID = True
except ImportError:
    pass

# 跨平台私有存储路径
if ANDROID:
    from android.storage import app_storage_path
    APP_STORAGE = app_storage_path()
else:
    APP_STORAGE = "./"

# 本地缓存文件（仅缓存云端拉取下来的完整价格数据）
PRICE_CACHE = os.path.join(APP_STORAGE, "price_cache.json")
# GitHub 云端价格文件直链，替换为你自己仓库地址
GITHUB_PRICE_URL = "https://raw.githubusercontent.com/tear-trace/darkprice/main/price_full.json"
# 缓存有效期 30分钟
CACHE_EXPIRE_SEC = 1800
TIMEOUT = 12

# Kivy高分屏配置
os.environ["KIVY_METRICS_DENSITY"] = "1"
os.environ["KIVY_NO_ARGS"] = "1"

import requests
from kivy.core.text import LabelBase
from kivy.config import Config
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle

# ====================== 字体兼容（纯系统自带，无外部ttc） ======================
FONT_NAME = "sys_cn"
font_ok = False
if ANDROID:
    try:
        LabelBase.register(name=FONT_NAME, fn_regular="/system/fonts/Roboto-Regular.ttf")
        font_ok = True
    except Exception:
        pass
else:
    try:
        LabelBase.register(name=FONT_NAME, fn_regular=r"C:/Windows/Fonts/msyh.ttc")
        font_ok = True
    except Exception:
        pass

if not font_ok:
    FONT_NAME = "Roboto"

Config.set('kivy', 'default_font', [FONT_NAME, "", "", ""])
Config.set('graphics', 'orientation', 'portrait')
Config.set('graphics', 'resizable', '0')
Window.softinput_mode = "below_target"

# ========== 网络工具：从GitHub拉取完整价格文件 ==========
def fetch_cloud_price() -> Optional[dict]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0.0.0"
    }
    try:
        resp = requests.get(GITHUB_PRICE_URL, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None

# ========== 缓存读写工具 ==========
def cache_is_valid() -> bool:
    if not os.path.exists(PRICE_CACHE):
        return False
    file_modify = os.path.getmtime(PRICE_CACHE)
    return (time.time() - file_modify) < CACHE_EXPIRE_SEC

def save_price_cache(cloud_json: dict):
    cache_body = {
        "local_save_ts": time.time(),
        "cloud_full_data": cloud_json
    }
    with open(PRICE_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache_body, f, ensure_ascii=False, indent=2)

def load_price_cache() -> Optional[dict]:
    if not os.path.exists(PRICE_CACHE):
        return None
    with open(PRICE_CACHE, "r", encoding="utf-8") as f:
        return json.load(f).get("cloud_full_data", None)

# ===================== UI组件：圆角卡片 =====================
class CardBox(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = dp(16)
        self.spacing = dp(8)
        self.size_hint_y = None
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            Color(0.17, 0.17, 0.17, 1)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=(dp(10), dp(10), dp(10), dp(10)))
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

# ===================== 主界面布局 =====================
class MainBox(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = dp(14)
        self.spacing = dp(16)
        # 全局深色背景
        with self.canvas.before:
            Color(0.10, 0.10, 0.10, 1)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=(0,0,0,0))
        self.bind(pos=self.update_bg, size=self.update_bg)

        # 顶部标题
        title_app = Label(
            text="战利品市场价格查询",
            size_hint_y=None,
            height=dp(40),
            font_size=dp(22),
            font_name=FONT_NAME,
            color=(1, 1, 1, 1),
            halign="center"
        )
        self.add_widget(title_app)

        # 云端数据更新时间展示
        self.time_label = Label(
            text="暂无价格数据",
            size_hint_y=None,
            height=dp(26),
            font_size=dp(13),
            font_name=FONT_NAME,
            color=(0.65, 0.75, 0.9, 1),
            halign="center"
        )
        self.add_widget(self.time_label)

        section_title_tool = Label(
            text="快速工具入口",
            size_hint_y=None,
            height=dp(30),
            font_size=dp(16),
            font_name=FONT_NAME,
            color=(0.9, 0.9, 0.9, 1),
            halign="center"
        )
        self.add_widget(section_title_tool)

        tool_center_box = BoxLayout(size_hint_y=None, size_hint_x=1)
        grid_tool = GridLayout(
            cols=1,
            spacing=dp(12),
            size_hint_y=None,
            size_hint_x=0.8,
            pos_hint={"center_x": 0.5}
        )
        grid_tool.bind(minimum_height=grid_tool.setter("height"))

        # 刷新按钮卡片
        card_refresh = CardBox(size_hint_y=None, height=dp(100))
        btn_refresh = Button(
            text="刷新市场价格",
            font_size=dp(16),
            font_name=FONT_NAME,
            background_color=(0.22, 0.35, 0.52, 1),
            size_hint_y=None,
            height=dp(44),
            halign="center"
        )
        btn_desc = Label(
            text="从GitHub云端拉取最新价目，本地缓存30分钟",
            font_size=dp(12),
            font_name=FONT_NAME,
            color=(0.75, 0.75, 0.75, 1),
            size_hint_y=None,
            height=dp(24),
            halign="center"
        )
        card_refresh.add_widget(btn_refresh)
        card_refresh.add_widget(btn_desc)
        btn_refresh.bind(on_press=self.start_refresh_task)
        grid_tool.add_widget(card_refresh)
        tool_center_box.add_widget(grid_tool)
        self.add_widget(tool_center_box)

        # 分割线
        line1 = Label(size_hint_y=None, height=dp(1), color=(0.3, 0.3, 0.3, 1))
        self.add_widget(line1)

        # 有价道具列表区域
        section_title_priced = Label(
            text="有价道具（价格由高至低）",
            size_hint_y=None,
            height=dp(30),
            font_size=dp(16),
            font_name=FONT_NAME,
            color=(0.9, 0.9, 0.9, 1),
            halign="center"
        )
        self.add_widget(section_title_priced)
        self.scroll_priced = ScrollView(size_hint_y=0.55)
        self.box_priced = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        self.box_priced.bind(minimum_height=self.box_priced.setter("height"))
        self.scroll_priced.add_widget(self.box_priced)
        self.add_widget(self.scroll_priced)

        line2 = Label(size_hint_y=None, height=dp(1), color=(0.3, 0.3, 0.3, 1))
        self.add_widget(line2)

        # 无挂单道具区域
        section_title_nostock = Label(
            text="当前无挂单道具",
            size_hint_y=None,
            height=dp(30),
            font_size=dp(16),
            font_name=FONT_NAME,
            color=(0.9, 0.9, 0.9, 1),
            halign="center"
        )
        self.add_widget(section_title_nostock)
        self.scroll_nostock = ScrollView(size_hint_y=0.30)
        self.box_nostock = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        self.box_nostock.bind(minimum_height=self.box_nostock.setter("height"))
        self.scroll_nostock.add_widget(self.box_nostock)
        self.add_widget(self.scroll_nostock)

        self.load_popup = None
        self.pop_label = None

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def clear_all_list(self):
        self.box_priced.clear_widgets()
        self.box_nostock.clear_widgets()

    def show_loading_pop(self):
        pop_root = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(16), size_hint_y=None)
        pop_root.bind(minimum_height=pop_root.setter("height"))
        pop_title = Label(
            text="正在拉取云端价格",
            size_hint_y=None,
            height=dp(32),
            font_size=dp(16),
            font_name=FONT_NAME,
            color=(1, 1, 1, 1)
        )
        self.pop_label = Label(
            text="连接GitHub云端...",
            font_size=dp(14),
            font_name=FONT_NAME,
            color=(0.9, 0.9, 0.9, 1),
            size_hint_y=None,
            height=dp(30)
        )
        pop_root.add_widget(pop_title)
        pop_root.add_widget(self.pop_label)
        self.load_popup = Popup(
            content=pop_root,
            size_hint=(0.92, 0.35),
            title="",
            background_color=(0.15, 0.15, 0.15, 1)
        )
        self.load_popup.open()

    def update_pop_text(self, text):
        self.pop_label.text = text

    def close_pop(self):
        self.load_popup.dismiss()

    def render_ui_data(self, cloud_data: dict):
        self.clear_all_list()
        priced_list = cloud_data.get("price_list", [])
        nostock_list = cloud_data.get("no_stock_list", [])
        update_time = cloud_data.get("update_time", "未知")
        valid_h = cloud_data.get("valid_hour", 0)
        self.time_label.text = f"云端数据更新时间：{update_time} | 有效期{valid_h}分钟"

        # 渲染有价道具
        for idx, item in enumerate(priced_list, 1):
            item_card = CardBox(size_hint_y=None, height=dp(44), padding=[dp(12), dp(8)])
            row_grid = GridLayout(cols=3, size_hint_y=None, height=dp(28))
            idx_lab = Label(text=f"{idx:03d}", font_name=FONT_NAME, color=(0.7, 0.7, 0.7, 1), size_hint_x=0.1)
            name_lab = Label(text=item["name"], font_name=FONT_NAME, color=(1, 1, 1, 1), halign="left", size_hint_x=0.6)
            price_lab = Label(text=f"{item['price']} 金币", font_name=FONT_NAME, color=(0.45, 0.7, 0.95, 1), size_hint_x=0.3)
            row_grid.add_widget(idx_lab)
            row_grid.add_widget(name_lab)
            row_grid.add_widget(price_lab)
            item_card.add_widget(row_grid)
            self.box_priced.add_widget(item_card)

        # 渲染无挂单道具
        for idx, item in enumerate(nostock_list, 1):
            item_card = CardBox(size_hint_y=None, height=dp(44), padding=[dp(12), dp(8)])
            row_grid = GridLayout(cols=2, size_hint_y=None, height=dp(28))
            idx_lab = Label(text=f"{idx:03d}", font_name=FONT_NAME, color=(0.6, 0.6, 0.6, 1), size_hint_x=0.1)
            name_lab = Label(text=item["name"], font_name=FONT_NAME, color=(0.8, 0.8, 0.8, 1), halign="left", size_hint_x=0.9)
            row_grid.add_widget(idx_lab)
            row_grid.add_widget(name_lab)
            item_card.add_widget(row_grid)
            self.box_nostock.add_widget(item_card)

    def _finish_load(self, dt, cloud_json):
        self.close_pop()
        if cloud_json is None:
            # 网络失败弹窗
            err_root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10), size_hint_y=None)
            err_root.bind(minimum_height=err_root.setter("height"))
            err_title = Label(text="拉取失败", font_size=dp(16), font_name=FONT_NAME, color=(1, 1, 1, 1), size_hint_y=None, height=dp(30))
            err_text = Label(text="无法连接GitHub云端，请检查网络", font_name=FONT_NAME, color=(0.85, 0.85, 0.85, 1), size_hint_y=None, height=dp(30))
            err_root.add_widget(err_title)
            err_root.add_widget(err_text)
            err_pop = Popup(content=err_root, size_hint=(0.8, 0.3), title="", background_color=(0.15, 0.15, 0.15, 1))
            err_pop.open()
            return
        # 渲染数据到界面
        self.render_ui_data(cloud_json)

    def start_refresh_task(self, touch):
        self.show_loading_pop()
        def load_work():
            # 优先读取有效本地缓存
            if cache_is_valid():
                self.update_pop_text("读取本地有效缓存...")
                cache_data = load_price_cache()
                Clock.schedule_once(partial(self._finish_load, cloud_json=cache_data), 0)
                return
            # 缓存过期/无缓存，拉取云端
            self.update_pop_text("请求GitHub云端价目...")
            cloud_data = fetch_cloud_price()
            if cloud_data is not None:
                save_price_cache(cloud_data)
            Clock.schedule_once(partial(self._finish_load, cloud_json=cloud_data), 0)
        threading.Thread(target=load_work, daemon=True).start()

# ========== APP入口 ==========
class DarkPriceApp(App):
    def build(self):
        Window.size = (dp(380), dp(760))
        self.title = "战利品市场价格查询"
        return MainBox()

if __name__ == "__main__":
    DarkPriceApp().run()