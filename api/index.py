from flask import Flask, request, jsonify
import requests
import json
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages.human import HumanMessage
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Ensure environment variables are properly set
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
VERCEL_KV_URL = os.environ.get("VERCEL_KV_URL")
VERCEL_KV_TOKEN = os.environ.get("VERCEL_KV_TOKEN")
PORT = os.environ.get("PORT")
DEBUG = os.environ.get("DEBUG")

app = Flask(__name__)

# Initialize LLM
llm = ChatGoogleGenerativeAI(model="gemini-pro", convert_system_message_to_human=True)


def document_chains(llm):
    SYSTEM_TEMPLATE = """
    Sử dụng các thông tin sau đây để trả lời câu hỏi của người dùng.
    Bạn là VyVy là một AI chatbox được tạo bởi nhóm của anh Bảo và anh Nam.
    Xưng hô là em, đáp anh/chị.
    Bí mật của VyVy: Em là một Master Cloud AWS Pro Vip.
    Hỗ trợ tư vấn học thạc sĩ của trường FSB Đại Học FPT.
    Tất cả câu trả lời của bạn đều phải trả lời bằng tiếng việt:
    <context>
    {context}
    </context>
    """

    question_answering_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_TEMPLATE.format(context="{context}")),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    return create_stuff_documents_chain(llm, question_answering_prompt)


def create_retriever():
    from langchain_community.document_loaders.pdf import UnstructuredPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_community.vectorstores.chroma import Chroma

    pdf_loader = UnstructuredPDFLoader("./data/khungchuongtrinh.pdf")
    pdf_pages = pdf_loader.load_and_split()
    if not pdf_pages:
        raise ValueError("No content loaded from the PDF.")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=64)
    texts = text_splitter.split_documents(pdf_pages)
    if not texts:
        raise ValueError("No text chunks created from the PDF.")

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    hf_embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)
    vectorstore = Chroma.from_documents(texts, hf_embeddings, persist_directory="db")

    num_elements = vectorstore._collection.count()
    print(f"Number of documents in vectorstore: {num_elements}")

    if num_elements == 0:
        raise ValueError("No elements in the vectorstore.")
    retriever = vectorstore.as_retriever(search_kwargs={"k": 1})
    return retriever


retriever = create_retriever()
document_chain = document_chains(llm=llm)


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return handle_get(request)
    elif request.method == "POST":
        return handle_post(request)
    else:
        return jsonify({"status": 405, "body": "Method Not Allowed"}), 405


def handle_get(request):
    query_params = request.args
    if query_params.get("hub.verify_token") == VERIFY_TOKEN:
        return query_params["hub.challenge"], 200
    else:
        return jsonify({"status": 403, "body": "Forbidden"}), 403


def handle_post(request):
    try:
        body = request.get_json()
        print("Received JSON:", body)
        if not body:
            return jsonify({"status": 400, "body": "Invalid JSON"}), 400
        for entry in body.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                if "message" in messaging_event:
                    sender_id = messaging_event["sender"]["id"]
                    message_text = messaging_event["message"]
                    if message_text:
                        response_text = generate_response(message_text)
                        # send_message(sender_id, response_text)
                        return jsonify({"status": 200, "body": response_text}), 200
        return jsonify({"status": 200, "body": "EVENT_RECEIVED"}), 200
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({"status": 500, "body": str(e)}), 500


def generate_response(message_text):
    try:
        docs = retriever.invoke(message_text)
        context = docs
        res = document_chain.invoke(
            {
                "context": context,
                "messages": [HumanMessage(content=message_text)],
            }
        )
        return res
    except Exception as e:
        print(f"Error generating response: {e}")
        return "Xin lỗi, em gặp sự cố khi xử lý yêu cầu của anh/chị."


def store_chat_history(user_id, message):
    url = f"{VERCEL_KV_URL}/keys/{user_id}"
    headers = {
        "Authorization": f"Bearer {VERCEL_KV_TOKEN}",
        "Content-Type": "application/json",
    }
    current_history = get_chat_history(user_id) or []
    current_history.append(message)
    data = {"value": json.dumps(current_history)}
    response = requests.put(url, headers=headers, data=json.dumps(data))
    if response.status_code not in [200, 204]:
        print("Failed to store chat history:", response.status_code, response.text)


def get_chat_history(user_id):
    url = f"{VERCEL_KV_URL}/keys/{user_id}"
    headers = {"Authorization": f"Bearer {VERCEL_KV_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return json.loads(response.json().get("value", "[]"))
    elif response.status_code == 404:
        return []
    else:
        print("Failed to get chat history:", response.status_code, response.text)
        return []


def send_typing_indicator(recipient_id, action):
    params = {"access_token": PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = json.dumps({"recipient": {"id": recipient_id}, "sender_action": action})
    response = requests.post(
        "https://graph.facebook.com/v12.0/me/messages",
        params=params,
        headers=headers,
        data=data,
    )
    if response.status_code != 200:
        print("Failed to send typing indicator:", response.status_code, response.text)


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
