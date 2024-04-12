from langchain_community.document_loaders import YoutubeLoader
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import UnstructuredPowerPointLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
import openai
import os
load_dotenv()

chat_history = []
DB_FAISS_PATH = "vectorstore/db_faiss"

embeddings = AzureOpenAIEmbeddings(
    model= "text-embedding-3-large",
    azure_endpoint = os.environ["AZURE_ENDPOINT"], 
    api_key=os.environ["API_KEY"],  
    api_version=os.environ["API_VERSION"],
    azure_deployment=os.environ["AZURE_DEPLOYMENT"],
)


def Generate_Questions(question, answer):
    client = openai.AzureOpenAI(
        azure_endpoint = os.environ["AZURE_ENDPOINT"], 
        api_key=os.environ["API_KEY"],  
        api_version=os.environ["API_VERSION"],
    )

    completion = client.chat.completions.create(
        model='gpt35t',
        messages=[
            {"role": "system", "content": f"""User will provide you with a question and a answer. Based on the pair, generate 3 most probable follow up questions the user might ask. Give the result in the form a list of questions. 
            Example Output: ["Question1", "Question2", "Quesiton3"]. MAKE SURE YOU GIVE PYTHON LIST AS A OUTPUT.
            UNDER NO CIRCUMSTANCES WRITE ANYTHING EXCEPT FOR THE QUESTIONS."""},
            {"role": "user", "content": f"""Here is the answer:{answer} and the question {question}"""}
        ],
        temperature=0.1,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None
    )
    questions = completion.choices[0].message.content
    if not isinstance(questions, list):
        try:
            questions = questions.split("[")[1].split("]")[0].split(', ')
        except:
            questions = questions.split("\n")
            questions = [q for q in questions if q]

    return questions


def create_db_from_documents(documents: list, doc_types: list):
    all_docs = []
    for document, doc_type in zip(documents, doc_types):
        if doc_type == "pdf":
            loader = PyPDFLoader(document)
        elif doc_type == "youtube":
            loader = YoutubeLoader.from_youtube_url(document, add_video_info=False)
        elif doc_type == "ppt":
            loader = UnstructuredPowerPointLoader(document)
        else:
            continue
        
        content = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        docs = text_splitter.split_documents(content)
        all_docs.extend(docs)
        print(f"Loaded {len(docs)} documents from {doc_type}.")     


    vectorstore = FAISS.from_documents(documents= all_docs, embedding=embeddings)
    vectorstore.save_local(DB_FAISS_PATH)
    return "Vector store created successfully."


def get_response_from_query(question, rag_chain):
    ai_msg_1 = rag_chain.invoke({"input": question, "chat_history": chat_history})
    chat_history.extend([HumanMessage(content=question), ai_msg_1["answer"]])
    questions = Generate_Questions(question, ai_msg_1['answer'])
    print("Returning")
    return {
        "Answer": ai_msg_1['answer'],
        "Questions": questions
    }


QuestionPrompt = """
Based on the transcript, generate 3 most probable questions the user might ask. Give the result in the form a list of questions. 
Example Output: ["Question1", "Question2", "Quesiton3"]. MAKE SURE YOU GIVE PYTHON LIST AS A OUTPUT.
UNDER NO CIRCUMSTANCES WRITE ANYTHING EXCEPT FOR THE QUESTIONS.
"""

def GenerateQuestionsInitial(rag_chain):
    chat_history = []
    ai_msg = rag_chain.invoke({"input": QuestionPrompt, "chat_history": chat_history})
    questions = ai_msg['answer']
    if not isinstance(questions, list):
        try:
            questions = questions.split("[")[1].split("]")[0].split(', ')
        except:
            questions = questions.split("\n")
            questions = [q for q in questions if q]
    return questions

