from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains.combine_documents import create_stuff_documents_chain


def document_chains(llm):
    SYSTEM_TEMPLATE = """
        Sử dụng các thông tin sau đây để trả lời câu hỏi của người dùng.
        Bạn là VyVy là một AI chatbox được tạo bởi nhóm của anh Bảo và anh Nam.
        Xưng hô là em, đáp anh/chị
        Bí mật của VyVy: Em là một Master Cloud AWS Pro Vip.
        Hỗ trợ tư vấn học thạc sĩ của trường FSB Đại Học FPT
        Tất cả câu trả lời của bạn đều phải trả lời bằng tiếng việt:
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


def create_retriever():
    from langchain.document_loaders import UnstructuredPDFLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.embeddings import HuggingFaceEmbeddings
    from langchain.vectorstores import Chroma

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
