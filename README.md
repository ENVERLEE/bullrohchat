# Bullroh Chat

Bullroh Chat is an AI-powered chatbot that answers questions based on blog content. It uses advanced natural language processing to provide accurate and context-aware responses.

## Features

- **Blog Crawling**: Automatically gathers and processes blog content
- **Question Answering**: Provides precise answers to user queries
- **Web Interface**: User-friendly interface for interacting with the chatbot
- **Real-time Chat**: Interactive conversation interface

## Installation

1. Clone the repository:
   ```bash
   git clone [repository URL]
   cd bullrohchat
   ```

2. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set environment variables (create a `.env` file):
   ```
   OPENAI_API_KEY=your_openai_api_key
   # Other required environment variables
   ```

## Web Interface Usage

1. Run the web application:
   ```bash
   python web_app.py
   ```

2. Access the web interface in your browser:
   ```
   http://localhost:5000
   ```

3. Interact with the chatbot:
   - Start/stop the chatbot
   - Engage in real-time conversations
   - View conversation history

## API Server Usage

To run the FastAPI server, use the following command:

```bash
python run_api.py
```

The API is accessible at http://localhost:8000.

### Available Endpoints

- `GET /ask?query=...`: Returns answers to questions

### API Usage Examples

**Ask a question**
```bash
curl "http://localhost:8000/ask?query=What's%20the%20best%20tire%20for%20winter"
```

**Trigger blog crawling**
```bash
curl -X POST "http://localhost:8000/crawl?max_posts=10"
```

**Set up business information**
```bash
curl -X POST "http://localhost:8000/onboard" \
  -d "business_name=AutoExpert" \
  -d "blog_url=https://auto-blog.example.com" \
  -d "chatbot_personality=Professional%20and%20technical"
```

## Podman Deployment

1. Build the container image:
   ```bash
   podman build -t bullrohchat .
   ```

2. (Optional) Save the image:
   ```bash
   podman save -o bullrohchat.tar bullrohchat
   ```

3. Run the container:
   ```bash
   podman run -d --name bullrohchat-container -p 8000:8000 bullrohchat
   ```

4. Access the API:
   http://localhost:8000

## Existing CLI Commands

You can still use the existing CLI commands:

```bash
# Onboarding (initial setup)
python main.py onboard

# Blog crawling
python main.py crawl

# Ask questions via CLI
python main.py ask "Question content"
```

## Open Source Licenses

This project uses the following open source libraries:

- **FastAPI** (MIT License): https://github.com/tiangolo/fastapi
- **uvicorn** (MIT License): https://github.com/encode/uvicorn
- **python-dotenv** (BSD-3-Clause License): https://github.com/theskumar/python-dotenv
- **requests** (Apache License 2.0): https://github.com/psf/requests
- **beautifulsoup4** (MIT License): https://www.crummy.com/software/BeautifulSoup/
- **oracledb** (Apache License 2.0): https://github.com/oracle/python-oracledb
- **langchain** (MIT License): https://github.com/langchain-ai/langchain
- **tiktoken** (MIT License): https://github.com/openai/tiktoken

Check each library's official website for full license details. You must comply with all license requirements when distributing this project.

## License

This project is licensed under the [MIT License](LICENSE).
