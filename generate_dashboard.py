"""
Google Sheetsからタスクを読み込み、ダッシュボードHTMLを生成する
"""

import json
import os
import warnings
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

warnings.filterwarnings("ignore")

JST = ZoneInfo("Asia/Tokyo")

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from config import SPREADSHEET_ID, SHEET_NAME, EMOJI_MAP, EMOJI_THINKING, EMOJI_SIMPLE

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_credentials():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        info = json.loads(creds_json)
    else:
        with open("credentials.json") as f:
            info = json.load(f)
    return Credentials.from_service_account_info(info, scopes=SCOPES)


def fetch_tasks(creds):
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
        padded = (row + [""] * 8)[:8]
        task_name, importance, urgency, task_type, duration_str, deadline_str, status, memo = padded
        if not task_name.strip():
            continue
        try:
            duration = int(duration_str)
        except ValueError:
            duration = 30
        try:
            deadline = datetime.strptime(deadline_str.strip(), "%Y/%m/%d").date()
        except ValueError:
            deadline = None

        days_left = (deadline - datetime.now(JST).date()).days if deadline else None
        tasks.append({
            "name": task_name.strip(),
            "importance": importance.strip(),
            "urgency": urgency.strip(),
            "task_type": task_type.strip(),
            "duration": duration,
            "deadline": deadline,
            "days_left": days_left,
            "status": status.strip(),
            "memo": memo.strip(),
        })
    return tasks


def deadline_color(days_left):
    if days_left is None:
        return {"bar": "bg-slate-300", "badge": "bg-slate-400", "border": "border-slate-100", "label": "期限なし", "section": "none"}
    if days_left <= 3:
        return {"bar": "bg-red-500", "badge": "bg-red-500", "border": "border-red-100", "label": f"残り{days_left}日", "section": "red"}
    if days_left <= 7:
        return {"bar": "bg-amber-400", "badge": "bg-amber-400", "border": "border-amber-100", "label": f"残り{days_left}日", "section": "amber"}
    return {"bar": "bg-blue-400", "badge": "bg-blue-400", "border": "border-blue-100", "label": f"残り{days_left}日", "section": "blue"}


def quadrant_info(importance, urgency):
    if importance == "高" and urgency == "高":
        return {"label": "すぐやる", "color": "text-violet-600 bg-violet-50"}
    if importance == "高":
        return {"label": "計画", "color": "text-teal-600 bg-teal-50"}
    if urgency == "高":
        return {"label": "任せる", "color": "text-orange-500 bg-orange-50"}
    return {"label": "後回し", "color": "text-slate-400 bg-slate-50"}


def make_emoji(importance, urgency, task_type):
    base = EMOJI_MAP.get((importance, urgency), "🔵")
    kind = EMOJI_THINKING if task_type == "思考系" else EMOJI_SIMPLE
    return f"{base}{kind}"


def task_card_html(task):
    dc = deadline_color(task["days_left"])
    qi = quadrant_info(task["importance"], task["urgency"])
    emoji = make_emoji(task["importance"], task["urgency"], task["task_type"])
    deadline_str = task["deadline"].strftime("%-m/%-d") if task["deadline"] else "期限なし"
    status_cls = "opacity-50" if task["status"] == "完了" else ""
    check_cls = "border-slate-200 bg-slate-100" if task["status"] == "完了" else f"border-slate-300"

    return f"""
<div class="mx-3 mb-2 flex rounded-xl overflow-hidden border {dc['border']} hover:shadow-sm transition-all cursor-pointer {status_cls}">
  <div class="w-1.5 {dc['bar']} flex-shrink-0"></div>
  <div class="flex-1 px-3 py-2.5 bg-white">
    <div class="flex items-start gap-2">
      <button class="w-4 h-4 rounded-full border-2 {check_cls} flex-shrink-0 mt-0.5"></button>
      <p class="text-xs font-bold text-slate-900 leading-snug flex-1">{emoji} {task['name']}</p>
    </div>
    <div class="flex items-center gap-2 mt-2 ml-6 flex-wrap">
      <span class="text-[10px] font-black text-white {dc['badge']} px-2 py-0.5 rounded-full">{dc['label']}</span>
      <span class="text-[10px] text-slate-400">{deadline_str}</span>
      <span class="text-[10px] {qi['color']} px-1.5 py-0.5 rounded font-bold">{qi['label']}</span>
      <span class="text-[10px] text-slate-400">{task['duration']}分</span>
    </div>
  </div>
</div>"""


