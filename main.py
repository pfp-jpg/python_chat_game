# ==========================================================
# game.py 整理版
# ※コードは消していません。順番の入れ替えとコメント追加だけです。
# ※「★」はバグ/要確認ポイント(動きは元のままにしてあります)
#
# 【全体の流れ】
#   1. 準備   : pygame初期化 → フォント/画像 → セーブ読込 → Wi-Fi確認 → 経過時間計算
#   2. ループ : (A)入力 → (B)更新 → (C)描画 → (D)拡大表示 を毎秒60回
#   3. 終了   : ウィンドウを閉じるとセーブして終わる
# ==========================================================


# ==========================================================
# 1. import
# ==========================================================
# いつもの
import pygame
import random      
import json
import os
import time       
import sys
from datetime import datetime
import urllib.request, urllib.parse   # 天気取得用(標準ライブラリ。requests から変更)
import asyncio          # ブラウザ版(pygbag)用
import atexit#更におニュー
import socket

# ブラウザ(WebAssembly)で動いているか
WEB = (sys.platform == "emscripten")
if WEB:
    import platform   # pygbag: JavaScript(localStorageなど)へのアクセス用


# ==========================================================
# 2. 画面のセットアップ
# ==========================================================
# セットアップ（画面サイズ+α）
VIRTUAL_W, VIRTUAL_H = 250, 122   # ゲーム内の画面サイズ(これを拡大して表示する)
pygame.init()
screen = pygame.display.set_mode((VIRTUAL_W, VIRTUAL_H), pygame.RESIZABLE)
virtual_surface = pygame.Surface((VIRTUAL_W, VIRTUAL_H))   # 描画は全部ここに行う
pygame.display.set_caption("Y")
clock = pygame.time.Clock()

def display_auto():
    # virtual_surface をウィンドウに合わせて拡大し、中央に表示する
    global scaled_w, scaled_h, offset_x, offset_y, scale
    win_w, win_h = screen.get_size()
    scale = min(win_w / VIRTUAL_W, win_h / VIRTUAL_H)
    scaled_w = int(VIRTUAL_W * scale)
    scaled_h = int(VIRTUAL_H * scale)
    scaled = pygame.transform.scale(virtual_surface, (scaled_w, scaled_h))
    offset_x = (win_w - scaled_w) // 2
    offset_y = (win_h - scaled_h) // 2
    screen.fill((255, 255, 255))
    screen.blit(scaled, (offset_x, offset_y))
    pygame.display.flip()


# ==========================================================
# 3. フォント・画像の読み込み
# ==========================================================
# セットアップ（フォント）
font_path = os.path.join("assets", "x12y12pxMaruMinya.ttf")
font_s = pygame.font.Font(font_path, 12)
font_m = pygame.font.Font(font_path, 24)

# 画像
txt_box_img = pygame.image.load(os.path.join("assets", "ui", "txt_box.png")).convert_alpha()
day_img = pygame.image.load(os.path.join("assets", "ui", "day.png")).convert_alpha()
night_img = pygame.image.load(os.path.join("assets", "ui", "night.png")).convert_alpha()
morning_img = pygame.image.load(os.path.join("assets", "ui", "morning.png")).convert_alpha()
noon_img = pygame.image.load(os.path.join("assets", "ui", "noon.png")).convert_alpha()


# ==========================================================
# 4. データ・設定値・状態変数
# ==========================================================

# ---------- 4-1. セリフ ----------
# テキスト
show_text="s"
talking = False

select_text_1 = [
    "撫でる",
    "食べ物を渡す",
    "雑談"
]

#スタート時の文
startup = {
    "low": {
        "morning" : ["おはようございます"],
        "day" : ["こんにちは"],
        "noon" : ["こんばんは"],
        "night" : ["こんばんは"],
        "sleep" : ["zzz...", "..."],
        "absence" : ["お久しぶりです"]
    },
    "mid" : {
        "morning" : ["おはよう", "おはよう..."],
        "day" : ["こんにちは", "こんにちは..."],
        "noon" : ["こんばんは","こんばんは..."],
        "night" : ["こんばんは","こんばんは..."],
        "sleep" : ["zzz...", "..."],
        "absence" : ["久しぶり"]
    },
    "high" : {
        "morning" : ["おはよ〜", "おはよ〜...","おはよ、あんまり良く眠れなかったかも..."],
        "day" : ["こんにちは", "こんにちは...", "こんにちは！"],
        "noon" : ["こんばんは","こんばんは...", "こんばんは!"],
        "night" : ["こんばんは","こんばんは...", "こんばんは〜"],
        "sleep" : ["zzz...", "...", "ムニャ..."],
        "absence" : ["久しぶり", "久しぶり！", "久しぶり！会いたかった！"],
        "absence_l" : ["久しぶり...", "...久しぶり", "..."]
    }
}

greet = {
    "low": {
        "morning": ["おはようございます"],
        "day":     ["こんにちは"],
        "noon":    ["こんにちは"],
        "night":   ["こんばんは"],
    },
    "mid": {
        "morning": ["おはよう", "おはよー"],
        "day":     ["こんにちは", "やあ"],
        "noon":    ["こんにちは", "おつかれ"],
        "night":   ["こんばんは", "こんばんはー"],
    },
    "high": {
        "morning": ["おはよ〜", "おはよう"],
        "day":     ["やっほー", "こんにちは"],
        "noon":    ["おかえり", "やっほー"],
        "night":   ["こんばんは〜", "おかえり"],
    },
}

sleep_line = {
    "low":  ["zzz...", "...", "すう...すう..."],
    "mid":  ["zzz...", "...", "すー...すー...", "んん..."],
    "high": ["zzz...", "...", "ムニャ...", "すぴー...", "んー...もうちょっと...", "えへへ...むにゃ..."],
}
 
