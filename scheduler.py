"""
Todo → Google Calendar 自動スケジューラー
毎朝4:30にGitHub Actionsから実行されます
"""

import os
import json
import math
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from config import (
    SPREADSHEET_ID, SHEET_NAME,
    BUFFER_RATIO, MORNING_START, MORNING_END,
    AFTERNOON_START, AFTERNOON_END, MIN_SLOT_MINUTES,
    SCHEDULE_DAYS_AHEAD, CALENDAR_ID,
    EMOJI_MAP, EMOJI_THINKING, EMOJI_SIMPLE,
)

JST = ZoneInfo("Asia/Tokyo")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/calendar",
]

# ===== 認証 =====

def get_credentials():
    """GitHub SecretsのJSON文字列 or ローカルのcredentials.jsonで認証"""
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        info = json.loads(creds_json)
    else:
        with open("credentials.json") as f:
            info = json.load(f)
    return Credentials.from_service_account_info(info, scopes=SCOPES)


# ===== Google Sheets: タスク読み込み =====

def fetch_tasks(creds):
    """SheetsからTodoを読み込み、スケジュール対象のタスク一覧を返す"""
    service = build("sheets", "v4", credentials=creds)
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_NAME}!A2:H")
        .execute()
    )
    rows = result.get("values", [])
    tasks = []
    for row in rows:
        if len(row) < 7:
            continue
        task_name, importance, urgency, task_type, duration_str, deadline_str, status = (
            row + [""] * 8
        )[:8][:7]

        # 完了済み・進行中はスキップ
        if status in ("完了", "進行中"):
            continue

        try:
            duration = int(duration_str)
        except ValueError:
            duration = 30  # デフォルト30分

        try:
            deadline = datetime.strptime(deadline_str.strip(), "%Y/%m/%d").date()
        except ValueError:
            deadline = date.today() + timedelta(days=30)

        tasks.append({
            "name": task_name.strip(),
            "importance": importance.strip(),   # 高/中/低
            "urgency": urgency.strip(),         # 高/中/低
            "task_type": task_type.strip(),     # 思考系/単純作業
            "duration": duration,               # 分
            "deadline": deadline,
            "status": status.strip(),
        })
    return tasks


def sort_tasks(tasks):
    """優先度スコアでソート（高いほど先に入れる）"""
    order = {"高": 0, "中": 1, "低": 2}

    def score(t):
        imp = order.get(t["importance"], 2)
        urg = order.get(t["urgency"], 2)
        days_left = (t["deadline"] - date.today()).days
        return (imp, urg, days_left)

    return sorted(tasks, key=score)


# ===== Google Calendar: 空き時間取得 =====

def _to_dt(time_str: str, target_date: date) -> datetime:
    h, m = map(int, time_str.split(":"))
    return datetime(target_date.year, target_date.month, target_date.day, h, m, tzinfo=JST)


def get_free_slots(creds, target_date: date):
    """
    指定日の空き時間スロット一覧を返す
    戻り値: [(start_dt, end_dt), ...]  ※午前・午後それぞれ設定時間内のみ
    """
    service = build("calendar", "v3", credentials=creds)

    day_start = _to_dt("00:00", target_date)
    day_end = _to_dt("23:59", target_date)

    body = {
        "timeMin": day_start.isoformat(),
        "timeMax": day_end.isoformat(),
        "items": [{"id": CALENDAR_ID}],
    }
    result = service.freebusy().query(body=body).execute()
    busy_periods = result["calendars"][CALENDAR_ID]["busy"]

    # 「使える時間帯」を定義
    windows = [
        (_to_dt(MORNING_START, target_date), _to_dt(MORNING_END, target_date), "morning"),
        (_to_dt(AFTERNOON_START, target_date), _to_dt(AFTERNOON_END, target_date), "afternoon"),
    ]

    free_slots = []
    for win_start, win_end, period in windows:
        cursor = win_start
        for busy in sorted(busy_periods, key=lambda x: x["start"]):
            # Python 3.9 は 'Z' を fromisoformat で解析できないため置換
            b_start = datetime.fromisoformat(busy["start"].replace("Z", "+00:00")).astimezone(JST)
            b_end = datetime.fromisoformat(busy["end"].replace("Z", "+00:00")).astimezone(JST)
            if b_end <= cursor or b_start >= win_end:
                continue
            if cursor < b_start:
                free_slots.append((cursor, min(b_start, win_end), period))
            cursor = max(cursor, b_end)
        if cursor < win_end:
            free_slots.append((cursor, win_end, period))

    # MIN_SLOT_MINUTES 未満の細切れ枠を除外
    return [
        s for s in free_slots
        if (s[1] - s[0]).total_seconds() / 60 >= MIN_SLOT_MINUTES
    ]


