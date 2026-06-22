# ========== Windows/Android 跨平台适配头部（无外部字体依赖） ==========
import os
import sys
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

LOOT_CACHE = os.path.join(APP_STORAGE, "loot_cache.json")
PRICE_CACHE = os.path.join(APP_STORAGE, "price_cache.json")

# 高分屏配置
os.environ["KIVY_METRICS_DENSITY"] = "1"
os.environ["KIVY_NO_ARGS"] = "1"

import requests
import time
import json
import threading
from functools import partial
from typing import Dict, List, Optional, Tuple
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

# ====================== 字体：纯系统自带，不需要msyh.ttc ======================
FONT_NAME = "sys_cn"
font_ok = False
if ANDROID:
    # 安卓系统自带Roboto，自带中文渲染
    try:
        LabelBase.register(name=FONT_NAME, fn_regular="/system/fonts/Roboto-Regular.ttf")
        font_ok = True
    except:
        pass
else:
    # Windows系统自带微软雅黑，无需外部文件
    try:
        LabelBase.register(name=FONT_NAME, fn_regular=r"C:/Windows/Fonts/msyh.ttc")
        font_ok = True
    except:
        pass

# 兜底：使用Kivy默认字体（会有方框，但程序不崩溃）
if not font_ok:
    FONT_NAME = "Roboto"

Config.set('kivy', 'default_font', [FONT_NAME, "", "", ""])
# 安卓强制竖屏锁定
Config.set('graphics', 'orientation', 'portrait')
Config.set('graphics', 'resizable', '0')
Window.softinput_mode = "below_target"

# ========== 业务全局配置 ==========
SORT_ASC = False
PAGE_LIMIT = 1
SORT_RULE = "price_asc"
SINGLE_ITEM_INTERVAL = 3.0
RETRY_TIMES = 3
TIMEOUT = 30
CACHE_EXPIRE_SEC = 1800
LOOT_CACHE_PATH = LOOT_CACHE
PRICE_CACHE_PATH = PRICE_CACHE

MARKET_API = "https://api.darkerdb.com/v1/market"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0.0.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
}

# ========== 工具函数 ==========
def safe_request(url: str, params: dict) -> Optional[dict]:
    for _ in range(RETRY_TIMES):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            time.sleep(2)
    return None

