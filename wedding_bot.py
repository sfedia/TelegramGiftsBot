import telebot
import json
from collections import defaultdict
from gift_manager import PeopleJSON, GiftsJSON, MessagesJSON
from telebot.types import *
import threading
import time
import os
import typing as tp


BOT_TOKEN = "..." # telegram api token here
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="MarkdownV2")

people = PeopleJSON()
gifts = GiftsJSON()
message_agent = MessagesJSON()
messages = message_agent.json


@bot.message_handler(commands = ["start", "help"])
def start_message(m):
    global people, gifts
    first_name = m.from_user.first_name if m.from_user.first_name else ""
    last_name = m.from_user.last_name if m.from_user.last_name else ""
    people.add_user(
        user_id = str(m.from_user.id),
        user_name = " ".join([first_name, last_name])
    )
    bot.reply_to(m, "*Привет\! ✋\nМы наш собрали свадебный виш\-лист здесь 👇*")
    send_available_gifts(m)


def send_available_gifts(m):
    global people, gifts
    first_name = m.from_user.first_name if m.from_user.first_name else ""
    last_name = m.from_user.last_name if m.from_user.last_name else ""
    available_gifts = gifts.get_available_gifts_for_user(
        people = people,
        user_id = str(m.from_user.id),
        user_name = " ".join([first_name, last_name])
    )
    for gft in available_gifts:
        send_gift_message(gft, str(m.from_user.id))
    people.json["users"][str(m.from_user.id)]["sent_once"] = True


def get_gift_data(gift_id):
    gift_list_dir = os.path.join("gift_list", gift_id)
    try:
        file_list = os.listdir(gift_list_dir)
    except FileNotFoundError:
        print(f"No directory for gift '{gift_id}'")
    ret = {
        "name": None,
        "desc": None,
        "images": []
    }
    for flname in file_list:
        if flname == "desc.md":
            ret["desc"] = open(os.path.join(gift_list_dir, "desc.md"), encoding="utf-8").read()
        elif flname == "name.md":
            ret["name"] = open(os.path.join(gift_list_dir, "name.md"), encoding="utf-8").read()
        elif "pic" in flname:
            ret["images"].append(os.path.join(gift_list_dir, flname))
    ret["summary"] = "\n\n".join(ret[key] for key in ("name", "desc") if ret[key]) + ("\n­" * 3)
    return ret


def get_checkmark() -> tp.BinaryIO:
    return open(os.path.join("gift_list", "checkmark.jpeg"), "rb")


def send_gift_message(gft, user_id):
    global messages, bot
    gift_data = get_gift_data(gft["id"])
    attachment = None
    text_content = gift_data["summary"]
    if gift_data["images"]:
        attachment = (gift_data["images"][0], "rb")
    button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Подарю!", callback_data=f"gift {gft['id']}")]]
    )
    msg_type = None
    if not attachment:
        bot_message = bot.send_message(
            user_id,
            text_content,
            open = attachment,
            reply_markup = button
        )
        msg_type = "pure_message"
    else:
        bot_message = bot.send_photo(
            user_id,
            photo = open(*attachment),
            caption = text_content,
            reply_markup = button,
            parse_mode = "MarkdownV2"
        )
        msg_type = "photo_message"

    messages[(user_id, gft["id"])] = {
        "chat_id": bot_message.chat.id,
        "message_id": bot_message.message_id,
        "message_type": msg_type
    }
    message_agent.json = messages
    message_agent.save()


@bot.callback_query_handler(func = lambda c: c.data.startswith("gift "))
def has_selected_gift(call):
    global people
    gift_id = call.data.lstrip("gift ")
    message_key = (str(call.from_user.id), gift_id)
    gift_message = messages[message_key]
    data = get_gift_data(gift_id)
    if gift_message["message_type"] == "pure_message":
        bot.edit_message_text(
            chat_id = gift_message["chat_id"],
            message_id = gift_message["message_id"],
            text = data["summary"]
        )
    else:
        bot.edit_message_caption(
            chat_id = gift_message["chat_id"],
            message_id = gift_message["message_id"],
            caption = f"✅{data['summary']}"
        )
    messages[(str(call.from_user.id), gift_id)] = False
    message_agent.json = messages
    message_agent.save()
    people.select_gift(gift_id, str(call.from_user.id))


def run_bot_polling():
    bot.infinity_polling()


def update_gift_messages():
    while True:
        gift_update_iteration()
        time.sleep(2)


def gift_update_iteration():
    global people, gifts, messages, bot
    for user_id in people.json["users"]:
        if not people.json["users"][str(user_id)]["sent_once"]:
            continue
        av_gifts = gifts.get_available_gifts_for_user(
            people = people,
            user_id = user_id,
            user_name = people.json["users"][user_id]["user_name"]
        )
        av_ids = [gft["id"] for gft in av_gifts]
        for msg_pair in messages:
            u_id, gift_id = msg_pair
            if u_id != user_id:
                continue
            if gift_id not in av_ids and messages[msg_pair] != False:
                try:
                    bot.delete_message(u_id, messages[msg_pair]["message_id"])
                except telebot.apihelper.ApiTelegramException:
                    pass
        for gft in av_gifts:
            if (user_id, gft["id"]) not in messages:
                send_gift_message(gft, user_id)



if __name__ =="__main__":
    t1 = threading.Thread(target=run_bot_polling)
    t2 = threading.Thread(target=update_gift_messages)
 
    t1.start()
    t2.start()
 
    t1.join()
    t2.join()