weather_line = {
    "low": {
        "晴れ":       ["いい天気ですね", "晴れていて気持ちいいですね"],
        "くもり":     ["今日は曇りですね", "雲が多いですね"],
        "弱い雨":     ["小雨が降っていますね", "少し雨が降っていますね"],
        "中くらいの雨": ["雨が降っていますね。傘はお持ちですか", "けっこう降っていますね"],
        "強い雨":     ["強い雨ですね。気をつけてくださいね", "ひどい雨ですね。お出かけは控えめに"],
        "雪":         ["雪が降っていますね", "雪ですね。足元に気をつけてください"],
        "霧":         ["霧が出ていますね", "外が白っぽいですね"],
        "みぞれ":     ["みぞれですね。冷えますね", "みぞれが降っていますね"],
        "あられ":     ["あられが降っているみたいですね", "何か当たる音がしますね"],
        "雷":         ["雷が鳴っていますね", "雷ですね。お気をつけて"],
    },
    "mid": {
        "晴れ":       ["今日いい天気だね", "晴れてるね、気持ちいい", "外、すごく晴れてるよ"],
        "くもり":     ["今日は曇りだね", "ちょっと空が重たいね", "雲が多いね"],
        "弱い雨":     ["小雨が降ってるね", "しとしと降ってるね", "ちょっと雨だね"],
        "中くらいの雨": ["けっこう降ってるね、傘持った？", "雨、しっかり降ってるね", "今日は雨だね"],
        "強い雨":     ["すごい雨だね、外出るなら気をつけて", "土砂降りだよ、濡れないようにね", "うわ、すごい降ってる"],
        "雪":         ["雪が降ってるよ", "雪だね、積もるかな", "外、雪だよ。寒いはず"],
        "霧":         ["霧が出てるね", "外、真っ白だよ"],
        "みぞれ":     ["みぞれだね、一番寒いやつ", "みぞれ降ってるよ、冷えるね"],
        "あられ":     ["あられ降ってるみたい", "なんかパラパラ音がするね"],
        "雷":         ["雷鳴ってるね", "ゴロゴロ言ってるよ、近いかも"],
    },
    "high": {
        "晴れ":       ["今日いい天気だよ！", "めっちゃ晴れてる！", "お出かけ日和だね！"],
        "くもり":     ["今日は曇りだけど、まあ悪くないね", "ちょっと曇ってるね。でものんびりできそう"],
        "弱い雨":     ["小雨だね。たまには雨もいいよね", "ちょっと降ってるね。傘いるかも"],
        "中くらいの雨": ["雨けっこう降ってるね、今日は家でのんびりしよっか", "雨だね、傘持った？風邪ひかないでね"],
        "強い雨":     ["すごい雨だね！ほんと気をつけてね", "土砂降り！今日は無理して出なくていいよ"],
        "雪":         ["雪だよ雪！見て見て！", "雪降ってるよ！積もるかな？"],
        "霧":         ["外、真っ白だよ！なんか不思議だね", "霧すごいね、映画みたい"],
        "みぞれ":     ["みぞれだね、寒そう。あったかくしてね", "みぞれ降ってるよ、足元気をつけてね"],
        "あられ":     ["あられ降ってる！パラパラ言ってるよ", "なんか当たる音すると思ったらあられだ！"],
        "雷":         ["雷すごいね。ちょっとびっくりした", "ゴロゴロ鳴ってるね。家にいたほうがいいかも"],
    },
}

temp_line = {
    "hot": {
        "low":  ["今日は暑いですね。水分をとってくださいね", "暑いですね。無理しないでくださいね"],
        "mid":  ["今日暑いね、水分とってね", "暑いね。ちゃんと水飲んでる？", "暑すぎない？無理しないでね"],
        "high": ["あっつい！ちゃんと水分とってね", "今日暑すぎ！溶けそう", "暑いね、アイスでも食べたいな"],
    },
    "cold": {
        "low":  ["今日は冷えますね。暖かくしてくださいね", "寒いですね。風邪に気をつけてください"],
        "mid":  ["今日寒いね、あったかくしてね", "寒いね。風邪ひかないようにね", "冷えるね、上着持った？"],
        "high": ["さむい！あったかくしてね", "今日めっちゃ寒いね。あったかいもの飲もう", "寒いね、風邪ひかないでね"],
    },
}
 
season_change = {
    "spring": {
        "low":  ["春になりましたね", "暖かくなってきましたね"],
        "mid":  ["春になったね", "あったかくなってきたね"],
        "high": ["春だよ！お花見行きたいな", "春になったね！なんかわくわくする"],
    },
    "summer": {
        "low":  ["夏になりましたね", "暑くなってきましたね"],
        "mid":  ["夏になったね", "暑くなってきたね"],
        "high": ["夏だー！何しよっか", "夏になったね！アイス食べたい"],
    },
    "autom": {
        "low":  ["秋になりましたね", "涼しくなってきましたね"],
        "mid":  ["秋になったね", "涼しくなってきたね"],
        "high": ["秋だね！おいしいもの食べたいな", "秋になったね、過ごしやすくていいね"],
    },
    "winter": {
        "low":  ["冬になりましたね", "寒くなってきましたね"],
        "mid":  ["冬になったね", "寒くなってきたね"],
        "high": ["冬だね！雪降るかな", "冬になったね。あったかくしなきゃ"],
    },
}
 
absence_text = {
    "low":  ["お久しぶりですね", "お久しぶりです。お元気でしたか"],
    "mid":  ["久しぶり、元気だった？", "久しぶりだね。どうしてたの？"],
    "high": ["久しぶり！元気だった？", "久しぶり！待ってたよ", "久しぶり！会いたかったよ"],
}

absence_long_text = {
    "mid":  ["久しぶり...忙しかった？"],
    "high": ["久しぶり...どうしてたの？", "...来てくれたんだ、久しぶり"],
}#ほぼ百あとでアップデートします

# 9ヶ月以上あいたとき用(mid / high のみ。low は通常のセリフ)。このあとに普通のあいさつが続く
absence_9m_text = {
    "mid":  ["...ずいぶん、長かったね", "久しぶりすぎて、ちょっとびっくりしたよ"],
    "high": ["...ずっと、待ってたんだよ", "もう来てくれないかと思った...", "...夢じゃ、ないよね？"],
}#★仮の文章。あとで差し替え