def quadrant_card_html(task):
    dc = deadline_color(task["days_left"])
    emoji = make_emoji(task["importance"], task["urgency"], task["task_type"])
    deadline_str = task["deadline"].strftime("%-m/%-d") if task["deadline"] else "期限なし"
    status_cls = "opacity-40" if task["status"] == "完了" else ""

    return f"""
<div class="rounded-xl overflow-hidden border border-slate-100 hover:shadow-sm transition-all cursor-pointer flex {status_cls}">
  <div class="w-2 {dc['bar']} flex-shrink-0"></div>
  <div class="flex-1 px-3 py-2.5 bg-white">
    <div class="flex items-start gap-2">
      <button class="w-4 h-4 rounded-full border-2 border-slate-300 flex-shrink-0 mt-0.5"></button>
      <div>
        <p class="text-xs font-bold text-slate-900 leading-snug mb-1.5">{emoji} {task['name']}</p>
        <span class="inline-flex items-center gap-1 text-xs font-black text-white {dc['badge']} px-2.5 py-1 rounded-lg">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          {dc['label']} &nbsp;·&nbsp; {deadline_str}
        </span>
      </div>
    </div>
  </div>
</div>"""


def generate_html(tasks):
    today = datetime.now(JST).date()
    updated_at = datetime.now(JST).strftime("%Y/%m/%d %H:%M")

    # 完了タスクはダッシュボードに表示しない
    active = [t for t in tasks if t["status"] != "完了"]

    order = {"高": 0, "中": 1, "低": 2}
    def sort_key(t):
        return (order.get(t["importance"], 2), order.get(t["urgency"], 2), t["days_left"] if t["days_left"] is not None else 999)

    sorted_tasks = sorted(active, key=sort_key)

    red_tasks   = [t for t in sorted_tasks if deadline_color(t["days_left"])["section"] == "red"]
    amber_tasks = [t for t in sorted_tasks if deadline_color(t["days_left"])["section"] == "amber"]
    blue_tasks  = [t for t in sorted_tasks if deadline_color(t["days_left"])["section"] in ("blue", "none")]

    # quadrants
    q1 = [t for t in active if t["importance"] == "高" and t["urgency"] == "高"]
    q2 = [t for t in active if t["importance"] == "高" and t["urgency"] != "高"]
    q3 = [t for t in active if t["importance"] != "高" and t["urgency"] == "高"]

    # today suggestion from Q2
    suggest = sorted(q2, key=sort_key)[0] if q2 else None

    red_count   = len([t for t in active if deadline_color(t["days_left"])["section"] == "red"])
    amber_count = len([t for t in active if deadline_color(t["days_left"])["section"] == "amber"])
    blue_count  = len([t for t in active if deadline_color(t["days_left"])["section"] in ("blue", "none")])

    list_html = ""
    if red_tasks:
        list_html += """<div class="px-3 pt-3 pb-1"><div class="flex items-center gap-1.5 mb-2"><div class="w-2.5 h-2.5 rounded-full bg-red-500"></div><span class="text-[10px] font-black text-red-500 tracking-wider uppercase">要対応</span></div></div>"""
        list_html += "".join(task_card_html(t) for t in red_tasks)
    if amber_tasks:
        list_html += """<div class="px-3 pt-3 pb-1"><div class="flex items-center gap-1.5 mb-2"><div class="w-2.5 h-2.5 rounded-full bg-amber-400"></div><span class="text-[10px] font-black text-amber-500 tracking-wider uppercase">今週中</span></div></div>"""
        list_html += "".join(task_card_html(t) for t in amber_tasks)
    if blue_tasks:
        list_html += """<div class="px-3 pt-3 pb-1"><div class="flex items-center gap-1.5 mb-2"><div class="w-2.5 h-2.5 rounded-full bg-blue-400"></div><span class="text-[10px] font-black text-blue-500 tracking-wider uppercase">余裕あり</span></div></div>"""
        list_html += "".join(task_card_html(t) for t in blue_tasks)

    q4 = [t for t in active if t["importance"] != "高" and t["urgency"] != "高"]

    q1_html = "".join(quadrant_card_html(t) for t in q1) or '<p class="text-xs text-slate-300 px-2 py-4 text-center">タスクなし</p>'
    q2_html = "".join(quadrant_card_html(t) for t in q2) or '<p class="text-xs text-slate-300 px-2 py-4 text-center">タスクなし</p>'
    q3_html = "".join(quadrant_card_html(t) for t in q3) or '<p class="text-xs text-slate-300 px-2 py-4 text-center">タスクなし</p>'
    q4_html = "".join(quadrant_card_html(t) for t in q4) or '<p class="text-xs text-slate-300 px-2 py-4 text-center">タスクなし</p>'

    suggest_html = ""
    if suggest:
        dc = deadline_color(suggest["days_left"])
        emoji = make_emoji(suggest["importance"], suggest["urgency"], suggest["task_type"])
        deadline_str = suggest["deadline"].strftime("%-m/%-d") if suggest["deadline"] else "期限なし"
        suggest_html = f"""
<div class="mx-3 mt-3 rounded-xl bg-teal-50 border-2 border-teal-300 overflow-hidden">
  <div class="flex items-center gap-2 px-3 py-2 border-b border-teal-200">
    <span class="text-xs">✨</span>
    <span class="text-xs font-black text-teal-700">今日やってみましょう</span>
  </div>
  <div class="px-3 py-3 flex items-start gap-3">
    <div class="w-8 h-8 rounded-lg bg-teal-600 flex items-center justify-center flex-shrink-0 text-sm">🎯</div>
    <div>
      <p class="text-sm font-black text-slate-900 leading-snug mb-1.5">{emoji} {suggest['name']}</p>
      <p class="text-[11px] text-teal-600 leading-relaxed mb-2">緊急ではないが重要なタスクです。今日少し時間を取ってみましょう。（目安: {suggest['duration']}分）</p>
      <span class="inline-flex items-center gap-1 text-xs font-black text-white {dc['badge']} px-2.5 py-1 rounded-lg">{dc['label']} &nbsp;·&nbsp; {deadline_str}</span>
    </div>
  </div>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>マイタスク ダッシュボード</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>tailwind.config = {{ theme: {{ extend: {{ fontFamily: {{ sans: ['"Noto Sans JP"', 'sans-serif'] }} }} }} }}</script>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700;900&display=swap" rel="stylesheet">
  <script>
    function showTab(tab) {{
      ['list','matrix'].forEach(function(t) {{
        var el = document.getElementById('mob-tab-' + t);
        var btn = document.getElementById('mob-btn-' + t);
        if (t === tab) {{
          el.classList.remove('hidden');
          btn.classList.add('text-violet-700','border-b-2','border-violet-600');
          btn.classList.remove('text-slate-400');
        }} else {{
          el.classList.add('hidden');
          btn.classList.remove('text-violet-700','border-b-2','border-violet-600');
          btn.classList.add('text-slate-400');
        }}
      }});
    }}
  </script>
</head>
<body class="bg-slate-100 min-h-screen" style="font-family:'Noto Sans JP',sans-serif;">

<!-- ===== MOBILE ===== -->
<div class="md:hidden flex flex-col h-screen">
  <header class="bg-white border-b border-slate-200 px-4 pt-3 pb-2 flex-shrink-0">
    <p class="text-[10px] text-slate-400">{today.strftime("%Y年%-m月%-d日")} &nbsp;·&nbsp; 更新: {updated_at}</p>
    <div class="flex items-center justify-between mt-1">
      <h1 class="text-base font-black text-slate-900">マイタスク</h1>
      <div class="flex gap-1.5">
        <span class="bg-red-500 text-white text-[10px] font-black px-2 py-0.5 rounded-full">🔴 {red_count}</span>
        <span class="bg-amber-400 text-white text-[10px] font-black px-2 py-0.5 rounded-full">🟡 {amber_count}</span>
        <span class="bg-blue-400 text-white text-[10px] font-black px-2 py-0.5 rounded-full">🔵 {blue_count}</span>
      </div>
    </div>
  </header>

  <!-- Tab bar -->
  <div class="bg-white border-b border-slate-200 flex flex-shrink-0">
    <button id="mob-btn-list" onclick="showTab('list')" class="flex-1 py-2.5 text-sm font-bold text-violet-700 border-b-2 border-violet-600">📋 リスト</button>
    <button id="mob-btn-matrix" onclick="showTab('matrix')" class="flex-1 py-2.5 text-sm font-bold text-slate-400">🎯 マトリックス</button>
  </div>

  <!-- Tab content -->
  <div class="flex-1 overflow-hidden">
    <!-- List tab -->
    <div id="mob-tab-list" class="h-full overflow-y-auto pb-4">
      {list_html}
    </div>

    <!-- Matrix tab (stacked vertically) -->
    <div id="mob-tab-matrix" class="h-full overflow-y-auto p-3 pb-6 space-y-3 hidden">
      {suggest_html}
      <!-- Q1 -->
      <div class="bg-white rounded-2xl border-2 border-violet-300 overflow-hidden">
        <div class="px-4 py-2.5 bg-violet-600 flex items-center justify-between">
          <div class="flex items-center gap-2"><span class="text-white">🔥</span><span class="text-sm font-black text-white">すぐやる</span></div>
          <span class="text-[10px] text-violet-200 font-bold">緊急 × 重要</span>
        </div>
        <div class="p-3 space-y-2">{q1_html}</div>
      </div>
      <!-- Q2 -->
      <div class="bg-white rounded-2xl border-2 border-teal-400 overflow-hidden">
        <div class="px-4 py-2.5 bg-teal-600 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-white">⭐</span>
            <span class="text-sm font-black text-white">計画してやる</span>
            <span class="text-[10px] text-teal-100 bg-teal-500 px-2 py-0.5 rounded-full font-bold">最重要</span>
          </div>
          <span class="text-[10px] text-teal-200 font-bold">余裕 × 重要</span>
        </div>
        <div class="p-3 space-y-2">{q2_html}</div>
      </div>
      <!-- Q3 -->
      <div class="bg-white rounded-2xl border-2 border-orange-300 overflow-hidden">
        <div class="px-4 py-2.5 bg-orange-500 flex items-center justify-between">
          <div class="flex items-center gap-2"><span class="text-white">📤</span><span class="text-sm font-black text-white">誰かに任せる</span></div>
          <span class="text-[10px] text-orange-100 font-bold">緊急 × 重要でない</span>
        </div>
        <div class="p-3 space-y-2">{q3_html}</div>
      </div>
      <!-- Q4 -->
      <div class="bg-white rounded-2xl border-2 border-slate-200 overflow-hidden opacity-70">
        <div class="px-4 py-2 bg-slate-400 flex items-center justify-between">
          <div class="flex items-center gap-2"><span class="text-white text-sm">🗄️</span><span class="text-sm font-black text-white">後回しor削除</span></div>
          <span class="text-[10px] text-slate-100 font-bold">余裕 × 重要でない</span>
        </div>
        <div class="p-3 space-y-2">{q4_html}</div>
      </div>
    </div>
  </div>
</div>

<!-- ===== DESKTOP ===== -->
<div class="hidden md:flex h-screen overflow-hidden">

  <!-- Nav -->
  <aside class="w-14 bg-slate-900 flex flex-col items-center py-4 gap-5 flex-shrink-0">
    <div class="w-8 h-8 rounded-lg bg-white flex items-center justify-center mb-2 text-sm">✅</div>
    <div class="w-9 h-9 rounded-xl bg-white/10 flex items-center justify-center text-white text-sm">📋</div>
    <div class="w-9 h-9 rounded-xl flex items-center justify-center text-slate-400 text-sm">📅</div>
    <div class="w-9 h-9 rounded-xl flex items-center justify-center text-slate-400 text-sm">📊</div>
  </aside>

  <!-- Todo list -->
  <div class="w-72 bg-white border-r border-slate-200 flex flex-col flex-shrink-0">
    <div class="px-4 py-4 border-b border-slate-100">
      <div class="flex items-center justify-between mb-1">
        <h2 class="text-sm font-black text-slate-900">全タスク</h2>
        <span class="text-[10px] text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">{len(active)}件</span>
      </div>
      <p class="text-[11px] text-slate-400">緊急度の高い順</p>
    </div>
    <div class="px-4 py-2.5 border-b border-slate-100 flex items-center gap-3">
      <div class="flex items-center gap-1.5"><div class="w-3 h-3 rounded-full bg-red-500"></div><span class="text-[10px] font-bold text-slate-500">〜3日</span></div>
      <div class="flex items-center gap-1.5"><div class="w-3 h-3 rounded-full bg-amber-400"></div><span class="text-[10px] font-bold text-slate-500">4〜7日</span></div>
      <div class="flex items-center gap-1.5"><div class="w-3 h-3 rounded-full bg-blue-400"></div><span class="text-[10px] font-bold text-slate-500">8日〜</span></div>
    </div>
    <div class="flex-1 overflow-y-auto pb-4">{list_html}</div>
  </div>

  <!-- Main matrix -->
  <div class="flex-1 flex flex-col overflow-hidden">
    <header class="bg-white border-b border-slate-200 px-5 py-3.5 flex items-center justify-between flex-shrink-0">
      <div>
        <p class="text-[11px] text-slate-400">{today.strftime("%Y年%-m月%-d日")} &nbsp;·&nbsp; 最終更新: {updated_at}</p>
        <h1 class="text-base font-black text-slate-900">重要度 × 緊急度マトリックス</h1>
      </div>
      <div class="flex items-center gap-2">
        <div class="flex items-center gap-1.5 bg-red-500 text-white px-3 py-1.5 rounded-lg text-xs font-black">🔴 要対応 {red_count}件</div>
        <div class="flex items-center gap-1.5 bg-amber-400 text-white px-3 py-1.5 rounded-lg text-xs font-black">🟡 今週中 {amber_count}件</div>
        <div class="flex items-center gap-1.5 bg-blue-400 text-white px-3 py-1.5 rounded-lg text-xs font-black">🔵 余裕あり {blue_count}件</div>
      </div>
    </header>

    <div class="flex-1 overflow-auto p-4">
      <div class="flex mb-2 pl-24">
        <div class="flex-1 text-center text-xs font-black text-slate-500">⚡ 緊急</div>
        <div class="flex-1 text-center text-xs font-bold text-slate-300">緊急でない</div>
      </div>
      <div class="flex gap-0" style="height:calc(100vh - 160px);">
        <div class="w-24 flex flex-col flex-shrink-0 gap-3">
          <div class="flex-1 flex items-center justify-center"><span class="text-xs font-black text-slate-500" style="writing-mode:vertical-rl;transform:rotate(180deg)">重要</span></div>
          <div class="flex-1 flex items-center justify-center"><span class="text-xs font-bold text-slate-300" style="writing-mode:vertical-rl;transform:rotate(180deg)">重要でない</span></div>
        </div>
        <div class="flex-1 flex gap-3">
          <!-- Left col: Q1 + Q3 -->
          <div class="flex-1 flex flex-col gap-3">
            <div class="flex-1 bg-white rounded-2xl border-2 border-violet-300 flex flex-col overflow-hidden">
              <div class="px-4 py-2.5 bg-violet-600 flex items-center justify-between">
                <div class="flex items-center gap-2"><span class="text-white">🔥</span><span class="text-sm font-black text-white">すぐやる</span></div>
                <span class="text-[10px] text-violet-200 font-bold">緊急 × 重要</span>
              </div>
              <div class="p-3 flex-1 space-y-2 overflow-auto">{q1_html}</div>
            </div>
            <div class="flex-1 bg-white rounded-2xl border-2 border-orange-300 flex flex-col overflow-hidden">
              <div class="px-4 py-2.5 bg-orange-500 flex items-center justify-between">
                <div class="flex items-center gap-2"><span class="text-white">📤</span><span class="text-sm font-black text-white">誰かに任せる</span></div>
                <span class="text-[10px] text-orange-100 font-bold">緊急 × 重要でない</span>
              </div>
              <div class="p-3 flex-1 space-y-2 overflow-auto">{q3_html}</div>
            </div>
          </div>
          <!-- Right col: Q2 (large) + Q4 (small) -->
          <div class="flex-1 flex flex-col gap-3">
            <div class="bg-white rounded-2xl border-2 border-teal-400 flex flex-col overflow-hidden" style="flex:2;">
              <div class="px-4 py-3 bg-teal-600 flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="text-white">⭐</span>
                  <span class="text-sm font-black text-white">計画してやる</span>
                  <span class="text-[10px] text-teal-100 bg-teal-500 px-2 py-0.5 rounded-full font-bold">最重要</span>
                </div>
                <span class="text-[10px] text-teal-200 font-bold">余裕あり × 重要</span>
              </div>
              {suggest_html}
              <div class="p-3 flex-1 space-y-2 overflow-auto">
                {"" if not suggest_html else '<p class="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1 pt-1">その他のタスク</p>'}
                {q2_html}
              </div>
            </div>
            <div class="bg-white rounded-2xl border-2 border-slate-200 flex flex-col overflow-hidden" style="flex:1;">
              <div class="px-4 py-2 bg-slate-400 flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="text-white text-sm">🗄️</span>
                  <span class="text-sm font-black text-white">後回しor削除</span>
                </div>
                <span class="text-[10px] text-slate-100 font-bold">余裕あり × 重要でない</span>
              </div>
              <div class="p-3 flex-1 space-y-2 overflow-auto opacity-70">{q4_html}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

</body>
</html>"""


def main():
    print("=== ダッシュボード生成 ===")
    creds = get_credentials()
    tasks = fetch_tasks(creds)
    print(f"タスク読み込み: {len(tasks)}件")
    html = generate_html(tasks)
    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("docs/index.html を生成しました")


if __name__ == "__main__":
    main()
