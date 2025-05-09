from fastapi import FastAPI, Form, BackgroundTasks
import requests
from ics import Calendar
from datetime import datetime, timedelta
import pytz

app = FastAPI()

def send_calendar_response(response_url: str):
    tz = pytz.timezone("Asia/Tokyo")
    now = datetime.now(tz)
    one_month_later = now + timedelta(days=30)

    calendars = [
        ("https://calendar.google.com/calendar/ical/86527e6d569ded6d0b4f284f5b5189a6ee7265363abd1e4ee754de1179bc6a89%40group.calendar.google.com/public/basic.ics", "開放"),
        ("https://calendar.google.com/calendar/ical/4d8ee5da96694f76fd6a794fabaab800a541b64d79e78f30af68a45b2574e85f%40group.calendar.google.com/public/basic.ics", "コース閉鎖時間")
    ]

    # 英語→日本語の曜日マッピング
    weekday_jp = {
        "Mon": "月",
        "Tue": "火",
        "Wed": "水",
        "Thu": "木",
        "Fri": "金",
        "Sat": "土",
        "Sun": "日"
    }

    closure_events = []
    open_events = []

    for ics_url, keyword in calendars:
        response = requests.get(ics_url)
        if response.status_code == 200:
            calendar = Calendar(response.text)
            for event in calendar.events:
                event_start = event.begin.astimezone(tz)
                event_end = event.end.astimezone(tz) if event.end else None

                if now <= event_start <= one_month_later and keyword in event.name:
                    # 曜日を取得
                    weekday = weekday_jp[event_start.strftime("%a")]

                    if "コース閉鎖時間" in event.name:
                        if "未定" in event.name:
                            closure_events.append(f"{event_start.month}月{event_start.day}日({weekday}) 未定")
                        else:
                            if event_end:
                                closure_events.append(
                                    f"{event_start.month}月{event_start.day}日({weekday}) {event_start.hour}:{str(event_start.minute).zfill(2)}~{event_end.hour}:{str(event_end.minute).zfill(2)}"
                                )
                            else:
                                closure_events.append(f"{event_start.month}月{event_start.day}日({weekday})")
                    elif "開放" in event.name:
                        open_events.append(f"{event_start.month}月{event_start.day}日({weekday})")

    closure_events.sort()
    open_events.sort()

    message_parts = []

    if closure_events:
        message_parts.append("【閉鎖】")
        message_parts.extend(closure_events)

    if open_events:
        message_parts.append("\n【開放】")
        message_parts.extend(open_events)

    if not message_parts:
        message = "1ヶ月以内に対象の予定はありません。"
    else:
        message = "\n".join(message_parts)

    requests.post(response_url, json={
        "response_type": "in_channel",
        "text": message
    })



@app.post("/slack/events")
async def slack_events(
    background_tasks: BackgroundTasks,
    token: str = Form(...),
    command: str = Form(...),
    text: str = Form(...),
    response_url: str = Form(...)
):
    # すぐにSlackへ「リクエスト受けたよ！」を返す
    background_tasks.add_task(send_calendar_response, response_url)
    return {"response_type": "ephemeral", "text": "1ヶ月以内のコース状況を取得中です..."}