# 文字送りの状態
char_idx = 0           # 何文字目まで表示したか

TEXT_SPEED = 80        # 1文字出すまでのミリ秒
last_text_time = pygame.time.get_ticks()

# ---------- 4-2. 時間帯・季節 ----------
day = [9,10,11,12,13,14,15,16]
night = [21,22,23,24,0,1,2,3,4]   
morning = [5,6,7,8]
noon = [17,18,19,20]
sleep = [23,24,0,1,2,3,4,5,6]

#四季
spring = [3,4,5]
summer = [6,7,8]
autom = [9,10,11]
winter = [12,1,2]

# ---------- 4-3. 選択メニューの状態 ----------
first_rect_size_add = 0     # 選ばれた枠だけ +2 で大きくする
second_rect_size_add = 0
third_rect_size_add = 0
selected = 2

# ---------- 4-4. ステータス ----------
#ステータス
stats = {
    "name" : "ほたる",
    "lk" : 0,        # 好感度
    "slp" : 80,      # 眠気(★小さいほど眠い。0〜100)
    "hunger" : 50,   # 空腹(★0=空腹 〜 100=満腹。大きいほど満腹)
    "lk_pending" : 0.0,                            # 今回遊んで増減した好感度。次回起動時に lk へ反映される
    "daily" : {"date": "", "pet": 0, "talk": 0}    # 今日の「撫でる/雑談」の回数(好感度が上がる回数の上限用)
}

# ---------- 4-5. 天気の設定 ----------
#天気のセットアップ
#住んでる場所に応じて変えてね ◎∀<

city = "Mississauga"

def make_url(c):
    return "https://wttr.in/" + urllib.parse.quote(c) + "?format=j1"

def web_ask_city(force=False):
    # ブラウザ版: 天気を取る場所を入力してもらう(最初の1回だけ。保存される)
    # force=True なら保存済みでも聞き直す(ゲーム中に C キー)
    global city
    saved = None
    try:
        v = platform.window.localStorage.getItem("city")
        saved = str(v) if v else None
    except Exception:
        pass
    if saved and not force:
        city = saved
        return
    default = saved or city
    try:
        ans = platform.window.prompt(
            "天気を取得する場所(都市名)を入力してください\n例: Tokyo / Osaka / Mississauga", default)
    except Exception:
        ans = None
    ans = str(ans).strip() if ans else ""
    city = ans if ans and ans != "None" else default
    try:
        platform.window.localStorage.setItem("city", city)
    except Exception:
        pass

if WEB:
    web_ask_city()

url = make_url(city)

# ---------- 4-6. 日時の記録 ----------
date_data = [0,0,0,25,4]#最後の年,最期の月,最期の日,最期の時間,四季0~3

first_code = True    # 最初の1フレームだけ date_data を今の日時で上書きするためのフラグ

# ---------- 4-7. 天気コード → 大分類 ----------
WEATHER_CATEGORY = {}

def _reg(category, codes):
    for c in codes:
        WEATHER_CATEGORY[str(c)] = category

_reg("晴れ",       [113])
_reg("くもり",     [116, 119, 122])
_reg("霧",         [143, 248, 260])
_reg("弱い雨",     [176, 263, 266, 293, 296, 353])
_reg("中くらいの雨", [299, 302, 356])
_reg("強い雨",     [305, 308, 359])
_reg("みぞれ",     [179, 182, 185, 281, 284, 311, 314, 317, 320, 362, 365])
_reg("雪",         [227, 230, 323, 326, 329, 332, 335, 338, 368, 371, 392, 395])
_reg("あられ",     [350, 374, 377])
_reg("雷",         [200, 386, 389])


# ---------- 4-8. 好感度・空腹度・眠気の数値設定 ----------
# ★バランス調整はここの数字をいじればOK
# 好感度の段階は ez_lk と同じ "low" / "mid" / "high" で引く

LK_DAILY = {"low": 0.25, "mid": 0.3, "high": 0.45}      # 毎日会う(前日にも会っていたとき、起動時に加算)

LK_PET = {"low": 0.0, "mid": 0.1, "high": 0.2}          # 撫でる
LK_PET_LIMIT = 4                                        # 好感度が上がるのは1日4回まで

LK_TALK = {"low": 0.04, "mid": 0.06, "high": 0.1}       # 雑談
LK_TALK_LIMIT = 10                                      # 好感度が上がるのは1日10回まで

LK_FEED = {                                             # 食事を与える(与える前の空腹度 x で決まる)
    "hungry": {"low": 0.4,  "mid": 0.5,  "high": 0.7},  #   0 <= x <= 20  空腹時
    "normal": {"low": 0.2,  "mid": 0.3,  "high": 0.4},  #  20 <  x <  80
    "full":   {"low": 0.01, "mid": 0.05, "high": 0.05}, #  80 <= x        満腹時
    "over":   {"low": -1,   "mid": -2,   "high": -3},   #  92 <= x        満腹超過("full" より優先)
}
FEED_AMOUNT = 30                                        # ★仮: 食事1回で空腹度が増える量(仕様に無かったので仮置き)

LONG_ABSENCE_DAYS = 2                                   # この日数以上あいたら「長時間」扱い(好感度ダウンもここから)
NINE_MONTHS_DAYS = 270                                  # 「ガチで9ヶ月以上」= 30日×9。これ以上は好感度が下がらない
LK_ABSENCE_DIV = {"low": 8, "mid": 5, "high": 3}        # 会わなかったとき -(日数 / これ) ** 2

HUNGER_LOSS_PER_HOUR = 12                               # 空腹度は1時間で12減る(約9時間で0)
MEAL_HOURS = [7, 12, 20]                                # 長時間あいたとき、この時間に食べたことにする
SLP_LOSS_PER_HOUR = 4.7                                 # 起きている1時間で眠気(slp)が4.7減る(約21時間で0)


# ==========================================================
# 5. 関数
# ==========================================================

