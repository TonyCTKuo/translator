import os, re
from openai import OpenAI
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 設定你的Channel Access Token和Channel Secret
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

client = OpenAI(
    api_key = os.getenv('OPENAI_API_KEY')
)

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 判斷語言類型（簡單正則表示式檢查）
def detect_language(text):
    if re.search(r"[\u4e00-\u9fff]", text):  # 檢查是否包含中文字符
        return "zh"
    else:
        return "en"
    
# 翻譯函式
def translate_text(text, target_language):
    prompt = ""
    if target_language == "en":
        prompt = f"將以下中文翻譯成英文：{text}"
    elif target_language == "zh":
        prompt = f"將以下英文翻譯成繁體中文： {text}"

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    translated_text = response.choices[0].message.content.strip()
    return translated_text

# 定義 Webhook 端點
@app.route("/webhook", methods=["POST"])
def webhook():
    # 取得請求的簽名
    signature = request.headers["X-Line-Signature"]

    # 取得請求的內容
    body = request.get_data(as_text=True)
    app.logger.info(f"Request body: {body}")

    # 驗證簽名:
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# 處理訊息事件
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 取得發言者的 id
    user_id = event.source.user_id
    # 使用 get_profile 方法來獲取用戶的個人資料
    profile = line_bot_api.get_profile(user_id)
    # 取得用戶的暱稱
    display_name = profile.display_name

    # 回覆訊息
    user_message = event.message.text
    language = detect_language(user_message)  # 判斷語言類型

    # 根據語言類型決定翻譯方向
    if language == "zh":
        reply_head = f"{display_name} said: "
        translated_text = translate_text(user_message, target_language="en")
    else:
        reply_head = f"{display_name} 說: "
        translated_text = translate_text(user_message, target_language="zh")

    # 回應翻譯結果
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_head + translated_text)
    )

if __name__ == "__main__":
    port = int(
        os.environ.get("PORT", 5555)
    )  # 預設為 5555，但在 Azure 上會使用環境變數的 PORT
    app.run(host="0.0.0.0", port=port)
