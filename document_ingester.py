import os
import logging
from typing import List, Dict
import PyPDF2
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def read_pdf(file_path: str) -> str:
    """
    Read text content from a PDF file.
    """
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num, page in enumerate(pdf_reader.pages, 1):
                content = page.extract_text()
                # Add page number metadata
                text += f"[PAGE {page_num}] {content}"
            return text
    except Exception as e:
        logger.error(f"Error reading PDF file {file_path}: {str(e)}")
        raise

def process_document(text: str, metadata: Dict = None) -> List[str]:
    """
    Process a document by splitting it into chunks suitable for embedding.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    return text_splitter.split_text(text)

def ingest_documents(documents: List[Dict[str, str]]):
    """
    Ingest documents into FAISS vector store.
    """
    try:
        # Initialize embeddings
        logger.info("Initializing OpenAI embeddings")
        embeddings = OpenAIEmbeddings()

        all_texts = []
        all_metadatas = []

        # Process each document
        for doc in documents:
            logger.info(f"Processing document for {doc['party']}")

            # Read PDF content
            text = read_pdf(doc['file_path'])
            chunks = process_document(text)

            # Extract page numbers from the text and include in metadata
            texts_with_metadata = []
            for chunk in chunks:
                page_num = None
                # Look for page number in chunk
                for line in chunk.split('\n'):
                    if line.startswith('[PAGE ') and ']' in line:
                        try:
                            page_num = int(line[6:line.index(']')])
                            chunk = chunk.replace(f"[PAGE {page_num}] ", "")
                            break
                        except ValueError:
                            continue

                texts_with_metadata.append({
                    "text": chunk,
                    "metadata": {
                        "party": doc["party"],
                        "category": doc.get("category", "platform"),
                        "source": os.path.basename(doc["file_path"]),
                        "page": str(page_num) if page_num else None
                    }
                })

            all_texts.extend([item["text"] for item in texts_with_metadata])
            all_metadatas.extend([item["metadata"] for item in texts_with_metadata])

        # Create and save the FAISS index
        logger.info("Creating FAISS index")
        vectorstore = FAISS.from_texts(
            texts=all_texts,
            embedding=embeddings,
            metadatas=all_metadatas
        )

        # Save the index
        logger.info("Saving FAISS index")
        vectorstore.save_local("faiss_index")

        logger.info("Document ingestion completed successfully")

    except Exception as e:
        logger.error(f"Error ingesting documents: {str(e)}")
        raise

if __name__ == "__main__":
    # Define the documents to process with official German party names
    documents = [
        {
            "file_path": "attached_assets/AFD.pdf",
            "party": "Alternative für Deutschland",
            "category": "platform"
        },
        {
            "file_path": "attached_assets/BSW.pdf",
            "party": "Bündnis Sahra Wagenknecht",
            "category": "platform"
        },
        {
            "file_path": "attached_assets/CDU_CSU.pdf",
            "party": "CDU/CSU",
            "category": "platform"
        },
        {
            "file_path": "attached_assets/Die Linke.pdf",
            "party": "DIE LINKE",
            "category": "platform"
        },
        {
            "file_path": "attached_assets/FDP.pdf",
            "party": "Freie Demokratische Partei",
            "category": "platform"
        },
        {
            "file_path": "attached_assets/Gruen.pdf",
            "party": "BÜNDNIS 90/DIE GRÜNEN",
            "category": "platform"
        },
        {
            "file_path": "attached_assets/SPD.pdf",
            "party": "Sozialdemokratische Partei Deutschlands",
            "category": "platform"
        }
    ]

    logger.info("Starting document ingestion process")
    ingest_documents(documents)
    logger.info("Document ingestion completed")