# ---------- 5-1. テキスト表示まわり ----------
def get_total_lines(full_text, font, max_width):
    if not full_text:
        return 1
    
    lines = 1
    current_x = 0
    for char in full_text:
        if char == '\n':
            lines += 1
            current_x = 0
            continue
        
        char_w, _ = font.size(char)
        if current_x + char_w > max_width:
            lines += 1
            current_x = char_w
        else:
            current_x += char_w
    return lines


def draw_centered_wrapped_text(surface, displayed_text, full_text, font, box_x, box_y, box_w, box_h, line_height=14):
    # テキストボックス画像を描き、その中に1文字ずつ折り返しながら文字を描く
    virtual_surface.blit(txt_box_img, (102, 22))
    padding_x = 5
    max_width = box_w - (padding_x * 2)
    
    total_lines = get_total_lines(full_text, font, max_width)
    total_lines = min(total_lines, 6)
    
    total_text_height = total_lines * line_height
    start_y = box_y + (box_h - total_text_height) // 2
    start_x = box_x + padding_x
    
    current_x = start_x
    current_y = start_y
    
    for char in displayed_text:
        if char == '\n':
            current_x = start_x
            current_y += line_height
            continue

        char_w, _ = font.size(char)

        if current_x + char_w > start_x + max_width:
            current_x = start_x
            current_y += line_height

        char_surface = font.render(char, False, (0, 0, 0))
        surface.blit(char_surface, (current_x, current_y))
        current_x += char_w