# ===== 絵文字生成 =====

def make_title(task: dict) -> str:
    base_emoji = EMOJI_MAP.get((task["importance"], task["urgency"]), "🔵")
    type_emoji = EMOJI_THINKING if task["task_type"] == "思考系" else EMOJI_SIMPLE
    return f"{base_emoji}{type_emoji} {task['name']}"


# ===== カレンダー登録 =====

def register_event(service, title: str, start_dt: datetime, end_dt: datetime):
    event = {
        "summary": title,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Tokyo"},
        "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "Asia/Tokyo"},
        "colorId": "11",  # Tomato（赤）— 重要タスクの目印
    }
    service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    print(f"  ✅ 登録: {title}  {start_dt.strftime('%H:%M')}〜{end_dt.strftime('%H:%M')}")


def already_registered(service, title: str, target_date: date) -> bool:
    """同じタイトルのイベントが今日すでに登録されているか確認（重複防止）"""
    day_start = _to_dt("00:00", target_date).isoformat()
    day_end = _to_dt("23:59", target_date).isoformat()
    events = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=day_start,
        timeMax=day_end,
        singleEvents=True,
    ).execute().get("items", [])
    return any(e.get("summary", "") == title for e in events)


# ===== メイン処理 =====

def main():
    print("=== Todo → Calendar スケジューラー 起動 ===")
    creds = get_credentials()
    cal_service = build("calendar", "v3", credentials=creds)

    tasks = fetch_tasks(creds)
    print(f"タスク読み込み: {len(tasks)}件")

    tasks = sort_tasks(tasks)

    for day_offset in range(SCHEDULE_DAYS_AHEAD):
        target_date = date.today() + timedelta(days=day_offset)
        print(f"\n--- {target_date} ---")

        free_slots = get_free_slots(creds, target_date)
        print(f"空き枠: {len(free_slots)}件")

        # 午前枠と午後枠に分ける
        morning_slots = [(s, e) for s, e, p in free_slots if p == "morning"]
        afternoon_slots = [(s, e) for s, e, p in free_slots if p == "afternoon"]

        # 午前: 思考系タスク優先
        thinking_tasks = [t for t in tasks if t["task_type"] == "思考系"]
        simple_tasks   = [t for t in tasks if t["task_type"] == "単純作業"]

        scheduled = set()

        def schedule_into(slot_list, task_list):
            for slot_start, slot_end in slot_list:
                cursor = slot_start
                for task in task_list:
                    task_id = task["name"]
                    if task_id in scheduled:
                        continue
                    buffered_min = math.ceil(task["duration"] * BUFFER_RATIO)
                    event_end = cursor + timedelta(minutes=buffered_min)
                    if event_end > slot_end:
                        break
                    title = make_title(task)
                    if not already_registered(cal_service, title, target_date):
                        register_event(cal_service, title, cursor, event_end)
                    scheduled.add(task_id)
                    cursor = event_end

        schedule_into(morning_slots, thinking_tasks)
        schedule_into(afternoon_slots, simple_tasks)

        # 午後に入りきらなかった思考系は午後にも回す
        remaining_thinking = [t for t in thinking_tasks if t["name"] not in scheduled]
        schedule_into(afternoon_slots, remaining_thinking)

    print("\n=== 完了 ===")


if __name__ == "__main__":
    main()
