import openai
from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import AzureChatOpenAI
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from utils import get_response_from_query, create_db_from_documents
from langchain_pinecone import PineconeVectorStore
import os
from werkzeug.utils import secure_filename
import json
app = Flask(__name__)
CORS(app)

from dotenv import load_dotenv
load_dotenv()

embeddings = AzureOpenAIEmbeddings(
    model= "text-embedding-3-large",
    azure_endpoint = os.environ["AZURE_ENDPOINT"], 
    api_key=os.environ["API_KEY"],  
    api_version=os.environ["API_VERSION"],
    azure_deployment=os.environ["AZURE_DEPLOYMENT"],
)

def chain_setup():
    vectorstore = PineconeVectorStore(index_name="html-embeddings-product-urls", embedding=embeddings, namespace = 'test')
    retriever = vectorstore.as_retriever()
    llm = AzureChatOpenAI(
        azure_endpoint= os.environ["AZURE_ENDPOINT_GPT_4"], 
        api_key=os.environ["API_KEY_GPT_4"],  
        api_version=os.environ["API_VERSION"],
        azure_deployment='shoppin-gpt4o',
    )


    contextualize_q_system_prompt = """Given a chat history and the latest user question \
    which might reference context in the chat history, formulate a standalone question \
    which can be understood without the chat history. Do NOT answer the question, \
    just reformulate it if needed and otherwise return it as is."""
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )

    qa_system_prompt = """
        You are a helpful assistant that that can answer questions about youtube videos/ pdf / ppts based on the given transcript as well as uses its own knowledge to provide a more detailed explanation in case the transcript only touches the surface. Please be aware whether the question is about a youtube video, pdf or ppt and answer accordingly.
        Answer the question based on the given transcript.
        Transcript: {context}
                
        If you feel like you don't have enough information to answer the question, say "I don't know".
        """

    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", qa_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    return rag_chain



UPLOAD_FOLDER = 'PDFs'
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/get_answer', methods=['POST'])
def get_answer():
    data = request.json
    question = data.get('question')
    if not question:
        return jsonify({"error": "No question provided"}), 400

    try:
        rag_chain = chain_setup()
        answer_and_questions = get_response_from_query(question, rag_chain)
        print(f"Answer: {answer_and_questions['Answer']}")
        return jsonify({
            "Answer": answer_and_questions['Answer'],
            "Questions": answer_and_questions['Questions']
        })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/upload', methods=['POST'])
def upload():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    # Get files from form-data.
    file_objects = request.files.getlist("files")
    uploaded_files = []

    # Save PDF files.
    for file in file_objects:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            uploaded_files.append(file_path)

    # Get JSON data from the form-data.
    json_data = request.form.get('json')
    if json_data:
        json_data = json.loads(json_data)
        urls = json_data.get('documents')
    else:
        return jsonify({"error": "Missing documents data"}), 400

    # Combine file paths and URLs.
    all_docs = uploaded_files + urls
    all_doc_types = ['pdf'] * len(uploaded_files) + ['yt'] * len(urls)

    print(all_docs)
    print(all_doc_types)

    try:
        response_message = create_db_from_documents(all_docs, all_doc_types)
        return jsonify({"response": "Embeddings Generated Successfully"}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)