# ---------- 5-2. セーブ/ロード ----------
def save_game():
    save_data = {
        "stats": stats,
        "date_data": date_data
    }
    if WEB:
        # ブラウザ版: localStorage に保存(ブラウザごとに残る)
        try:
            platform.window.localStorage.setItem("save_json", json.dumps(save_data, ensure_ascii=False))
        except Exception as e:
            print("save failed", e)
        return
    path = os.path.join("save.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    print("saved")

def load_game():
    global stats
    path = os.path.join("save.json")
    try:
        if WEB:
            raw = platform.window.localStorage.getItem("save_json")
            if not raw:
                raise FileNotFoundError
            save_data = json.loads(str(raw))
        else:
            with open(path, "r", encoding="utf-8") as f:
                save_data = json.load(f)
        stats.update(save_data["stats"])
        date_data[:] = save_data["date_data"]
        print("loaded")
        return True
    except (FileNotFoundError, ValueError, KeyError):
        print("no data found")
        return False


# ---------- 5-3. 天気・通信 ----------
def get_weather_category(code):
    return WEATHER_CATEGORY.get(str(code),"?")   # 不明なコードは "?" が返る

def check_wifi():
    if WEB:
        try:
            return bool(platform.window.navigator.onLine)
        except Exception:
            return True
    try:
        socket.setdefaulttimeout(1)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8",53))
        return True
    except OSError:
        return False


# ---------- 5-4. 終了時 ----------
def on_exit():
    # ★「最後に遊んだ日時」を終了時の日時にしてから保存する
    #   (日付は起動直後にしか更新されないため、日をまたいで遊ぶと記録がズレるのを防ぐ)
    now_exit = datetime.now()
    date_data[0:5] = [now_exit.year, now_exit.month, now_exit.day, now_exit.hour, get_season(now_exit.month)]
    save_game()


# ---------- 5-5. セリフの抽選 ----------
ABSENCE_HOURS = 24                 # この時間以上あいたら「久しぶり」
SEASON_KEYS = ["spring", "summer", "autom", "winter"]   # get_season の 0〜3 に対応

def get_season(month):
    # 月 → 0=春 1=夏 2=秋 3=冬 (date_data[4] と同じ数え方)
    if month in spring:
        return 0
    elif month in summer:
        return 1
    elif month in autom:
        return 2
    else:
        return 3

def get_temp_cat(t):
    # 気温(文字列でも可) → "hot" / "cold" / None(普通)
    t = int(t)
    if t >= 28:
        return "hot"
    elif t <= 5:
        return "cold"
    return None

def pick_startup_text(skip_absence=False):
    # 起動時のセリフを1つ選んで「文字列」で返す
    # 優先順位: 寝ている → 久しぶり → (Wi-Fiあり)季節/気温/天気つきのあいさつ → 普通のあいさつ
    hour = now.hour
    long_absence = date_passed >= LONG_ABSENCE_DAYS

    # 1. 寝ている時間 → 寝息だけ
    if hour in sleep:
        if wifi_on:
            return random.choice(sleep_line[ez_lk])
        return random.choice(startup[ez_lk]["sleep"])

    # 2. 久しぶり(長くあいたときは absence_l / absence_long_text があればそちら)
    if hour_passed >= ABSENCE_HOURS and not skip_absence:
        if wifi_on:
            pool = absence_long_text.get(ez_lk) if long_absence else None
            pool = pool or absence_text[ez_lk]
        else:
            pool = startup[ez_lk].get("absence_l") if long_absence else None
            pool = pool or startup[ez_lk]["absence"]
        return random.choice(pool)

    # 3. Wi-Fiあり(天気が取れているとき): あいさつ + 区切り + コメント
    if wifi_on and weather_cat is not None:
        g = random.choice(greet[ez_lk][now_day_q])
        sep = "。" if ez_lk == "low" else "、"
        cur_season = get_season(now.month)
        if last_season in (0, 1, 2, 3) and last_season != cur_season:
            # 季節が変わっていたら季節を最優先
            comment = random.choice(season_change[SEASON_KEYS[cur_season]][ez_lk])
        else:
            temp_cat = get_temp_cat(temp_c)
            if temp_cat is not None and random.random() < 0.4:
                # 暑い/寒いときは、4割の確率で気温コメント
                comment = random.choice(temp_line[temp_cat][ez_lk])
            else:
                lines = weather_line[ez_lk].get(weather_cat, weather_line[ez_lk]["くもり"])   # 不明("?")はくもり扱い
                comment = random.choice(lines)
        return g + sep + comment

    # 4. Wi-Fiなし(または天気が取れなかった): 普通のあいさつ
    return random.choice(startup[ez_lk][now_day_q])


def pick_startup_lines():
    # 起動セリフを「リスト」で返す
    # 9ヶ月以上あいたとき、mid/high は「特別なセリフ → 普通のあいさつ」の順。low は通常のセリフ。
    # (寝ている時間は寝息だけ)
    if date_passed >= NINE_MONTHS_DAYS and ez_lk in ("mid", "high") and now.hour not in sleep:
        return [random.choice(absence_9m_text[ez_lk]), pick_startup_text(skip_absence=True)]
    return [pick_startup_text()]


# ---------- 5-6. 会話(テキスト表示)の制御 ----------
talk_lines = []     # いまの会話のセリフ(リスト)
talk_idx = 0        # 何番目のセリフを表示中か

def start_talk(lines):
    # 会話を始める。lines は文字列、または文字列のリスト(2つ以上ならZで続きが出る)
    global talk_lines, talk_idx, show_text, full_text, char_idx, talking
    if isinstance(lines, str):
        lines = [lines]
    talk_lines = lines
    talk_idx = 0
    show_text = talk_lines[0]
    full_text = show_text
    char_idx = 0          # 文字送りを最初からやり直す
    talking = True

def advance_talk():
    # Zが押されたときの会話の進め方。会話がおわったら True を返す
    global talk_idx, show_text, full_text, char_idx, talking
    if char_idx < len(full_text):
        char_idx = len(full_text)       # 文字送りの途中 → 全文を一気に出す
        return False
    if talk_idx + 1 < len(talk_lines):
        talk_idx += 1                   # 次のセリフへ
        show_text = talk_lines[talk_idx]
        full_text = show_text
        char_idx = 0
        return False
    talking = False                     # 最後のセリフ → 会話おわり
    return True

# 選択したあとの返事(★仮の文章。あとで本物に差し替え)
# 1つの返事は「セリフのリスト」。リストを2つ以上入れると、Zで続きが出る
reply_lines = {
    "pet": {
        "low":  [["…どうも"]],
        "mid":  [["えへへ", "くすぐったいよ"]],
        "high": [["もっと撫でて！"]],
    },
    "feed": {
        "low":  [["ありがとうございます"]],
        "mid":  [["ありがとう、おいしい"]],
        "high": [["わーい！ありがとう！", "もう一個ほしいな"]],
    },
    "talk": {
        "low":  [["何かご用ですか？"]],
        "mid":  [["今日はなにしてたの？"]],
        "high": [["ねえ聞いて聞いて！", "さっきね、面白いことがあったんだ"]],
    },
}

# 食事を与えたときの返事(★仮の文章。あとで本物に差し替え)
# 与える「前」の空腹度で4つに分かれる(数値の境目は get_feed_state と同じ):
#   hungry = 空腹時(0〜20) / normal = ふつう(21〜79) / full = 満腹時(80〜91) / over = 満腹超過(92以上)
# 好感度(low/mid/high)ごとに「セリフのリスト」を並べる。リストを2つ以上入れると、Zで続きが出る
feed_reply_lines = {
    "hungry": {
        "low":  [["ありがとうございます。助かります"], ["いただきます"]],
        "mid":  [["ありがとう！お腹ぺこぺこだった"], ["待ってました！いただきます"]],
        "high": [["わーい！待ってたよ！", "いただきます！"], ["ありがとう！ほんとにお腹すいてたんだ"]],
    },
    "normal": {
        "low":  [["ありがとうございます"]],
        "mid":  [["ありがとう、おいしい"]],
        "high": [["わーい！ありがとう！", "もう一個ほしいな"]],
    },
    "full": {
        "low":  [["ありがとうございます..."],["...では、すこしだけ","..."]],
        "mid":  [["あ、ありがとう。一応もらっておくね"], ["...じゃあ、ちょっとだけもらうね"]],
        "high": [["ありがとう！でもちょっとだけでいいかな"], ["ちょ、ちょっとだけもらうね"]],
    },
    "over": {
        "low":  [["もう結構です"], ["さすがに、これ以上は……"]],
        "mid":  [["うっ、もう入らないよ..."], ["...もう食食べられないよ"]],
        "high": [["もう無理だよ〜！", "苦しい..."], ["...こんなに食べきれないよ"]],
    },
}

# def pick_reply_lines(action):
#     # action: "pet" / "feed" / "talk"。好感度(ez_lk)に合った返事を1つ選ぶ
#     return random.choice(reply_lines[action][ez_lk])

def pick_reply_lines(action, feed_state=None):
    # action: "pet" / "feed" / "talk"。好感度(ez_lk)に合った返事を1つ選ぶ
    # 食事のときだけ、与える前の状態(feed_state)に合わせた返事を使う
    # (feed_state が無いときは、上の reply_lines["feed"] がそのまま使われる)
    if action == "feed" and feed_state in feed_reply_lines:
        return random.choice(feed_reply_lines[feed_state][ez_lk])
    return random.choice(reply_lines[action][ez_lk])


# ---------- 5-7. 好感度・空腹度・眠気の計算 ----------
def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))

def lk_to_level(lk):
    # 好感度の数値 → "low" / "mid" / "high" (ez_lk と同じ基準)
    if lk > 80:
        return "high"
    elif lk > 44:
        return "mid"
    return "low"

def get_feed_state(x):
    # 食事を与える前の空腹度 x → 状態(返事を空腹/満腹で変えたいときにも使えます)
    if x >= 92:
        return "over"      # 満腹超過
    elif x >= 80:
        return "full"      # 満腹時
    elif x > 20:
        return "normal"
    return "hungry"        # 空腹時(0 <= x <= 20)

