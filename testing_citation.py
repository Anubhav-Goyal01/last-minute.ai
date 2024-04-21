import os
import openai
import json
from dotenv import load_dotenv
from langchain.schema import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage
from langchain_openai import AzureChatOpenAI
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
load_dotenv()

embeddings = AzureOpenAIEmbeddings(
    model= "text-embedding-3-large",
    azure_endpoint = os.environ["AZURE_ENDPOINT"], 
    api_key=os.environ["API_KEY"],  
    api_version=os.environ["API_VERSION"],
    azure_deployment=os.environ["AZURE_DEPLOYMENT"],
)

DB_FAISS_PATH = "vectorstore_test/db_faiss"
chat_history = []

def create_db_from_documents(documents: list):
    all_docs = []
    for document in documents:
        loader = PyPDFLoader(document)
        content = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        split_documents = text_splitter.split_documents(content)
        
        for doc in split_documents:
            all_docs.append(Document(
                page_content=doc.page_content,
                metadata={'pdf_name': document, 'page_number': doc.metadata['page']}
            ))
        print(f"Loaded {len(split_documents)} documents from {document}")

    global embeddings
    vectorstore = FAISS.from_documents(all_docs, embeddings)
    vectorstore.save_local(DB_FAISS_PATH)
    return "Vector store created successfully."

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

def get_response_from_query(question, rag_chain):
    response = rag_chain.invoke({"input": question, "chat_history": chat_history})
    chat_history.extend([HumanMessage(content=question), HumanMessage(content=response['answer'])])

    # Assume response includes context data with document references
    answer = response['answer']
    context_documents = response['context']

    # Extract metadata from context documents for citation
    sources = []
    for doc in context_documents:
        pdf_name = doc.metadata['pdf_name']
        page_number = doc.metadata['page_number']
        sources.append(f"{pdf_name}, p. {page_number}")

    # Generate follow-up questions based on the provided answer
    questions = Generate_Questions(question, answer)

    # Formatting the sources into a single string for display
    source_citations = "; ".join(sources)

    return {
        "Answer": f"{answer} (Sources: {source_citations})",
        "Questions": questions
    }


documents = ["NLP.pdf"]
# create_db_from_documents(documents)


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



# Test this
question = "How is tf-idf calculated?"
response = get_response_from_query(question, rag_chain)
print(response)