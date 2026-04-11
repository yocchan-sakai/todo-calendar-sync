"""
カレンダーへの書き込みテスト
"""
import json
import warnings
warnings.filterwarnings("ignore")

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_ID = "yocchan.tempa@gmail.com"
JST = ZoneInfo("Asia/Tokyo")

with open("credentials.json") as f:
    info = json.load(f)

creds = Credentials.from_service_account_info(info, scopes=SCOPES)
service = build("calendar", "v3", credentials=creds)

# テスト用イベントを登録
now = datetime.now(JST).replace(second=0, microsecond=0)
start = now + timedelta(minutes=5)
end = start + timedelta(minutes=30)

event = {
    "summary": "🧪 テストイベント（削除OK）",
    "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Tokyo"},
    "end":   {"dateTime": end.isoformat(),   "timeZone": "Asia/Tokyo"},
}

try:
    result = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    print(f"✅ 登録成功！")
    print(f"   タイトル: {result['summary']}")
    print(f"   時間: {start.strftime('%H:%M')}〜{end.strftime('%H:%M')}")
    print(f"   カレンダーで確認してください。")
except Exception as e:
    print(f"❌ エラー: {e}")
    print()
    print("【対処法】")
    print("Googleカレンダーの共有設定を再確認してください:")
    print("  カレンダー設定 → 特定のユーザーと共有 → 権限を「予定の変更」に設定")
    print(f"  追加するメール: credentials.json 内の client_email の値")
