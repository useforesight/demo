import os
from flask import Flask, request, jsonify, render_template, Response, stream_with_context
import openai

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the weather today?"}
    ]
)

print(response.choices[0].message['content'])

def load_documents_from_folder(folder_path):
    documents = []
    for filename in os.listdir(folder_path):
        if filename.endswith('.txt'):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                documents.append(file.read())
    return "\n\n".join(documents)

documents_folder = 'context_documents'
document_context = load_documents_from_folder(documents_folder)

def chat_with_gpt_stream(prompt, model="gpt-3.5-turbo"):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": f"You are a helpful assistant. Here's some context information: {document_context}"},
                {"role": "user", "content": prompt}
            ],
            stream=True
        )
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"An error occurred: {str(e)}"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']
    return Response(stream_with_context(chat_with_gpt_stream(user_message)), content_type='text/plain')

if __name__ == '__main__':
    app.run(debug=True)