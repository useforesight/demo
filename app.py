import os
import PyPDF2
from docx import Document
from flask import Flask, request, jsonify, render_template, Response, stream_with_context, send_from_directory
from openai import OpenAI

app = Flask(__name__, static_folder='templates')

# Load the OpenAI API key from an environment variable
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")

# Now you can use openai_api_key wherever needed in your app

def load_documents_from_folder(folder_path):
    documents = []
    for filename in os.listdir(folder_path):
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

def get_folder_path_for_page(page_name):
    if page_name == "tris4nonylphenyl-phosphite-identified-as-potential-endocrine-disruptor":
        return os.path.join("context_documents", "chat-tris4nonylphenyl")
    elif page_name == "assistant":
        return os.path.join("context_documents", "chat-assistant")
    elif page_name == "public-consultation-launched-for-the-stockholm-convention":
        return os.path.join("context_documents", "chat-stockholm")
    elif page_name == "reach":  # New condition for reach.html
        return os.path.join("context_documents", "reach")
    else:
        return os.path.join("context_documents", "default")

def chat_with_gpt_stream(prompt, context, model="gpt-4o"):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": f"You are a helpful assistant. Here's some context information: {context}"},
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

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']
    page_name = request.json.get('page_name', 'default')
    
    # Remove the .html extension if present
    page_name = page_name.replace('.html', '')
    
    folder_path = get_folder_path_for_page(page_name)
    document_context = load_documents_from_folder(folder_path)
    return Response(stream_with_context(chat_with_gpt_stream(user_message, document_context)), content_type='text/plain')


@app.route('/alerts')
def alerts():
    # Fetch your alerts data here. This is a placeholder.
    alerts_data = [
        {
            "title": "New Stockholm Convention Consultation",
            "description": "Public consultation launched for the Stockholm Convention",
            "slug": "public-consultation-launched-for-the-stockholm-convention"
        },
        # Add more alerts as needed
    ]
    return render_template('alerts.html', alerts=alerts_data)


@app.route('/<path:page_name>')
def render_page(page_name):
    # Check if the HTML file exists
    if os.path.exists(os.path.join(app.static_folder, f"{page_name}.html")):
        return render_template(f"{page_name}.html")
    else:
        return "Page not found", 404


@app.route('/generate_prompts', methods=['POST'])
def generate_prompts():
    data = request.json
    question = data['question']
    answer = data['answer']
    
    prompt = f"""Based on the following question and answer, generate 4 concise but complete follow-up questions. 
    Each question should be brief (ideally 10-15 words) but must be a fully formed question:

    Q: {question}
    A: {answer}

    Concise, complete follow-up questions:"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates concise but complete follow-up questions. Each question must be fully formed and end with a question mark."},
                {"role": "user", "content": prompt}
            ]
        )
        
        new_prompts = response.choices[0].message.content.strip().split('\n')
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