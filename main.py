import os
import json
import asyncio
import websockets
import urllib.request
import urllib.error
from flask import Flask, request, render_template_string
from threading import Thread

# --- إعدادات Flask للـ Dashboard ---
app = Flask(__name__)

# المتغيرات اللي هتتغير من الـ Dashboard
config = {
    "custom_text": "ihh anyway ------- break",
    "ws_instance": None
}

# شكل لوحة التحكم (Dashboard)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Status Dashboard</title>
    <style>
        body { background: #121212; color: white; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1e1e1e; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); width: 400px; text-align: center; }
        input { width: 100%; padding: 10px; margin: 20px 0; border-radius: 5px; border: 1px solid #333; background: #2c2c2c; color: white; }
        button { background: #5865F2; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; }
        button:hover { background: #4752c4; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Update Discord Status</h2>
        <form method="POST">
            <input type="text" name="new_status" value="{{ current_status }}" placeholder="Enter new status...">
            <button type="submit">Update Status 🔥</button>
        </form>
        {% if msg %}<p style="color: #00ff00;">{{ msg }}</p>{% endif %}
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def home():
    msg = ""
    if request.method == 'POST':
        config["custom_text"] = request.form.get('new_status')
        msg = "Status Updated! Restarting Connection..."
        if config["ws_instance"]:
            asyncio.run_coroutine_threadsafe(config["ws_instance"].close(), loop)

    return render_template_string(HTML_TEMPLATE, current_status=config["custom_text"], msg=msg)

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- كود الديسكورد الأساسي ---
TOKEN = os.environ.get("TOKEN")
APP_ID = "1341185241800245291"

# 🔹 المعرفات الخاصة بالـ Seen التلقائي
TARGET_CHANNEL = "1353447802889437357"
TARGET_USER = "1249754394417696801"

def send_ack(channel_id, message_id):
    """إرسال طلب HTTP لقراءة الرسالة فورًا"""
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}/ack"
    req = urllib.request.Request(url, method="POST")
    req.add_header("Authorization", TOKEN)
    req.add_header("Content-Type", "application/json")
    
    # ديسكورد بيطلب جسم فارغ أو توكن نل عشان يثبت القراءة
    data = b'{"token": null}'
    try:
        with urllib.request.urlopen(req, data=data) as response:
            if response.status in [200, 204]:
                print(f"⚡ Auto-Seen triggered for message {message_id} in channel {channel_id}")
    except Exception as e:
        print(f"❌ Failed to send seen: {e}")

async def heartbit(ws, interval):
    while True:
        try:
            await asyncio.sleep(interval / 1000)
            await ws.send(json.dumps({"op": 1, "d": None}))
        except: break

async def onliner():
    url = "wss://gateway.discord.gg/?v=9&encoding=json"
    async with websockets.connect(url) as ws:
        config["ws_instance"] = ws
        data = json.loads(await ws.recv())
        interval = data['d']['heartbeat_interval']
        asyncio.create_task(heartbit(ws, interval))

        auth = {
            "op": 2,
            "d": {
                "token": TOKEN,
                "properties": {"$os": "Windows", "$browser": "Discord Client", "$device": ""},
                "presence": {
                    "status": "dnd",
                    "activities": [
                        {
                            "name": "𝖤𝗌𝖼𝖺𝗉𝗂่น𝗀 𝖱𝖾𝖺𝗅𝗂𝗍𝗒",
                            "type": 1,
                            "url": "https://twitch.tv/phantom053/about",
                            "application_id": APP_ID,
                            "assets": {} 
                        },
                        {
                            "name": "Custom Status",
                            "type": 4,
                            "state": config["custom_text"],
                            "emoji": {"name": "e_tired", "id": "1472371287845240915"}
                        }
                    ],
                    "since": 0, "afk": False
                }
            }
        }
        await ws.send(json.dumps(auth))
        print(f"✅ Active! Status: {config['custom_text']}")
        
        # 💣 حلقة استقبال الأحداث وفحص الرسائل الجديدة
        while True:
            msg = await ws.recv()
            msg_data = json.loads(msg)
            
            # التأكد إن الحدث هو استقبال رسالة جديدة
            if msg_data.get("op") == 0 and msg_data.get("t") == "MESSAGE_CREATE":
                d = msg_data.get("d", {})
                channel_id = d.get("channel_id")
                author_id = d.get("author", {}).get("id")
                message_id = d.get("id")
                
                # ⚠️ التحقق لو الرسالة مبعوتة من الشخص أو جوه الروم المحددة
                if channel_id == TARGET_CHANNEL or author_id == TARGET_USER:
                    current_loop = asyncio.get_event_loop()
                    # تشغيل طلب الـ Seen في خلفية منفصلة عشان السكربت ما يقفش
                    current_loop.run_in_executor(None, send_ack, channel_id, message_id)

async def main():
    while True:
        try:
            await onliner()
        except Exception as e:
            print(f"🚨 Lost connection, retrying... {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # تشغيل الفلاسك
    Thread(target=run_flask, daemon=True).start()
    # تشغيل الديسكورد
    loop.run_until_complete(main())
