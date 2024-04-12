import openai
from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import AzureChatOpenAI
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from utils import get_response_from_query, create_db_from_documents, Generate_Questions, GenerateQuestionsInitial
import os

app = Flask(__name__)
CORS(app)


DB_FAISS_PATH = "vectorstore/db_faiss"
embeddings = AzureOpenAIEmbeddings(
    model= "text-embedding-3-large",
    azure_endpoint = os.environ["AZURE_ENDPOINT"], 
    api_key=os.environ["API_KEY"],  
    api_version=os.environ["API_VERSION"],
    azure_deployment=os.environ["AZURE_DEPLOYMENT"],
)

vectorstore = FAISS.load_local(DB_FAISS_PATH, embeddings, allow_dangerous_deserialization=True)
retriever = vectorstore.as_retriever()

llm = AzureChatOpenAI(
    azure_endpoint = os.environ["AZURE_ENDPOINT"], 
    api_key=os.environ["API_KEY"],  
    api_version=os.environ["API_VERSION"],
    azure_deployment='gpt35t',
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


@app.route('/get_answer', methods=['POST'])
def get_answer():
    data = request.json
    question = data.get('question')
    if not question:
        return jsonify({"error": "No question provided"}), 400

    try:
        answer_and_questions = get_response_from_query(question, rag_chain)
        return jsonify({
            "Answer": answer_and_questions['Answer'],
            "Questions": answer_and_questions['Questions']
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/upload', methods=['POST'])
def upload():
    data = request.json
    url = data.get('url')
    doc_type = data.get('type') 

    url = [url[0], "NLP.pdf"]
    doc_type = ["youtube", "pdf"]
    
    if not url and not doc_type:
        return jsonify({"error": "Missing URL or type"}), 400

    try:
        response_message = create_db_from_documents(url, doc_type)
        questions = GenerateQuestionsInitial(rag_chain)
        return jsonify({"questions": [ques for ques in questions]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)