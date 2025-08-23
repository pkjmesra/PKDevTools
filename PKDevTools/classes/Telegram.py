"""
The MIT License (MIT)

Copyright (c) 2023 pkjmesra

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""
# Use this token to access the HTTP API: <Token>
# Keep your token secure and store it safely, it can be used by anyone to control your bot.
# For a description of the Bot API, see this page:
# https://core.telegram.org/bots/api

# https://medium.com/codex/using-python-to-send-telegram-messages-in-3-simple-steps-419a8b5e5e2

import json

# Get from telegram
# See tutorial
# https://www.siteguarding.com/en/how-to-get-telegram-bot-api-token
import os
import urllib.parse
from io import BytesIO

import requests
from PIL import Image
from telegram import InputMediaDocument

from PKDevTools.classes.Environment import PKEnvironment
from PKDevTools.classes.log import default_logger
from PKDevTools.classes.OutputControls import OutputControls

# from io import BytesIO
# from PIL import Image


# URL_TELE = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
# **DOCU**
# 5.2 Configure chatID and tokes in Telegram
# Once the token has been obtained, the chatId of the users and the administrator must be obtained.
# The users only receive purchase and startup alerts, while the administrator receives the alerts of the users as well as possible problems.
# To get the chatId of each user run ztelegram_send_message_UptateUser.py and then write any message to the bot, the chadID appears both in the execution console and to the user.
# [>>> BOT] Message Send on 2022-11-08 22:30:31
# 	Text: You "User nickname " send me:
# "Hello world""
#  ChatId: "5058733760"
# 	From: Bot name
# 	Message ID: 915
# 	CHAT ID: 500000760
# -----------------------------------------------
# Pick up CHAT ID: 500000760
# With the chatId of the desired users, add them to the list LIST_PEOPLE_IDS_CHAT
#
Channel_Id = "00000"
chat_idADMIN = ""
botsUrl = ""
MAX_MSG_LENGTH = 4096
MAX_CAPTION_LENGTH = 1024
# chat_idUser1 = "563000000"
# chat_idUser2 = "207000000"
# chat_idUser3= "495000000"
LIST_PEOPLE_IDS_CHAT = [Channel_Id]


def initTelegram():
    global chat_idADMIN, botsUrl, Channel_Id, LIST_PEOPLE_IDS_CHAT, TOKEN
    if chat_idADMIN == "" or botsUrl == "":
        TOKEN = "00000000xxxxxxx"
        try:
            Channel_Id, TOKEN, chat_idADMIN, _ = get_secrets()
        except Exception as e:
            # default_logger().debug(e, exc_info=True)
            # print(
            #     "[+] Telegram token and secrets are not configured!\n[+] See https://github.com/pkjmesra/pkscreener#creating-your-own-telegram-channel-to-receive-your-own-alerts"
            # )
            pass
        Channel_Id = "-" + str(Channel_Id)
        LIST_PEOPLE_IDS_CHAT = [Channel_Id]
        botsUrl = f"https://api.telegram.org/bot{TOKEN}"


def get_secrets():
    return PKEnvironment().secrets


def is_token_telegram_configured():
    global chat_idADMIN, botsUrl, Channel_Id, LIST_PEOPLE_IDS_CHAT, TOKEN
    initTelegram()
    if TOKEN == "00000000xxxxxxx" or len(TOKEN) < 1:
        # print(
        #     "[+] There is no value for the telegram TOKEN. It is required to telegram someone.\n[+] See tutorial: https://www.siteguarding.com/en/how-to-get-telegram-bot-api-token"
        # )
        return False
    return True


def send_exception(ex, extra_mes=""):
    extra_mes + "   ** Exception **" + str(ex)
    if not is_token_telegram_configured():
        return


def send_message(
    message,
    userID=None,
    parse_type="HTML",
    list_png=None,
    retrial=False,
    reply_markup=None,
):
    """
    To use Telegram's sendMessage API with chat_id, text, parse_mode, and
    reply_markup, ensuring they are URL encoded, follow these steps:

    # 1. Basic API Structure

    Telegram's sendMessage API looks like this:
    https://api.telegram.org/bot<BOT_TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=<TEXT>&parse_mode=<PARSE_MODE>&reply_markup=<REPLY_MARKUP>
    However, special characters (like spaces, newlines, JSON in reply_markup) need to be URL encoded.

    # 2. Key Points

    urllib.parse.quote(json.dumps(reply_markup)): Ensures reply_markup is properly URL-encoded.
    requests.get(url, params=params): Automatically encodes parameters, but reply_markup needs manual encoding.
    Markdown or HTML formatting in text should also be escaped according to Telegram's rules.

    # 3. Example:

    import requests
    import urllib.parse
    import json

    BOT_TOKEN = "your_bot_token"
    CHAT_ID = "your_chat_id"
    TEXT = "Hello, *bold text*!"
    PARSE_MODE = "MarkdownV2"

    #Inline keyboard example
    reply_markup = {
        "inline_keyboard": [
            [{"text": "Click me!", "url": "https://example.com"}]
        ]
    }

    #Convert reply_markup to JSON and URL encode it
    reply_markup_encoded = urllib.parse.quote(json.dumps(reply_markup))

    #Construct URL
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {
        "chat_id": CHAT_ID,
        "text": TEXT,
        "parse_mode": PARSE_MODE,
        "reply_markup": reply_markup_encoded
    }

    #Send request
    response = requests.get(url, params=params)

    #Print response
    print(response.json())
    """
    initTelegram()
    # botsUrl = f"https://api.telegram.org/bot{TOKEN}"  # + "/sendMessage?chat_id={}&text={}".format(chat_idLUISL, message_aler, parse_mode="HTML")
    # url = botsUrl + "/sendMessage?chat_id={}&text={}&parse_mode={parse_mode}".format(chat_idLUISL, message_aler,parse_mode=PARSEMODE_MARKDOWN_V2)
    if not is_token_telegram_configured():
        return
    # Inline keyboard example
    # reply_markup = {
    #     "inline_keyboard": [
    #         [{"text": "Click me!", "url": "https://example.com"}]
    #     ]
    # }
    global chat_idADMIN, botsUrl, Channel_Id, LIST_PEOPLE_IDS_CHAT, TOKEN
    if userID is not None and userID != "":
        LIST_PEOPLE_IDS_CHAT = [int(str(userID).replace('"', ""))]
    reply_markup_encoded = ""
    if reply_markup is not None and len(reply_markup) > 0:
        # Convert reply_markup to JSON and URL encode it
        reply_markup_encoded = urllib.parse.quote(json.dumps(reply_markup))
    escaped_text = ""
    if message is not None and len(message) > 0:
        escaped_text = urllib.parse.quote(message)

    if list_png is None or any(elem is None for elem in list_png):
        resp = None
        for people_id in LIST_PEOPLE_IDS_CHAT:
            if len(reply_markup_encoded) > 0:
                url = (
                    botsUrl
                    + "/sendMessage?chat_id={}&text={}&reply_markup={reply_markup_encoded}&parse_mode={parse_mode}".format(
                        people_id,
                        escaped_text[:MAX_MSG_LENGTH],
                        reply_markup_encoded=reply_markup_encoded,
                        parse_mode=parse_type,
                    )
                )
            else:
                url = (
                    botsUrl
                    + "/sendMessage?chat_id={}&text={}&parse_mode={parse_mode}".format(
                        people_id, escaped_text[:MAX_MSG_LENGTH], parse_mode=parse_type
                    )
                )
            try:
                resp = requests.get(
                    url,
                    timeout=2,  # 2 sec timeout
                )  # headers={'Connection': 'Close'})
            except Exception as e:
                default_logger().debug(e, exc_info=True)
                if not retrial:
                    from time import sleep

                    sleep(2)
                    resp = send_message(
                        message=message,
                        userID=userID,
                        parse_type=parse_type,
                        list_png=list_png,
                        retrial=True,
                    )
        return resp
    # else:
    #     for people_id in LIST_PEOPLE_IDS_CHAT:
    #         resp_media = __send_media_group(people_id, list_png, caption=message, reply_to_message_id=None)
    #         # resp_intro = send_A_photo(botsUrl, people_id, open(list_png[0], 'rb'), text_html =message_aler)
    #         # message_id = int(re.search(r'\"message_id\":(\d*)\,\"from\"', str(resp_intro.content), re.IGNORECASE).group(1))
    #         # resp_respuesta = send_A_photo(botsUrl, people_id, open(list_png[1], 'rb'), text_html ="", message_id=message_id)
    #     # print(telegram_msg)
    #     # print(telegram_msg.content)


def send_photo(photoFilePath, message="", message_id=None,
               userID=None, retrial=False):
    initTelegram()
    if not is_token_telegram_configured():
        return
    OutputControls().printOutput(f"Sending message:{message}")
    method = "/sendPhoto"
    global chat_idADMIN, botsUrl, Channel_Id, LIST_PEOPLE_IDS_CHAT, TOKEN
    photo = open(photoFilePath, "rb")
    if message_id is not None:
        params = {
            "chat_id": (userID if userID is not None else Channel_Id),
            "caption": message[:MAX_CAPTION_LENGTH],
            "parse_mode": "HTML",
            "reply_to_message_id": message_id,
        }
    else:
        params = {
            "chat_id": (userID if userID is not None else Channel_Id),
            "caption": message[:MAX_CAPTION_LENGTH],
            "parse_mode": "HTML",
        }
    files = {"photo": photo}
    resp = None
    try:
        resp = requests.post(
            botsUrl + method,
            params,
            files=files,
            timeout=2 * 2,  # 2 sec timeout
        )  # headers={'Connection': 'Close'})
    except Exception as e:
        default_logger().debug(e, exc_info=True)
        if not retrial:
            from time import sleep

            sleep(2)
            resp = send_photo(
                photoFilePath=photoFilePath,
                message=message,
                message_id=message_id,
                userID=userID,
                retrial=True,
            )
    return resp


def send_document(
    documentFilePath, message="", message_id=None, retryCount=0, userID=None
):
    initTelegram()
    if not is_token_telegram_configured():
        return
    document = open(documentFilePath, "rb")
    global chat_idADMIN, botsUrl, Channel_Id, LIST_PEOPLE_IDS_CHAT, TOKEN
    if message_id is not None:
        params = {
            "chat_id": (userID if userID is not None else Channel_Id),
            "caption": message[:MAX_CAPTION_LENGTH],
            "parse_mode": "HTML",
            "reply_to_message_id": message_id,
        }
    else:
        params = {
            "chat_id": (userID if userID is not None else Channel_Id),
            "caption": message[:MAX_CAPTION_LENGTH],
            "parse_mode": "HTML",
        }
    files = {"document": document}
    method = "/sendDocument"
    resp = None
    try:
        resp = requests.post(
            botsUrl + method,
            params,
            files=files,
            timeout=3 * 2,  # 2 sec timeout
        )  # headers={'Connection': 'Close'})
    except Exception as e:
        default_logger().debug(e, exc_info=True)
        from time import sleep

        if retryCount <= 3:
            sleep(2 * (retryCount + 1))
            resp = send_document(
                documentFilePath, message, message_id, retryCount=retryCount + 1
            )
    return resp
    # content = response.content.decode("utf8")
    # js = json.loads(content)
    # print(js)


# https://stackoverflow.com/questions/58893142/how-to-send-telegram-mediagroup-with-caption-text
# https://stackoverflow.com/questions/74851187/send-multiple-files-to-a-telegram-channel-in-a-single-message-using-bot
def send_media_group(
    user,
    png_paths=[],
    png_album_caption=None,
    file_paths=[],
    file_captions=[],
    reply_to_message_id=None,
):
    """
    Use this method to send an album of photos. On success, an array of Messages that were sent is returned.
    :param user: chat id
    :param images: list of PIL images to send
    :param caption: caption of image
    :param reply_to_message_id: If the message is a reply, ID of the original message
    :return: response with the sent message
    """
    initTelegram()
    if not is_token_telegram_configured():
        return
    global TOKEN, Channel_Id
    SEND_MEDIA_GROUP = f"https://api.telegram.org/bot{TOKEN}/sendMediaGroup"
    files = {}
    media = []
    if len(png_paths) > 0:
        list_image_bytes = []
        list_image_bytes = [
            Image.open(x if os.sep in x else os.path.join(os.getcwd(), x))
            for x in png_paths
        ]
        for i, img in enumerate(list_image_bytes):
            if img is not None and img.size[0] > 0:
                with BytesIO() as output:
                    img.save(output, format="PNG")
                    output.seek(0)
                    name = png_paths[i].split(os.sep)[-1]
                    files[name] = output.read()
                    # a list of InputMediaPhoto. attach refers to the name of
                    # the file in the files dict
                    media.append(
    dict(
        type="document",
         media=f"attach://{name}"))
        media[0]["caption"] = png_album_caption[:MAX_CAPTION_LENGTH]
        media[0]["parse_mode"] = "HTML"

    if len(file_paths) > 0:
        fileIndex = 0
        prevMediaIndex = len(media)
        # From 2 to 10 items in one media group
        # https://core.telegram.org/bots/api#sendmediagroup
        # media_group = list()
        for f in file_paths:
            x = f if os.sep in f else os.path.join(os.getcwd(), f)
            filesize = os.stat(x).st_size if os.path.exists(x) else 0
            if filesize > 0:
                with open(x, "rb") as output:
                    # Up to 1024 characters.
                    # https://core.telegram.org/bots/api#inputmediadocument
                    caption = file_captions[fileIndex]
                    # After the len(fin.readlines()) file's current position
                    # will be at the end of the file. seek(0) sets the position
                    # to the begining of the file so we can read it again during
                    # sending.
                    # output.seek(0)
                    # media_group.append(InputMediaDocument(output, caption=caption))
                    name = file_paths[fileIndex].split(os.sep)[-1]
                    files[name] = output.read()
                    # a list of InputMediaDocument. attach refers to the name
                    # of the file in the files dict
                    media.append(
    dict(
        type="document",
         media=f"attach://{name}"))
                    media[len(media) -
     1]["caption"] = caption[:MAX_CAPTION_LENGTH]
                    media[len(media) - 1]["parse_mode"] = "HTML"
            fileIndex += 1
    if len(media) > 0:
        return requests.post(
            SEND_MEDIA_GROUP,
            data={
                "chat_id": (user if user is not None else Channel_Id),
                "media": json.dumps(media),
                "reply_to_message_id": reply_to_message_id,
            },
            files=files,
        )
    return None
