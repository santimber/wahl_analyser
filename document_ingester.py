import os
import logging
from typing import List, Dict, Tuple
import PyPDF2
import re
import nltk
nltk.download('punkt', quiet=True)
import fitz
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

# Load environment variables
load_dotenv()

# Ensure OpenAI API key and Pinecone API key are set
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def clean_page_text(text: str) -> str:
    """
    Remove line numbers, page artifacts, and extra spacing from PDF text.
    This is a simple approach; it may need further refinement for multi-column or footnotes.
    """
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        # Remove all digit sequences to handle line numbering or line references
        line = re.sub(r'\d+', '', line)
        # Strip leftover whitespace, unify spacing
        line = line.strip()
        line = re.sub(r'\s+', ' ', line)
        if line:
            cleaned_lines.append(line)
    # Rejoin lines into a single string
    return ' '.join(cleaned_lines)

def read_pdf(file_path: str) -> List[Tuple[int, str]]:
    """
    Read each page from a PDF file using PyMuPDF (fitz), extracting blocks in reading order.
    Returns a list of (page_number, cleaned_text) tuples.
    """
    pages = []
    try:
        with fitz.open(file_path) as doc:
            for page_index in range(len(doc)):
                page = doc[page_index]
                # Extract blocks, each block is (x0, y0, x1, y1, text, block_type, block_no)
                blocks = page.get_text("blocks") or []
                # Sort blocks top-to-bottom, then left-to-right
                blocks.sort(key=lambda b: (b[1], b[0]))

                # Join block texts
                joined_text = []
                for b in blocks:
                    # b[4] is the text portion of the block tuple
                    joined_text.append(b[4])

                raw_content = "".join(joined_text)
                cleaned_content = clean_page_text(raw_content)
                pages.append((page_index + 1, cleaned_content))
    except Exception as e:
        logger.error(f"Error reading PDF file {file_path}: {str(e)}")
        raise

    return pages

def process_document(text: str) -> List[str]:
    """
    Process a document by first splitting it into sentences (using NLTK) and
    then chunking them for embedding.
    """
    from nltk.tokenize import sent_tokenize

    # 1. Sentence tokenize (assuming German documents)
    sentences = sent_tokenize(text, language='german')

    # 2. Optionally merge very short adjacent sentences
    processed_sentences = []
    buffer = ""
    for s in sentences:
        s = s.strip()
        if not buffer:
            buffer = s
        elif len(buffer) + len(s) < 120:
            buffer += " " + s
        else:
            processed_sentences.append(buffer.strip())
            buffer = s
    if buffer:
        processed_sentences.append(buffer.strip())

    # 3. Re-join them with newlines to preserve natural breaks
    final_text = "\n".join(processed_sentences)

    # 4. Use RecursiveCharacterTextSplitter for final chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    return text_splitter.split_text(final_text)


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

            # Read pages from PDF
            pdf_pages = read_pdf(doc['file_path'])

            # For each page, create chunks and store with metadata (including page number)
            for page_num, page_content in pdf_pages:
                # Split the page content into chunks
                chunks = process_document(page_content)

                for chunk in chunks:
                    all_texts.append(chunk)
                    all_metadatas.append({
                        "party": doc["party"],
                        "category": doc.get("category", "platform"),
                        "source": os.path.basename(doc["file_path"]),
                        "page": str(page_num)
                    })

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
            "file_path": "./static/documents/AFD.pdf",
            "party": "Alternative für Deutschland",
            "category": "platform"
        },
        {
            "file_path": "./static/documents/BSW.pdf",
            "party": "Bündnis Sahra Wagenknecht",
            "category": "platform"
        },
        {
            "file_path": "./static/documents/CDU_CSU.pdf",
            "party": "Christlich Demokratische Union",
            "category": "platform"
        },
        {
            "file_path": "./static/documents/Die Linke.pdf",
            "party": "DIE LINKE",
            "category": "platform"
        },
        {
            "file_path": "./static/documents/FDP.pdf",
            "party": "Freie Demokratische Partei",
            "category": "platform"
        },
        {
            "file_path": "./static/documents/Gruen.pdf",
            "party": "BÜNDNIS 90_DIE GRÜNEN",
            "category": "platform"
        },
        {
            "file_path": "./static/documents/SPD.pdf",
            "party": "Sozialdemokratische Partei Deutschlands",
            "category": "platform"
        }
    ]

    logger.info("Starting document ingestion process")
    ingest_documents(documents)
    logger.info("Document ingestion completed")