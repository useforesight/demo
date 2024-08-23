import os
import PyPDF2
from docx import Document
from flask import Flask, request, jsonify, render_template, Response, stream_with_context, send_from_directory
import openai

app = Flask(__name__, static_folder='templates')

# Initialize the OpenAI client
openai.api_key = "sk-svcacct-xzMk_q38nWSlzD34ENrtRfFsm420mlsg3ivF7CqFz_I6I7n7CTdwkn_JsPSkBgQo5IeT3BlbkFJQYfUVfbck1Tfuq3Kmv6M_Hja6zl_0da4dxzj11iO3OtH2OznipZ6wElIGE4twrsbMXQA"

def load_documents_from_folder(folder_path):
    documents = []
    supported_extensions = ('.txt', '.pdf', '.docx')
    
    for filename in os.listdir(folder_path):
        if not filename.endswith(supported_extensions):
            continue
        
        file_path = os.path.join(folder_path, filename)
        
        if filename.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as file:
                documents.append(file.read())
        
        elif filename.endswith('.pdf'):
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ''
                for page in reader.pages:
                    text += page.extract_text()
                documents.append(text)
        
        elif filename.endswith('.docx'):
            doc = Document(file_path)
            text = '\n'.join([para.text for para in doc.paragraphs])
            documents.append(text)
    
    return "\n\n".join(documents)

documents_folder = 'context_documents'
document_context = load_documents_from_folder(documents_folder)

def chat_with_gpt_stream(prompt, model="gpt-4o"):
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": f"You are a helpful assistant. Here's some context information: {document_context}"},
                {"role": "user", "content": prompt}
            ],
            stream=True
        )
        for chunk in response:
            if chunk.choices[0].delta.get('content'):
                yield chunk.choices[0].delta['content']
    except Exception as e:
        yield f"An error occurred: {str(e)}"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')
    return Response(stream_with_context(chat_with_gpt_stream(user_message)), content_type='text/plain')

@app.route('/generate_prompts', methods=['POST'])
def generate_prompts():
    data = request.json
    question = data.get('question', '')
    answer = data.get('answer', '')
    
    prompt = f"""Based on the following question and answer, generate 4 concise but complete follow-up questions. 
    Each question should be brief (ideally 10-15 words) but must be a fully formed question:

    Q: {question}
    A: {answer}

    Concise, complete follow-up questions:"""
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates concise but complete follow-up questions. Each question must be fully formed and end with a question mark."},
                {"role": "user", "content": prompt}
            ]
        )
        
        new_prompts = response.choices[0].message['content'].strip().split('\n')
        # Clean up the prompts (remove numbers if present)
        new_prompts = [p.lstrip('1234567890. ').strip() for p in new_prompts]
        
        # Ensure each prompt ends with a question mark
        new_prompts = [p if p.endswith('?') else p + '?' for p in new_prompts]
        
        # Limit to 4 prompts
        new_prompts = new_prompts[:4]
        
        return jsonify(new_prompts)
    except Exception as e:
        print(f"Error generating prompts: {str(e)}")
        return jsonify(["Error generating new prompts"]), 500

if __name__ == '__main__':
    app.run(debug=True)