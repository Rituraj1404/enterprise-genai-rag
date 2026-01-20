from pathlib import Path
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DATA_PATH = Path(__file__).resolve().parents[2] / "data"

def load_documents():
    documents = []

    role_map = {
        "intern_docs": "intern",
        "manager_docs": "manager",
        "admin_docs": "admin",
    }

    for folder, role in role_map.items():
        folder_path = BASE_DATA_PATH / folder

        if not folder_path.exists():
            continue

        for file in folder_path.iterdir():

            # TXT files
            if file.suffix == ".txt":
                loader = TextLoader(str(file))
                docs = loader.load()

            # PDF files
            elif file.suffix == ".pdf":
                loader = PyPDFLoader(str(file))
                docs = loader.load()

            else:
                continue

            for doc in docs:
                doc.metadata["role"] = role
                doc.metadata["source"] = file.name
                documents.append(doc)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=100
    )

    return splitter.split_documents(documents)
