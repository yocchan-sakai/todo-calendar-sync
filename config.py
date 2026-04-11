# ===== 設定ファイル =====
# ここの値を自分の環境に合わせて変更してください

# Google Sheetsの設定
SPREADSHEET_ID = "1BwBwz9OaPwPUq53FwtfSoQN3Yh8XwZPz_Rb09dxvIfE"
SHEET_NAME = "タスク"                    # シート名

# スケジューリング設定
BUFFER_RATIO = 1.3          # バッファ倍率（1.3 = 30%増し）
MORNING_START = "06:00"     # 午前枠の開始時刻
MORNING_END   = "12:00"     # 午前枠の終了時刻
AFTERNOON_START = "13:00"   # 午後枠の開始時刻（昼休み除外）
AFTERNOON_END   = "18:30"   # 午後枠の終了時刻
MIN_SLOT_MINUTES = 30       # これ未満の空き枠は使わない

# 何日先までスケジュールするか
SCHEDULE_DAYS_AHEAD = 1     # 1=今日のみ、2=今日+明日

# Googleカレンダーの設定
CALENDAR_ID = "yocchan.tempa@gmail.com"  # Googleアカウントのメールアドレス

# 絵文字マッピング
EMOJI_MAP = {
    ("高", "高"): "🔴",  # 重要度高 × 緊急度高
    ("高", "中"): "🌟",  # 重要度高 × 緊急度中
    ("高", "低"): "🌟",  # 重要度高 × 緊急度低
    ("中", "高"): "🟡",  # 重要度中 × 緊急度高
    ("中", "中"): "🟡",
    ("中", "低"): "🔵",
    ("低", "高"): "🔵",
    ("低", "中"): "🔵",
    ("低", "低"): "🔵",
}
EMOJI_THINKING = "🧠"   # 思考系タスクに追加
EMOJI_SIMPLE   = "✅"   # 単純作業タスクに追加
