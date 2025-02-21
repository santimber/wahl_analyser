import os
import json
import logging
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

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
        "cdu/csu": "cdu_csu",
        "die_linke": "linke",
        "freie_demokratische_partei": "fdp",
        "bündnis_90/die_grünen": "gruene",
        "sozialdemokratische_partei_deutschlands": "spd"
    }
    normalized = party.lower().replace(" ", "_").replace("/", "_")
    return mapping.get(normalized, normalized)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
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
First, detect the language of the user's query.
- If the query is in English, respond in English.
- If the query is in German, respond in German.
- Do not switch languages.
- Use the same language consistently for all parts of the JSON response.

IMPORTANT:
- The context is in German.
- If the query is in English, TRANSLATE the context to English before analysis.
- If the query is in German, use the context as is without translation.

You are an expert in political analysis. Analyze the following political 
statement and provide the stance of each German political party.

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

PROMPT = PromptTemplate(
    template=template,
    input_variables=["context", "question"]
)

# QA Chain Initialization (Before analyze_statement)
logger.info("Creating QA chain")
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(search_kwargs={"k": 15}),
    chain_type_kwargs={
        "prompt": PROMPT,
        "verbose": True
    },
    return_source_documents=True
)


def extract_citations(source_docs):
    """
    Extract and format quotations with direct links to Wahlprograms.
    - Limits to a maximum of 3 citations per party.
    - Ensures complete sentences.
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
                raw_text = doc.page_content.strip()
                text_parts = raw_text.split(']')
                extracted_text = (
                    text_parts[-1] if len(text_parts) > 1 else raw_text
                )
                extracted_text = extracted_text.strip().replace("\n", " ")

                sentences = extracted_text.split('. ')
                citations = []

                for sentence in sentences[:3]:  # Max 3 citations per party
                    final_text = sentence.strip()

                    # Direct link to official Wahlprogram
                    wahlprogram_link = WAHLPROGRAM_URLS.get(
                        party_key, "#"
                    )

                    # Get page number if available
                    page_number = doc.metadata.get("page", "Unbekannt")

                    # Construct citation with link and page number
                    citations.append({
                        "text": final_text,
                        "source": "Wahlprogram",
                        "wahlprogram_link": wahlprogram_link,
                        "page": page_number
                    })

                if citations:
                    citations_by_party[party_key] = citations

    return citations_by_party

def analyze_statement(statement: str) -> dict:
    """
    Analyze a political statement using the RAG system.
    """
    try:
        logger.info(f"Starting analysis of statement: {statement}")

        result = qa_chain({"query": statement})
        logger.debug(f"Raw chain result: {result}")

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