def apply_action(action):
    # 選んだ行動の効果を反映する("pet" / "feed" / "talk")
    # ・好感度は lk_pending にためる(次回起動時に反映。今の ez_lk は変わらない)
    # ・撫でる/雑談は、1日の上限回数までしか好感度が上がらない
    # ・食事は空腹度がすぐ増える
    # ・食事のときだけ「与える前の状態」(hungry/normal/full/over)を返す(返事のセリフ選びに使う)
    today = datetime.now().strftime("%Y-%m-%d")
    daily = stats["daily"]
    if daily.get("date") != today:               # 日付が変わっていたら回数をリセット
        daily["date"] = today
        daily["pet"] = 0
        daily["talk"] = 0

    gain = 0.0
    feed_state = None
    if action == "pet":
        if daily["pet"] < LK_PET_LIMIT:
            gain = LK_PET[ez_lk]
        daily["pet"] += 1
    elif action == "talk":
        if daily["talk"] < LK_TALK_LIMIT:
            gain = LK_TALK[ez_lk]
        daily["talk"] += 1
    elif action == "feed":
        # gain = LK_FEED[get_feed_state(stats["hunger"])][ez_lk]
        feed_state = get_feed_state(stats["hunger"])   # ★食べさせる「前」の空腹度で判定(増やす前に決める)
        gain = LK_FEED[feed_state][ez_lk]
        stats["hunger"] = clamp(stats["hunger"] + FEED_AMOUNT)

    stats["lk_pending"] = round(stats["lk_pending"] + gain, 4)
    return feed_state

