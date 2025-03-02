# Interview Helper

A comprehensive platform for technical interview preparation and conducting remote interviews with AI assistance.

## Features

- **Practice Mode**: Practice technical interview questions with AI feedback
- **Interview Mode**: Conduct real-time interviews with video, audio, and chat
- **AI-Powered Question Generation**: Get relevant technical questions based on job roles
- **Vector Search**: Find similar questions based on conversation context
- **Voice Analysis**: Get question suggestions based on voice transcripts
- **Performance Analytics**: Track your practice performance over time

## New Features

- **Gemini AI Integration**: Replaced Ollama with Google's Gemini API for more reliable AI responses
- **Vector Search**: Added semantic search using HuggingFace embeddings and FAISS
- **Interview Room Questions**: Interviewers can now generate relevant questions during interviews
- **Voice Analysis**: Get question suggestions based on voice transcripts during interviews

## Setup

### Windows Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/interview-helper.git
   cd interview-helper
   ```

2. Run the setup script:
   ```
   setup.bat
   ```
   This will:
   - Create a virtual environment
   - Install all required packages
   - Download necessary NLTK data

3. Make sure MongoDB is installed and running
   - Download from: https://www.mongodb.com/try/download/community
   - Start the MongoDB service

4. Run the application:
   - In one terminal: `run_app.bat`
   - In another terminal: `run_interview_server.bat`

5. Access the application at http://localhost:5001

### Manual Setup (Linux/Mac)

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/interview-helper.git
   cd interview-helper
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Initialize NLTK data (for voice analysis):
   ```
   python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
   ```

4. Set up environment variables:
   ```
   cp .env.example .env
   ```
   
   Edit the `.env` file and add your:
   - MongoDB connection string
   - Flask secret key
   - Google API key for Gemini (get one from https://makersuite.google.com/app/apikey)

5. Start the application:
   ```
   python app.py
   ```

6. In a separate terminal, start the interview server:
   ```
   python interview_server.py
   ```

7. Access the application at http://localhost:5001

## Using the Interview Room

1. Schedule an interview as an interviewer
2. Share the interview key with the interviewee
3. Join the interview room
4. As an interviewer, you can:
   - Use the "Get Interview Question" button to generate relevant questions
   - Select different job roles from the dropdown
   - Click on suggested questions that appear based on the conversation
   - Use voice recognition to get question suggestions based on what's being discussed

## Architecture

- **Frontend**: HTML, CSS (Tailwind), JavaScript
- **Backend**: Flask, Flask-SocketIO, MongoDB
- **AI Components**:
  - Google Gemini API for question generation and answer assessment
  - LangChain for prompt engineering and chain management
  - HuggingFace Transformers for embeddings
  - FAISS for vector search
  - NLTK for voice transcript analysis

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
