#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (c) 2boom 2023-24

import json
import socket, errno
import os
import ssl
import time
import requests
from schedule import every, repeat, run_pending
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

def getHostname():
	hostname = ""
	if os.path.exists('/proc/sys/kernel/hostname'):
		with open('/proc/sys/kernel/hostname', "r") as file:
			hostname = file.read().strip('\n')
		file.close()
	return hostname

def send_message(message : str):
	message = message.replace("\t", "")
	if TELEGRAM_ON:
		try:
			response = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})
		except requests.exceptions.RequestException as e:
			print("error:", e)
	if DISCORD_ON:
		try:
			response = requests.post(DISCORD_WEB, json={"content": message.replace("*", "**")})
		except requests.exceptions.RequestException as e:
			print("error:", e)
	if SLACK_ON:
		try:
			response = requests.post(SLACK_WEB, json = {"text": message})
		except requests.exceptions.RequestException as e:
			print("error:", e)
	message = message.replace("*", "")
	header = message[:message.index("\n")].rstrip("\n")
	message = message[message.index("\n"):].strip("\n")
	if GOTIFY_ON:
		try:
			response = requests.post(f"{GOTIFY_WEB}/message?token={GOTIFY_TOKEN}",\
			json={'title': header, 'message': message, 'priority': 0})
		except requests.exceptions.RequestException as e:
			print("error:", e)
	if NTFY_ON:
		try:
			response = requests.post(f"{NTFY_WEB}/{NTFY_SUB}", data=message.encode(encoding='utf-8'), headers={"Title": header})
		except requests.exceptions.RequestException as e:
			print("error:", e)
	if PUSHBULLET_ON:
		try:
			response = requests.post('https://api.pushbullet.com/v2/pushes',\
			json={'type': 'note', 'title': header, 'body': message},\
			headers={'Access-Token': PUSHBULLET_API, 'Content-Type': 'application/json'})
		except requests.exceptions.RequestException as e:
			print("error:", e)

if __name__ == "__main__":	
	CURRENT_PATH =  os.path.dirname(os.path.realpath(__file__))
	HOSTNAME = getHostname()
	ssl._create_default_https_context = ssl._create_unverified_context
	TELEGRAM_ON = DISCORD_ON = GOTIFY_ON = NTFY_ON = SLACK_ON = PUSHBULLET_ON = False
	TOKEN = CHAT_ID = DISCORD_WEB = GOTIFY_WEB = GOTIFY_TOKEN = NTFY_WEB = NTFY_SUB = PUSHBULLET_API = SLACK_WEB = MESSAGING_SERVICE = ""
	if os.path.exists(f"{CURRENT_PATH}/config.json"):
		parsed_json = json.loads(open(f"{CURRENT_PATH}/config.json", "r").read())
		TELEGRAM_ON = parsed_json["TELEGRAM"]["ON"]
		DISCORD_ON = parsed_json["DISCORD"]["ON"]
		GOTIFY_ON = parsed_json["GOTIFY"]["ON"]
		NTFY_ON = parsed_json["NTFY"]["ON"]
		PUSHBULLET_ON = parsed_json["PUSHBULLET"]["ON"]
		SLACK_ON = parsed_json["SLACK"]["ON"]
		if TELEGRAM_ON:
			TOKEN = parsed_json["TELEGRAM"]["TOKEN"]
			CHAT_ID = parsed_json["TELEGRAM"]["CHAT_ID"]
			MESSAGING_SERVICE += "- messenging: Telegram,\n"
		if DISCORD_ON:
			DISCORD_WEB = parsed_json["DISCORD"]["WEB"]
			MESSAGING_SERVICE += "- messenging: Discord,\n"
		if GOTIFY_ON:
			GOTIFY_WEB = parsed_json["GOTIFY"]["WEB"]
			GOTIFY_TOKEN = parsed_json["GOTIFY"]["TOKEN"]
			MESSAGING_SERVICE += "- messenging: Gotify,\n"
		if NTFY_ON:
			NTFY_WEB = parsed_json["NTFY"]["WEB"]
			NTFY_SUB = parsed_json["NTFY"]["SUB"]
			MESSAGING_SERVICE += "- messenging: Ntfy,\n"
		if PUSHBULLET_ON:
			PUSHBULLET_API = parsed_json["PUSHBULLET"]["API"]
			MESSAGING_SERVICE += "- messenging: Pushbullet,\n"
		if SLACK_ON:
			SLACK_WEB = parsed_json["SLACK"]["WEB"]
			MESSAGING_SERVICE += "- messenging: Slack,\n"
		MIN_REPEAT = int(parsed_json["MIN_REPEAT"])
		send_message(f"*{HOSTNAME}* (hosts)\nhosts monitor:\n{MESSAGING_SERVICE}- polling period: {MIN_REPEAT} minute(s).")
	else:
		print("config.json not nound")

@repeat(every(MIN_REPEAT).minutes)
def web_check():
	TMP_FILE = "/tmp/status_web.tmp"
	web_list = []
	count_hosts = 0
	RED_DOT, GREEN_DOT  = "\U0001F534", "\U0001F7E2"
	status_message = old_status_str = new_status_str = ""
	if os.path.exists(f"{CURRENT_PATH}/url_list.json"):
		parsed_json = json.loads(open(f"{CURRENT_PATH}/url_list.json", "r").read())
		web_list = parsed_json["list"]
		total_hosts = len(web_list)
		if not os.path.exists(TMP_FILE) or total_hosts != os.path.getsize(TMP_FILE):
			with open(TMP_FILE, "w") as file:
				old_status_str = "0" * total_hosts
				file.write(old_status_str)
			file.close()
		with open(TMP_FILE, "r") as file:
			old_status_str = file.read()
			li = list(old_status_str)
		file.close()
		for i in range(total_hosts):
			req = Request(web_list[i][0], headers={'User-Agent': 'Mozilla/5.0'})
			try:
				response = urlopen(req)#timeout
			except HTTPError as e:
				li[i] = "1"
				status_message += f"{RED_DOT} *{web_list[i][1]}*, error: {e.code}\n"
			except URLError as e:
				li[i] = "1"
				status_message += f"{RED_DOT} *{web_list[i][1]}*, reason: {e.reason}\n"		
			else:
				li[i] = "0"
				count_hosts += 1
		new_status_str = "".join(li)
		bad_hosts = total_hosts - count_hosts
		if count_hosts == total_hosts:
			status_message = f"{GREEN_DOT} monitoring host(s):\n|ALL| - {total_hosts}, |OK| - {count_hosts}, |BAD| - {bad_hosts}"
		else:
			status_message = f"monitoring host(s):\n|ALL| - {total_hosts}, |OK| - {count_hosts}, |BAD| - {bad_hosts}\n{status_message}"
		if old_status_str != new_status_str:
			with open(TMP_FILE, "w") as file:
				file.write(new_status_str)
			file.close()
			send_message(f"*{HOSTNAME}* (hosts)\n{status_message}")
	else:
		print("url_list.json not nound")
	
while True:
    run_pending()
    time.sleep(1)
