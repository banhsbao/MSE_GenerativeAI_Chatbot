from flask import Flask, render_template, request, jsonify
import requests
import json

import os

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello, this is chatbox server"


@app.route("/webhook", methods=["GET", "POST"])
def get_method():
    if request.method == "GET":
        return handle_get(request)
    elif request.method == "POST":
        return handle_post(request)
    else:
        return jsonify({"status": 405, "body": "Method Not Allowed"}), 405


def handle_get(request):
    query_params = request.args
    if query_params and query_params.get("hub.verify_token") == VERIFY_TOKEN:
        return query_params["hub.challenge"], 200
    else:
        return jsonify({"status": 403, "body": "Forbidden"}), 403


def handle_post(request):
    try:
        body = request.get_json()
        for entry in body.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                if "message" in messaging_event:
                    sender_id = messaging_event["sender"]["id"]
                    message_text = messaging_event["message"].get("text")
                    if message_text:
                        send_message(sender_id, message_text)
        return jsonify({"status": 200, "body": "EVENT_RECEIVED"}), 200
    except Exception as e:
        return jsonify({"status": 500, "body": str(e)}), 500


def send_message(recipient_id, message_text):
    params = {"access_token": PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = json.dumps(
        {"recipient": {"id": recipient_id}, "message": {"text": message_text}}
    )
    response = requests.post(
        "https://graph.facebook.com/v12.0/me/messages",
        params=params,
        headers=headers,
        data=data,
    )
    if response.status_code != 200:
        print("Failed to send message:", response.status_code, response.text)
    return response.json()


@app.route("/test")
def test():
    return "Test"


@app.route("/result")
def result():
    dict = {"phy": 50, "che": 60, "maths": 70}
    return render_template("result.html", result=dict)
