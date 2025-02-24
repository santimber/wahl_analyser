
## Set up environment variables:
Wahl Explorer is designed to help users discover how Germany’s major political parties align with their personal views on specific political positions. By analyzing party manifestos, Wahl Explorer enables users to enter a political statement or query (e.g., "Should electric vehicles be subsidized?") and receive a detailed comparison of how each party's official stance relates to the user’s input. The application:
- **Ingests and processes** raw political documents (e.g., manifestos, policy proposals)
- **Indexes document content** using FAISS for fast, approximate vector similarity searches
- **Presents an interactive interface** where users can query and compare policy texts

## Install dependencies:
```bash
pip install -r dependencies.txt
```

## Set up environment variables:
Create a `.env` file in the project root with the following variables:
```
OPENAI_API_KEY=your_openai_api_key

```

## Installation
```bash
git clone https://github.com/santimber/wahl_analyser.git
cd wahl_analyser
```

## Start the application locally:
```bash
python main.py
python document_ingester.py
python flask run
```
