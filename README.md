git clone <repository-url>
cd political-stance-analyzer
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r dependencies.txt
```

4. Set up environment variables:
Create a `.env` file in the project root with the following variables:
```
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
SESSION_SECRET=your_secret_key
```

5. Initialize the database:
```bash
flask db upgrade
```

6. Start the application:
```bash
python main.py