def calc_elapsed():
    # 前回から経過した (時間, 日数) を返す。日数は「カレンダー上の日付の差」(昨日→今日 = 1)
    # 記録がない(初回起動)ときは (0, 0)
    if date_data[0] == 0:
        return 0, 0
    try:
        last = datetime(date_data[0], date_data[1], date_data[2], date_data[3])
    except ValueError:
        return 0, 0
    cur = datetime.now()
    hours = max(0, int((cur - last).total_seconds() // 3600))
    days = max(0, (cur.date() - last.date()).days)
    return hours, days

def update_lk_on_startup():
    # 起動時の好感度の更新(起動時に1回だけ)
    # 1. 前回までに lk_pending にたまった分を反映
    # 2. 前日にも会っていれば「毎日会う」ボーナス
    #    2日以上あいたら減少 -(日数/div)**2 ※9ヶ月以上あいたときは減らない
    stats["lk"] = clamp(stats["lk"] + stats["lk_pending"])
    stats["lk_pending"] = 0.0
    level = lk_to_level(stats["lk"])
    if date_passed == 1:
        stats["lk"] += LK_DAILY[level]
    elif LONG_ABSENCE_DAYS <= date_passed < NINE_MONTHS_DAYS:
        stats["lk"] -= (date_passed / LK_ABSENCE_DIV[level]) ** 2
    stats["lk"] = round(clamp(stats["lk"]), 4)

def sleep_gain(h):
    # 寝ていた時間 h(時間)ぶんの眠気の回復量。毎回少しランダム(8時間なら76〜100)
    slp_conf = random.randint(1, 25)
    return max(0, h * 12.5 - 25 / slp_conf + 1)

def update_slp_short(hours, start_hour):
    # 短い経過: 経過した時間を「寝ている時間(sleep)」と「起きている時間」のかたまりに分けて計算
    #   起きているかたまり → 1時間ごとに SLP_LOSS_PER_HOUR 減る
    #   寝ているかたまり   → sleep_gain(かたまりの時間) だけまとめて回復
    i = 0
    while i < hours:
        asleep = ((start_hour + i) % 24) in sleep
        j = i
        while j < hours and (((start_hour + j) % 24) in sleep) == asleep:
            j += 1
        run = j - i
        if asleep:
            stats["slp"] = clamp(stats["slp"] + sleep_gain(run))
        else:
            stats["slp"] = clamp(stats["slp"] - SLP_LOSS_PER_HOUR * run)
        i = j

def hunger_after_long_absence():
    # 長時間あいたとき: 食べさせていなくても食事時間(7,12,20時)には食べたことにする
    # → いちばん最近の食事時間に満腹(100)になって、そこから今までの時間ぶん減らす
    h = now.hour
    past = [m for m in MEAL_HOURS if m <= h]
    last_meal = max(past) if past else max(MEAL_HOURS) - 24   # 今日まだ食事時間が来ていなければ前日の最後の食事
    return clamp(100 - HUNGER_LOSS_PER_HOUR * (h - last_meal))


# ==========================================================
# 6. 起動時の処理(ループに入る前に1回だけ)
# ==========================================================

# ---------- 6-1. セーブ読み込み ----------
load_game()

# ---------- 6-2. Wi-Fi確認 ----------
if check_wifi():
    wifi_on = True
else:
    wifi_on = False

# ---------- 6-3. 前回から何時間/何日たったか → 好感度・空腹度・眠気の更新 ----------
# 【ルール】(数値は 4-8 で調整)
# ・好感度(lk)  : 起動時にだけ変わる。遊んでいる間の増減は lk_pending にためて、次回起動時に反映
#                 前日にも会っていれば毎日ボーナス / 2日以上あいたら減少 / 9ヶ月以上は減らない
# ・空腹度(hunger): 0=空腹 〜 100=満腹。1時間で12減る(約9時間で0)
# ・眠気(slp)   : 起きている間は1時間で4.7減る(約21時間で0)。寝ている時間(sleep)にまとめて回復
# ・2日以上あいた(長時間)ときは、hunger は食事時間(7,12,20時)から逆算、slp は76〜100のランダム

now = datetime.now()
hour_passed, date_passed = calc_elapsed()

# --- 好感度 ---
update_lk_on_startup()

# --- 空腹度・眠気 ---
if date_passed >= LONG_ABSENCE_DAYS:
    stats["hunger"] = hunger_after_long_absence()
    stats["slp"] = random.randint(76, 100)
else:
    stats["hunger"] = clamp(stats["hunger"] - HUNGER_LOSS_PER_HOUR * hour_passed)
    update_slp_short(hour_passed, date_data[3])

stats["hunger"] = round(stats["hunger"], 1)
stats["slp"] = round(stats["slp"], 1)

print(f"経過: {hour_passed}時間 / {date_passed}日 → lk={stats['lk']} hunger={stats['hunger']} slp={stats['slp']}")


#game loooop defを使ってみよう　（泣）

#諦め


# ==========================================================
# 7. メインループ
# ==========================================================
selecting = False   # True=選択メニュー表示中
# ---------- ブラウザ版の天気取得(JavaScript の fetch を使う。待たずに動く) ----------
web_weather_pending = False

def web_weather_start():
    global web_weather_pending
    try:
        platform.window.eval(
            "window.wxresult = null;"
            "fetch(" + json.dumps(url) + ")"
            ".then(r => r.text())"
            ".then(t => { window.wxresult = t; })"
            ".catch(e => { window.wxresult = 'ERR'; });"
        )
        web_weather_pending = True
    except Exception:
        web_weather_pending = False

def web_weather_poll():
    # 結果が届いていたら天気の変数に反映する
    global web_weather_pending, weather_code, weather_cat, temp_c, feels_like
    if not web_weather_pending:
        return
    try:
        res = platform.window.wxresult
    except Exception:
        web_weather_pending = False
        return
    if res is None:
        return
    web_weather_pending = False
    try:
        data = json.loads(str(res))
        cur = data["current_condition"][0]
        weather_code = cur["weatherCode"]
        temp_c = cur["temp_C"]
        feels_like = cur["FeelsLikeC"]
        weather_cat = get_weather_category(weather_code)
    except (KeyError, ValueError, IndexError):
        pass

last_weather_hour = None   # 最後に天気を取得した「時」(None=まだ取得していない)
weather_code = None        
weather_cat = None
temp_c = None
txt_setup = False          # True になった最初の1回だけ、起動セリフを抽選する
last_season = 4            # 前回の季節(0〜3、4=記録なし)。最初のフレームで入る
running = True

last_autosave = 0

async def main():
    global url, city, action, char_idx, current, current_time, data, date_str, date_text, displayed_text, event, ez_lk, feed_state, feels_like, first_code, first_rect_size_add, full_text, last_season, last_text_time, last_weather_hour, now, now_day_q, response, running, second_rect_size_add, select_text, selected, selecting, temp_c, text_image, third_rect_size_add, time_str, time_text, txt_setup, weather_cat, weather_code, last_autosave
    while running:
        current_time = pygame.time.get_ticks()
        full_text = show_text
        now = datetime.now()

        # ------------------------------------------------------
        # (A) 入力
        # ------------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.KEYDOWN:
                # → と ↓ : selected が 1 減る(=画面では下へ移動)
                if event.key == pygame.K_RIGHT:
                    if selecting == True:
                        selected -= 1
                        if selected < 0:
                            selected = 2

                # ← と ↑ : selected が 1 増える(=画面では上へ移動)
                elif event.key == pygame.K_LEFT:
                    if selecting == True:
                        selected += 1
                        if selected > 2:
                            selected = 0
                        
                elif event.key == pygame.K_DOWN:
                    if selecting == True:
                        selected -= 1
                        if selected < 0:
                            selected = 2

                elif event.key == pygame.K_UP:
                    if selecting == True:
                        selected += 1
                        if selected > 2:
                            selected = 0
                        
                # Z : 決定
                elif event.key == pygame.K_z:
                    if selecting == True:

                        # ---- 選択で決定 → 返事のセリフを出して会話へ ----
                        action = ["pet", "feed", "talk"][2 - selected]   # 上から 撫でる / 食べ物 / 雑談
                        selecting = False
                        # apply_action(action)   # 好感度(次回反映)・空腹度・1日の回数を更新
                        # start_talk(pick_reply_lines(action))
                        feed_state = apply_action(action)   # 好感度(次回反映)・空腹度・1日の回数を更新。食事のときだけ状態が返る
                        start_talk(pick_reply_lines(action, feed_state))
                    elif talking == True:
                        # talking = False   # 元: 押したら即おわり

                        # ---- 会話中のZ: 全文表示 → 次のセリフ → おわり ----
                        if advance_talk():
                            selecting = True    # 会話がおわったら選択メニューへ(Xで閉じられる)
                elif WEB and event.key == pygame.K_c:
                    # ブラウザ版: 天気の場所を変える
                    web_ask_city(force=True)
                    url = make_url(city)
                    weather_cat = None
                    last_weather_hour = None

                elif event.key == pygame.K_x:
                    if selecting == False and talking == False:
                        selecting = True
                    elif selecting == True and talking == False:
                        selecting = False
                    

        # ------------------------------------------------------
        # (B) 更新
        # ------------------------------------------------------

        # ---- B-1. 文字送り(80msごとに1文字増やす) ----
        # 文字送り処理
        if char_idx < len(full_text):
            if current_time - last_text_time >= TEXT_SPEED:
                last_text_time = current_time
                char_idx += 1

        # ---- B-2. 画面の下地を白で塗りつぶす(ここから描画) ----
        # 描画処理（毎フレーム実行）
        virtual_surface.fill((255, 255, 255))
    
        # ---- B-3. 時刻の文字列を作る ----
        time_str = now.strftime("%H:%M:%S")#時
        date_str = now.strftime("%Y-%m-%d")#間

        # ---- B-4. 天気取得(Wi-Fiあり & 「時」が変わったときだけ) ----
        if wifi_on == True:
            if WEB:
                if last_weather_hour != now.hour:
                    last_weather_hour = now.hour
                    web_weather_start()
                web_weather_poll()
            elif last_weather_hour != now.hour:
                last_weather_hour = now.hour   
                try:
                    with urllib.request.urlopen(url, timeout=3) as response:#天
                        data = json.loads(response.read().decode("utf-8"))#      気
                    current = data["current_condition"][0]
                    weather_code = current["weatherCode"]
                    temp_c = current["temp_C"]
                    feels_like = current["FeelsLikeC"]
                    weather_cat =  get_weather_category(weather_code)
                except (OSError, KeyError, ValueError):
                    pass   

        # ---- B-5. 「最後の時間」を今の時間に更新 ----
        if date_data[3] != now.hour:
            date_data[3] = now.hour

        time_text = time_str
        date_text = date_str
    
        # ------------------------------------------------------
        # (C) 描画
        # ------------------------------------------------------

        # ---- C-1. 時間帯のアイコン ----
        if now.hour in day:
            virtual_surface.blit(day_img, (114, 3))
            now_day_q = "day"
        elif now.hour in night:
            virtual_surface.blit(night_img, (114, 3))
            now_day_q = "night"
        elif now.hour in morning:
            virtual_surface.blit(morning_img, (114, 3))
            now_day_q = "morning"
        else:
            virtual_surface.blit(noon_img, (114, 3))
            # now_day_q = "night"
            now_day_q = "noon"   # ★夕方のセリフ(noon)が使われるように変更。元は "night" でした

        # ---- C-2. 最初の1フレームだけ、date_data を今の日時にする ----
        if first_code == True and (not WEB or not wifi_on or weather_cat is not None or current_time > 4000):   # ブラウザ版は天気が届くのを最大4秒待つ
            date_data[0] = now.year
            date_data[1] = now.month
            date_data[2] = now.day
            date_data[3] = now.hour
            last_season = date_data[4]                # ★書き換える前の「前回の季節」を控えておく(季節の変わり目の判定用)
            date_data[4] = get_season(now.month)      # 今の季節を記録(終了時にも保存される)
            # if stats['lk'] > 80:
            #     ez_lk = 'high'
            # elif stats['lk'] > 44:
            #     ez_lk = 'mid'
            # else:
            #     ez_lk = 'low'
            ez_lk = lk_to_level(stats['lk'])   # 基準は同じ(80超=high, 44超=mid)。5-7 の関数にまとめた
            txt_setup = True
            first_code = False
    
        # ---- C-3. 日付と時刻 ----
        text_image = font_s.render(date_text, False, (0, 0, 0))
        virtual_surface.blit(text_image, (132, 4))
        text_image = font_s.render(time_text, False, (0, 0, 0))
        virtual_surface.blit(text_image, (195, 4))
    
        # ---- C-4. 上下の黒い線 ----
        pygame.draw.rect(virtual_surface, (0, 0, 0), (0, 0, 250, 1))
        pygame.draw.rect(virtual_surface, (0, 0, 0), (0, 121, 250, 1))

        # ---- C-5. 選択メニュー(selecting が True の間だけ) ----
        # 選択枠の描画
        if selecting:
            # 選ばれている枠だけ +2 で大きくする
            if selected == 0:
                first_rect_size_add = 0
                second_rect_size_add = 0
                third_rect_size_add = 2
            elif selected == 1:
                first_rect_size_add = 0
                second_rect_size_add = 2
                third_rect_size_add = 0
            elif selected == 2:
                first_rect_size_add = 2
                second_rect_size_add = 0
                third_rect_size_add = 0

            # 1つ目(上): 撫でる
            pygame.draw.rect(virtual_surface, (0, 0, 0), (120 - first_rect_size_add, 35 - first_rect_size_add, 120 + first_rect_size_add, 16 + first_rect_size_add))
            pygame.draw.rect(virtual_surface, (255, 255, 255), (121 - first_rect_size_add, 36 - first_rect_size_add, 118 + first_rect_size_add, 14 + first_rect_size_add))
            select_text = select_text_1[0]
            text_image = font_s.render(select_text, False, (0, 0, 0))
            virtual_surface.blit(text_image, (162- first_rect_size_add, 37- first_rect_size_add))
        
            # 2つ目(中): 食べ物を渡す
            pygame.draw.rect(virtual_surface, (0, 0, 0), (120 - second_rect_size_add, 60 - second_rect_size_add, 120 + second_rect_size_add, 16 + second_rect_size_add))
            pygame.draw.rect(virtual_surface, (255, 255, 255), (121 - second_rect_size_add, 61 - second_rect_size_add, 118 + second_rect_size_add, 14 + second_rect_size_add))
            select_text = select_text_1[1]
            text_image = font_s.render(select_text, False, (0, 0, 0))
            virtual_surface.blit(text_image, (145 - second_rect_size_add, 62 - second_rect_size_add))
        
            # 3つ目(下): 雑談
            pygame.draw.rect(virtual_surface, (0, 0, 0), (120 - third_rect_size_add, 85 - third_rect_size_add, 120 + third_rect_size_add, 16 + third_rect_size_add))
            pygame.draw.rect(virtual_surface, (255, 255, 255), (121 - third_rect_size_add, 86 - third_rect_size_add, 118 + third_rect_size_add, 14 + third_rect_size_add))
            select_text = select_text_1[2]
            text_image = font_s.render(select_text, False, (0, 0, 0))
            virtual_surface.blit(text_image, (168 - third_rect_size_add, 87 - third_rect_size_add))

        # ---- C-6. テキストボックスとセリフ ----
        if txt_setup == True:
            start_talk(pick_startup_lines())   # 起動セリフを抽選して会話開始(中身は 5-5 の関数)
            txt_setup = False

        if talking:
        
        
            displayed_text = full_text[:char_idx]
            draw_centered_wrapped_text(
                surface=virtual_surface,
                displayed_text=displayed_text,
                full_text=full_text,
                font=font_s,
                box_x=113,
                box_y=25,
                box_w=125,
                box_h=82,
                line_height=14
            )
    
        # ------------------------------------------------------
        # (D) 拡大してウィンドウに表示 / 60fps に制限
        # ------------------------------------------------------
        display_auto()
        # ブラウザ版: 5秒ごとに自動セーブ(タブを閉じても進行が残るように)
        if WEB and current_time - last_autosave >= 5000:
            last_autosave = current_time
            on_exit()
        clock.tick(60)
        await asyncio.sleep(0)   # ブラウザに制御を返す(pygbagに必須)

asyncio.run(main())


# ==========================================================
# 8. 終了処理
# ==========================================================
if not WEB:
    # PC版だけ: ブラウザ版では asyncio.run が待たずに戻るので、ここで終了処理をしてはいけない
    atexit.register(on_exit)
    pygame.quit()
    sys.exit()
