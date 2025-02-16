git clone https://github.com/santimber/wahl_analyser.git
cd wahl_analyser
```

2. Install dependencies:
```bash
pip install -r dependencies.txt
```

3. Set up environment variables:
Create a `.env` file in the project root with the following variables:
```
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=your_database_url
SESSION_SECRET=your_secret_key
```

4. Start the application:
```bash
python main.py