def load_loot_mapping() -> Dict[str, str]:
    if not os.path.exists(LOOT_CACHE_PATH):
        return {}
    with open(LOOT_CACHE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def cache_is_valid() -> bool:
    if not os.path.exists(PRICE_CACHE_PATH):
        return False
    file_modify = os.path.getmtime(PRICE_CACHE_PATH)
    return (time.time() - file_modify) < CACHE_EXPIRE_SEC

def save_price_cache(data: List[Tuple[str, str, int]]):
    cache_body = {"update_time": time.time(), "price_list": data}
    with open(PRICE_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache_body, f, ensure_ascii=False, indent=2)

def load_price_cache() -> List[Tuple[str, str, int]]:
    with open(PRICE_CACHE_PATH, "r", encoding="utf-8") as f:
        return json.load(f).get("price_list", [])

def query_single_min_price(archetype_id: str) -> Optional[int]:
    params = {"archetype": archetype_id, "sort": SORT_RULE, "limit": PAGE_LIMIT, "condense": True}
    resp_data = safe_request(MARKET_API, params)
    if not resp_data:
        return None
    item_list = resp_data.get("body", [])
    if not item_list:
        return None
    price = item_list[0].get("price", 0)
    return price if price > 0 else None

def batch_query_all(loot_map: Dict[str, str], update_text_cb) -> tuple[List[Tuple[str, str, int]], List[Tuple[str, str]]]:
    total = len(loot_map)
    priced = []
    no_stock = []
    index = 1
    item_list = list(loot_map.items())
    for item_id, name in item_list:
        update_text_cb(f"正在查询 {index}/{total}：{name}")
        min_price = query_single_min_price(item_id)
        if min_price is not None:
            priced.append((item_id, name, min_price))
        else:
            no_stock.append((item_id, name))
        index += 1
        time.sleep(SINGLE_ITEM_INTERVAL)
    priced.sort(key=lambda x: x[2], reverse=not SORT_ASC)
    return priced, no_stock

# ===================== 圆角卡片组件 =====================
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
        # 底层全屏深色背景
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

        # 分区标题
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

        # 刷新卡片水平居中容器
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
            text="重新拉取全道具实时最低售价，缓存30分钟",
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
        line1 = Label(size_hint_y=None, height=dp(1), color=(0.3,0.3,0.3,1))
        self.add_widget(line1)

        # 有价道具区域（占比放大）
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

        # 分割线
        line2 = Label(size_hint_y=None, height=dp(1), color=(0.3,0.3,0.3,1))
        self.add_widget(line2)

        # 无挂单道具（缩小占比）
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
            text="市场价格查询中",
            size_hint_y=None,
            height=dp(32),
            font_size=dp(16),
            font_name=FONT_NAME,
            color=(1,1,1,1)
        )
        self.pop_label = Label(
            text="初始化中...",
            font_size=dp(14),
            font_name=FONT_NAME,
            color=(0.9,0.9,0.9,1),
            size_hint_y=None,
            height=dp(30)
        )
        pop_root.add_widget(pop_title)
        pop_root.add_widget(self.pop_label)
        self.load_popup = Popup(
            content=pop_root,
            size_hint=(0.92, 0.35),
            title="",
            background_color=(0.15,0.15,0.15,1)
        )
        self.load_popup.open()

    def update_pop_text(self, text):
        self.pop_label.text = text

    def close_pop(self):
        self.load_popup.dismiss()

    def render_ui_data(self, priced_data: list, nostock_data: list):
        self.clear_all_list()
        # 有价道具卡片行
        for idx, (_, name, price) in enumerate(priced_data, 1):
            item_card = CardBox(size_hint_y=None, height=dp(44), padding=[dp(12),dp(8)])
            row_grid = GridLayout(cols=3, size_hint_y=None, height=dp(28))
            idx_lab = Label(text=f"{idx:03d}", font_name=FONT_NAME, color=(0.7,0.7,0.7,1), size_hint_x=0.1)
            name_lab = Label(text=name, font_name=FONT_NAME, color=(1,1,1,1), halign="left", size_hint_x=0.6)
            price_lab = Label(text=f"{price} 金币", font_name=FONT_NAME, color=(0.45,0.7,0.95,1), size_hint_x=0.3)
            row_grid.add_widget(idx_lab)
            row_grid.add_widget(name_lab)
            row_grid.add_widget(price_lab)
            item_card.add_widget(row_grid)
            self.box_priced.add_widget(item_card)
        # 无货道具卡片行
        for idx, (_, name) in enumerate(nostock_data, 1):
            item_card = CardBox(size_hint_y=None, height=dp(44), padding=[dp(12),dp(8)])
            row_grid = GridLayout(cols=2, size_hint_y=None, height=dp(28))
            idx_lab = Label(text=f"{idx:03d}", font_name=FONT_NAME, color=(0.6,0.6,0.6,1), size_hint_x=0.1)
            name_lab = Label(text=name, font_name=FONT_NAME, color=(0.8,0.8,0.8,1), halign="left", size_hint_x=0.9)
            row_grid.add_widget(idx_lab)
            row_grid.add_widget(name_lab)
            item_card.add_widget(row_grid)
            self.box_nostock.add_widget(item_card)

    def _finish_render(self, dt, priced, nostock):
        self.close_pop()
        self.render_ui_data(priced, nostock)

    def start_refresh_task(self, touch):
        loot_dict = load_loot_mapping()
        if not loot_dict:
            err_root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10), size_hint_y=None)
            err_root.bind(minimum_height=err_root.setter("height"))
            err_title = Label(text="文件缺失", font_size=dp(16), font_name=FONT_NAME, color=(1,1,1,1), size_hint_y=None, height=dp(30))
            err_text = Label(text="应用目录缺少道具数据文件", font_name=FONT_NAME, color=(0.85,0.85,0.85,1), size_hint_y=None, height=dp(30))
            err_root.add_widget(err_title)
            err_root.add_widget(err_text)
            err_pop = Popup(content=err_root, size_hint=(0.8, 0.3), title="", background_color=(0.15,0.15,0.15,1))
            err_pop.open()
            return
        self.show_loading_pop()
        def query_work():
            if cache_is_valid():
                self.update_pop_text("读取本地30分钟缓存...")
                priced_result = load_price_cache()
                all_item_ids = set(loot_dict.keys())
                priced_ids_set = set(i[0] for i in priced_result)
                nostock_result = [(k, v) for k, v in loot_dict.items() if k not in priced_ids_set]
            else:
                priced_result, nostock_result = batch_query_all(loot_dict, self.update_pop_text)
                save_price_cache(priced_result)
            Clock.schedule_once(partial(self._finish_render, priced=priced_result, nostock=nostock_result), 0)
        work_thread = threading.Thread(target=query_work, daemon=True)
        work_thread.start()

# ========== APP入口（固定窄窗口，不会变宽） ==========
class DarkPriceApp(App):
    def build(self):
        # 固定竖屏窄窗口，恢复原来尺寸，不会自动加宽
        Window.size = (dp(380), dp(760))
        self.title = "战利品市场价格查询"
        return MainBox()

if __name__ == "__main__":
    DarkPriceApp().run()