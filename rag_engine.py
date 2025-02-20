import os
import json
import logging
from typing import List, Dict
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()

# Ensure OpenAI API key and Pinecone API key are set
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def extract_citations_from_pdfs(source_docs):
    """
    Extract exact quotations with page numbers from retrieved PDFs.
    """
    citations_by_party = {party: [] for party in ["afd", "bsw", "cdu_csu", "linke", "fdp", "gruene", "spd"]}

    for doc in source_docs:
        if hasattr(doc, "metadata"):
            party_key = normalize_party_name(doc.metadata.get("party", ""))
            if party_key in citations_by_party:
                # Extract text and clean it
                raw_text = doc.page_content.strip()

                # Remove page markers and clean up text
                text_parts = raw_text.split(']')
                extracted_text = text_parts[-1] if len(text_parts) > 1 else raw_text
                extracted_text = extracted_text.strip().replace("\n", " ")

                # Ensure complete sentences by finding sentence boundaries
                sentences = []
                current_sentence = ""
                words = extracted_text.split()

                for word in words:
                    current_sentence += word + " "
                    if word.strip().endswith(('.', '!', '?')):
                        sentences.append(current_sentence.strip())
                        current_sentence = ""

                if current_sentence.strip():  # Add any remaining text if it seems complete
                    if len(current_sentence.split()) > 5:  # Only add if it's a substantial fragment
                        sentences.append(current_sentence.strip())

                # Join complete sentences up to roughly 500 characters
                final_text = ""
                for sentence in sentences:
                    if len(final_text) + len(sentence) + 1 <= 500:
                        final_text += sentence + " "
                    else:
                        break

                final_text = final_text.strip()

                if final_text:  # Only add if we have valid text
                    # Retrieve correct page number
                    page_number = doc.metadata.get("page", "Unknown")
                    if isinstance(page_number, (list, tuple)):
                        page_number = page_number[0] if page_number else "Unknown"

                    # Store citation with page number and source file
                    citations_by_party[party_key].append({
                        "text": final_text,
                        "source": doc.metadata.get("source", "Unknown"),
                        "page": page_number
                    })

    return citations_by_party

def normalize_party_name(party: str) -> str:
    """
    Normalize party names to match the expected keys in the JSON response.
    """
    mapping = {
        "alternative_für_deutschland": "afd",
        "bündnis_sahra_wagenknecht": "bsw",
        "cdu/csu": "cdu_csu",
        "die_linke": "linke",
        "freie_demokratische_partei": "fdp",
        "bündnis_90/die_grünen": "gruene",
        "sozialdemokratische_partei_deutschlands": "spd"
    }
    normalized = party.lower().replace(" ", "_").replace("/", "_")
    return mapping.get(normalized, normalized)

# Initialize embeddings and vector store
try:
    logger.info("Initializing OpenAI embeddings")
    embeddings = OpenAIEmbeddings()

    # Load the FAISS index
    logger.info("Loading FAISS index")
    vectorstore = FAISS.load_local(
        "faiss_index",
        embeddings,
        allow_dangerous_deserialization=True
    )
except Exception as e:
    logger.error(f"Failed to initialize vector store: {str(e)}", exc_info=True)
    raise

# Initialize the language model
logger.info("Initializing ChatOpenAI")
llm = ChatOpenAI(temperature=0, model="gpt-4")

# Define prompt template
template = """
First, detect the language of the user's query.
- If the query is in English, respond in English.
- If the query is in German, respond in German.
- Do not switch languages.
- Use the same language consistently for all parts of the JSON response.

IMPORTANT:
- The context is in German.
- If the query is in English, TRANSLATE the context to English before analysis.
- If the query is in German, use the context as is without translation.

You are an expert in political analysis. Analyze the following political statement and provide the stance of each German political party.

Context: {context}

Statement: {question}

Reply ONLY with a JSON object in this format:
{{
  "afd": {{"agreement": 75, "explanation": "Explanation", "citations": []}},
  "bsw": {{"agreement": 50, "explanation": "Explanation", "citations": []}},
  "cdu_csu": {{"agreement": 30, "explanation": "Explanation", "citations": []}},
  "linke": {{"agreement": 20, "explanation": "Explanation", "citations": []}},
  "fdp": {{"agreement": 60, "explanation": "Explanation", "citations": []}},
  "gruene": {{"agreement": 40, "explanation": "Explanation", "citations": []}},
  "spd": {{"agreement": 80, "explanation": "Explanation", "citations": []}}
}}

STRICT REQUIREMENTS:
- The response MUST be in valid JSON format.
- No text or explanations outside the JSON object.
- If the query is in English, explanations must be in English.
- If the query is in German, explanations must be in German.
- DO NOT provide any introductory or closing text.
- If unable to provide a valid JSON response, state "Invalid JSON Format".
"""

PROMPT = PromptTemplate(template=template, input_variables=["context", "question"])

# Create the QA chain with increased retrieval
logger.info("Creating QA chain")
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(search_kwargs={"k": 15}),  # Increased retrieval
    chain_type_kwargs={
        "prompt": PROMPT,
        "verbose": True
    },
    return_source_documents=True  # Ensure source documents are returned
)

def analyze_statement(statement: str) -> dict:
    """
    Analyze a political statement using the RAG system, ensuring citations include exact quotations and page numbers.
    """
    try:
        logger.info(f"Starting analysis of statement: {statement}")

        # Get response from the chain
        result = qa_chain({"query": statement})
        logger.debug(f"Raw chain result: {result}")

        # Extract relevant citations from PDF source documents
        source_docs = result.get("source_documents", [])
        citations_by_party = extract_citations_from_pdfs(source_docs)

        # Extract the answer
        answer = result.get("result", "").strip()
        if not answer:
            logger.warning("Empty response received from model.")
            return {}

        try:
            parsed_result = json.loads(answer)
            logger.debug(f"Parsed result: {parsed_result}")

            # Validate structure and attach citations
            required_parties = ["afd", "bsw", "cdu_csu", "linke", "fdp", "gruene", "spd"]
            result_dict = {}

            for party in required_parties:
                party_data = parsed_result.get(party, {})
                if not isinstance(party_data, dict):
                    party_data = {}

                # Attach citations from PDF documents
                party_data["citations"] = citations_by_party.get(party, [])

                # Clean and validate party data
                result_dict[party] = {
                    "agreement": min(100, max(0, int(party_data.get("agreement", 0)))),
                    "explanation": str(party_data.get("explanation", "Keine Erklärung verfügbar.")),
                    "citations": party_data["citations"]
                }

            logger.info("Successfully generated analysis result with citations from PDFs")
            return result_dict

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}", exc_info=True)
            logger.error(f"Raw response that failed to parse: {answer}")
            raise ValueError("Ungültiges Antwortformat vom Analysedienst")

    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}", exc_info=True)
        raise ValueError(f"Analyse fehlgeschlagen: {str(e)}")