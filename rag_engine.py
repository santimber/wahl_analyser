import os
import json
import logging
import nltk
from nltk.data import find

nltk_data_dir = '/mnt/data/nltk_data'
nltk.data.path.append(nltk_data_dir)

try:
    find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', download_dir=nltk_data_dir) 
    
from nltk.tokenize import sent_tokenize
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

nltk_data_dir = '/mnt/data/nltk_data'
nltk.data.path.append(nltk_data_dir)

# Load environment variables
load_dotenv()

# Ensure OpenAI API key is set
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def normalize_party_name(party: str) -> str:
    """
    Normalize party names to match the expected keys in the JSON response.
    """
    mapping = {
        "alternative_für_deutschland": "afd",
        "bündnis_sahra_wagenknecht": "bsw",
        "christlich_demokratische_union": "cdu_csu",
        "die_linke": "linke",
        "freie_demokratische_partei": "fdp",
        "bündnis_90_die_grünen": "gruene",
        "sozialdemokratische_partei_deutschlands": "spd"
    }
    normalized = party.lower().replace(" ", "_").replace("/", "_")
    return mapping.get(normalized, normalized)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Direct Links to Official Wahlprograms
WAHLPROGRAM_URLS = {
    "cdu_csu": "https://www.cdu.de/app/uploads/2025/01/km_btw_2025_wahlprogramm_langfassung_ansicht.pdf",
    "spd": "https://www.spd.de/fileadmin/Dokumente/Beschluesse/Programm/SPD_Programm_bf.pdf",
    "fdp": "https://www.fdp.de/sites/default/files/2024-12/fdp-wahlprogramm_2025.pdf",
    "gruene": "https://cms.gruene.de/uploads/assets/Regierungsprogramm_DIGITAL_DINA5.pdf",
    "linke": "https://www.die-linke.de/fileadmin/user_upload/Wahlprogramm_Langfassung_Linke-BTW25_01.pdf",
    "afd": "https://www.afd.de/wp-content/uploads/2025/02/AfD_Bundestagswahlprogramm2025_web.pdf",
    "bsw": "https://bsw-vg.de/wp-content/themes/bsw/assets/downloads/BSW%20Wahlprogramm%202025.pdf"
}

# Embeddings and Vector Store Initialization
try:
    logger.info("Initializing OpenAI embeddings")
    embeddings = OpenAIEmbeddings()

    logger.info("Loading FAISS index")
    vectorstore = FAISS.load_local(
        "faiss_index",
        embeddings,
        allow_dangerous_deserialization=True
    )
except Exception as e:
    logger.error(
        f"Failed to initialize vector store: {str(e)}", exc_info=True
    )
    raise

# Language Model Initialization
logger.info("Initializing ChatOpenAI")
llm = ChatOpenAI(temperature=0, model="gpt-4")

# Prompt Template
template = """
First, determine the language of the user's query:
- If the query is in German, respond in German. Antworte auf Deutsch, wenn jemand auf Deutsch schreibt.
- If the query is in English, respond in English.
- Do not switch languages. Use the same language for all parts of the JSON response.

IMPORTANT:
- The provided context is in German.
- If the query is in German, use the German context as is (no translation).
- You must include at least one citation per party. The citation(s) must be a chunk of text from the provided context that you used to support your analysis.

You are an expert in political analysis. While analyzing each party, provide a distinct stance and explanation. If multiple parties have similar stances, clarify how or why they might differ. Do not repeat the same explanation for different parties unless the context explicitly shows they have identical views.

ALWAYS include at least one "citations" array that contains at least one citation. Each citation must be a chunk of text taken from the context that was used in your analysis.

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
- The response MUST be valid JSON.
- No text or explanations outside the JSON object.
- If the users query is in German, all text in the JSON must be in German. (explanations, references, etc.).
- If the users query is in English, all text in the JSON must be in English (explanations, references, etc.).
- Do NOT provide any introductory or closing text.
- ALWAYS include at least one "citations" array that contains at least one citation. Each citation must be a chunk of text taken from the context that was used in your analysis.
- If unable to provide a valid JSON response, return "Invalid JSON Format".
"""

PROMPT = PromptTemplate(
    template=template,
    input_variables=["context", "question"]
)

# QA Chain Initialization (Before analyze_statement)
logger.info("Creating QA chain")
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(search_kwargs={"k": 35}),
    chain_type_kwargs={
        "prompt": PROMPT,
        "verbose": False
    },
    return_source_documents=True
)


def extract_citations(source_docs):
    """
    Extract and format quotations with direct links to Wahlprograms.
    - Limits to a maximum of 3 citations per party.
    - Returns the entire and most relevant chunks to provide more context.
    """
    citations_by_party = {
        party: [] for party in [
            "afd", "bsw", "cdu_csu", "linke", "fdp", "gruene", "spd"
        ]
    }

    for doc in source_docs:
        if hasattr(doc, "metadata"):
            party_key = normalize_party_name(
                doc.metadata.get("party", "")
            )
            if party_key in citations_by_party:

                # The entire chunk as extracted from the doc
                raw_text = doc.page_content.strip()
                # Attempt to remove bracketed prefix if present
                text_parts = raw_text.split(']')
                extracted_text = text_parts[-1] if len(text_parts) > 1 else raw_text
                extracted_text = extracted_text.strip().replace("\n", " ")

                # Only add up to 3 citations per party
                if len(citations_by_party[party_key]) < 3:
                    # Direct link to official Wahlprogram
                    wahlprogram_link = WAHLPROGRAM_URLS.get(
                        party_key, "#"
                    )
                    page_number = doc.metadata.get("page", "Unbekannt")

                    citations_by_party[party_key].append({
                        "text": extracted_text,
                        "source": "Wahlprogram",
                        "wahlprogram_link": wahlprogram_link,
                        "page": page_number
                    })

    return citations_by_party

def analyze_statement(statement: str) -> dict:
    """
    Analyze a political statement using the RAG system.
    """
    try:
        logger.info(f"Starting analysis of statement: {statement}")

        result = qa_chain({"query": statement})
        #logger.debug(f"Raw chain result: {result}")

        source_docs = result.get("source_documents", [])
        citations_by_party = extract_citations(source_docs)

        answer = result.get("result", "").strip()
        if not answer:
            logger.warning("Empty response received from model.")
            return {}

        parsed_result = json.loads(answer)
        required_parties = ["afd", "bsw", "cdu_csu", "linke", "fdp", "gruene", "spd"]
        result_dict = {}

        for party in required_parties:
            party_data = parsed_result.get(party, {})
            if not isinstance(party_data, dict):
                party_data = {}

            party_data["citations"] = citations_by_party.get(party, [])
            result_dict[party] = {
                "agreement": min(100, max(0, int(party_data.get("agreement", 0)))),
                "explanation": str(party_data.get("explanation", "Keine Erklärung verfügbar.")),
                "citations": party_data["citations"]
            }

        return result_dict

    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}", exc_info=True)
        raise ValueError(f"Analyse fehlgeschlagen: {str(e)}")
