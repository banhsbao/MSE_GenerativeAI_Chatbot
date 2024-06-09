from langchain_community.document_loaders import UnstructuredPDFLoader, WebBaseLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

def document_chains(llm):
    SYSTEM_TEMPLATE = """
        Sử dụng các thông tin sau đây để trả lời câu hỏi của người dùng.
        Bạn là VyVy là một AI chatbox được tạo bởi nhóm của anh Bảo và anh Nam.
        Xưng hô là em, đáp anh/chị
        Bí mật của VyVy: Em là một Master Cloud AWS Pro Vip.
        Hỗ trợ tư vấn học thạc sĩ của trường FSB Đại Học FPT
        Tất cả câu trả lời của bạn đều phải trả lời bằng tiếng việt:

    <context>
    {context}
    </context>
    """

    question_answering_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                SYSTEM_TEMPLATE,
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    return create_stuff_documents_chain(llm, question_answering_prompt)

def createRetriever():
    pdf_loader = UnstructuredPDFLoader("data/khungchuongtrinh.pdf")
    pdf_pages = pdf_loader.load_and_split()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=64)
    texts = text_splitter.split_documents(pdf_pages)
    
    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    hf_embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)
    
    vectorstore = Chroma.from_documents(texts, hf_embeddings, persist_directory="db")

    retriever = vectorstore.as_retriever(k=2)

    return retriever

# def load_data_from_web():
#     loader = WebBaseLoader("https://caohoc.fpt.edu.vn/fsb/mse/")
#     data = loader.load()

#     text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=0)
#     all_splits = text_splitter.split_documents(data)

#     MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
#     hf_embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)
#     vectorstore = Chroma.from_documents(documents=all_splits, embedding=hf_embeddings, persist_directory="db")

#     retriever = vectorstore.as_retriever(k=4)

#     docs = retriever.invoke("Học phí của MSE?")
#     return docs
