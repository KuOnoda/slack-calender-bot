from fastapi import FastAPI, Form
import requests
from ics import Calendar
from datetime import datetime, timedelta
import pytz

app = FastAPI()

# 公開カレンダーの.ics URL
ics_url = "https://calendar.google.com/calendar/ical/86527e6d569ded6d0b4f284f5b5189a6ee7265363abd1e4ee754de1179bc6a89%40group.calendar.google.com/public/basic.ics"

@app.post("/slack/events")
async def slack_events(
    token: str = Form(...),
    command: str = Form(...),
    text: str = Form(...),
    response_url: str = Form(...)
):
    tz = pytz.timezone("Asia/Tokyo")
    now = datetime.now(tz)
    one_month_later = now + timedelta(days=30)
    response = requests.get(ics_url)
    filtered_events = []

    if response.status_code == 200:
        calendar = Calendar(response.text)
        for event in calendar.events:
            event_start = event.begin.astimezone(tz)
            if now <= event_start <= one_month_later and "開放" in event.name:
                filtered_events.append(f"{event_start.date()} : {event.name}")

    if filtered_events:
        message = "\n".join(filtered_events)
    else:
        message = "1ヶ月以内に「開放」の予定はありません。"

    requests.post(response_url, json={
        "response_type": "in_channel",
        "text": message
    })

    return {"status": "ok"}
