import os
import logging
import json
import time
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
    PromptTemplate
)
from langchain_core.output_parsers import JsonOutputParser
from langchain.chains import LLMChain
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from typing import Dict, Any, Optional
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Gemini API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    logger.error("GOOGLE_API_KEY environment variable not set")
    raise ValueError("GOOGLE_API_KEY environment variable not set")

genai.configure(api_key=GOOGLE_API_KEY)

# System prompts
SYSTEM_TEMPLATE = """You are an expert AI technical interviewer and coding assistant. 
Provide detailed assessments and constructive feedback for interview responses.
Always respond in English and maintain a professional tone.
IMPORTANT: Always respond with clean, properly formatted JSON. Do not include any explanations outside of the JSON structure.
"""

# Initialize Gemini model
def init_gemini():
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            # Initialize the Gemini model with LangChain
            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-pro-latest",
                temperature=0.2,
                google_api_key=GOOGLE_API_KEY,
                convert_system_message_to_human=True
            )
            
            # Test the model with a simple prompt
            try:
                test_response = llm.invoke("test")
                logger.info("Gemini model initialized and tested successfully")
                return llm
            except Exception as e:
                logger.error(f"Gemini model test failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
                
        except Exception as e:
            logger.error(f"Error initializing Gemini (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return None
    
    logger.error("Failed to initialize Gemini model after all retries")
    return None

# Output parser for JSON responses
class InterviewAssessmentParser(JsonOutputParser):
    def parse(self, text):
        try:
            # If text is already a dict, just validate and return it
            if isinstance(text, dict):
                assessment = text
            else:
                # Clean the text to ensure it's valid JSON
                text = text.strip()
                
                # Extract JSON from markdown code blocks if present
                if text.startswith('```json'):
                    text = text[7:]
                    if text.endswith('```'):
                        text = text[:-3]
                elif text.startswith('```'):
                    # Handle code blocks without language specification
                    text = text[3:]
                    if text.endswith('```'):
                        text = text[:-3]
                
                # Find the first { and last } to extract JSON
                start_idx = text.find('{')
                end_idx = text.rfind('}')
                
                if start_idx != -1 and end_idx != -1:
                    text = text[start_idx:end_idx+1]
                
                # Parse the JSON
                assessment = json.loads(text)
            
            # Validate and ensure required fields
            if not isinstance(assessment.get('score'), (int, float)):
                assessment['score'] = 70
            
            if not isinstance(assessment.get('strengths'), list):
                assessment['strengths'] = ["Basic understanding shown"]
            
            if not isinstance(assessment.get('improvements'), list):
                assessment['improvements'] = ["Add more detail"]
            
            if not isinstance(assessment.get('feedback'), str):
                assessment['feedback'] = "Answer shows basic understanding but needs more depth."
            
            return assessment
            
        except Exception as e:
            logger.error(f"Error parsing JSON: {str(e)}")
            return {
                "score": 70,
                "strengths": ["Basic understanding shown", "Attempted to answer", "Shows potential"],
                "improvements": ["Add more detail", "Include examples", "Better structure"],
                "feedback": "Answer shows basic understanding but needs more depth."
            }

# Interview assessment prompt template
INTERVIEW_ASSESSMENT_TEMPLATE = """
You are an experienced technical interviewer evaluating a candidate's response.
Analyze the following response carefully and provide a detailed assessment.

Role: {role}
Question: {question}
Candidate's Answer: {answer}

IMPORTANT: Respond ONLY with a valid JSON object. Do not include any explanations outside the JSON.
Provide your assessment in this exact JSON format:
{{
    "score": <number 0-100>,
    "strengths": ["<specific strength 1>", "<specific strength 2>", "<specific strength 3>"],
    "improvements": ["<specific improvement 1>", "<specific improvement 2>", "<specific improvement 3>"],
    "feedback": "<2-3 sentences of constructive overall feedback>"
}}

Guidelines:
- Score should reflect technical accuracy, completeness, and clarity
- Strengths should be specific and highlight technical competencies
- Improvements should be actionable and specific
- Feedback should be constructive and professional
"""

# Question generation prompt template
QUESTION_GENERATION_TEMPLATE = """
Generate a technical interview question following these specifications:

Role: {role}
Level: {level}
Technology: {technology}

IMPORTANT: Respond ONLY with a valid JSON object. Do not include any explanations outside the JSON.
Provide your response in this exact JSON format:
{{
    "question": "<detailed technical interview question>",
    "expected_topics": ["<topic 1>", "<topic 2>", "<topic 3>"],
    "difficulty": "<easy/medium/hard>",
    "ideal_answer_points": ["<key point 1>", "<key point 2>", "<key point 3>"]
}}
"""

# Initialize prompt templates with output parser
assessment_parser = InterviewAssessmentParser()
question_parser = InterviewAssessmentParser()

interview_prompt = PromptTemplate(
    input_variables=["role", "question", "answer"],
    template=INTERVIEW_ASSESSMENT_TEMPLATE
)

question_prompt = PromptTemplate(
    input_variables=["role", "level", "technology"],
    template=QUESTION_GENERATION_TEMPLATE
)

# Create LangChain chains
def create_assessment_chain(llm):
    if llm is None:
        raise ValueError("LLM initialization failed")
    return LLMChain(
        llm=llm,
        prompt=interview_prompt,
        output_parser=assessment_parser,
        verbose=False  # Set to False to avoid unnecessary output
    )

def create_question_chain(llm):
    if llm is None:
        raise ValueError("LLM initialization failed")
    return LLMChain(
        llm=llm,
        prompt=question_prompt,
        output_parser=question_parser,
        verbose=False  # Set to False to avoid unnecessary output
    )

# Add this new function for checking AI service status
def check_ai_services_status() -> Dict[str, Any]:
    """Check the status of all AI services and return detailed status information."""
    status = {
        'llm': {
            'available': False,
            'error': None,
            'details': None
        },
        'vector_store': {
            'available': False,
            'error': None,
            'details': None
        },
        'assessment_chain': {
            'available': False,
            'error': None
        },
        'question_chain': {
            'available': False,
            'error': None
        }
    }
    
    try:
        # Test LLM
        llm = init_gemini()
        if llm is not None:
            test_response = llm.invoke("test")
            status['llm']['available'] = True
            status['llm']['details'] = "Gemini model responding correctly"
        else:
            status['llm']['error'] = "Failed to initialize Gemini model"
    except Exception as e:
        status['llm']['error'] = str(e)
        status['llm']['details'] = traceback.format_exc()

    try:
        # Test vector store
        vs = init_vector_store()
        if vs is not None:
            status['vector_store']['available'] = True
            status['vector_store']['details'] = "Vector store initialized successfully"
        else:
            status['vector_store']['error'] = "Failed to initialize vector store"
    except Exception as e:
        status['vector_store']['error'] = str(e)
        status['vector_store']['details'] = traceback.format_exc()

    # Update the assessment and question chain status based on LLM availability
    if status['llm']['available']:
        try:
            if assessment_chain is not None:
                status['assessment_chain']['available'] = True
            if question_chain is not None:
                status['question_chain']['available'] = True
        except Exception as e:
            logger.error(f"Error checking chain status: {e}")
    
    return status

# Modify the init_vector_store function to be more robust
def init_vector_store() -> Optional[Any]:
    """Initialize the vector store with better error handling."""
    try:
        # Initialize HuggingFace embeddings
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # Check if questions.json exists
        if not os.path.exists('frontend/assets/questions.json'):
            logger.error("questions.json file not found")
            return None
            
        # Load questions from JSON
        try:
            with open('frontend/assets/questions.json', 'r', encoding='utf-8') as f:
                questions_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in questions.json: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading questions.json: {e}")
            return None
        
        # Validate questions data structure
        if not isinstance(questions_data, dict):
            logger.error("questions.json root must be a dictionary")
            return None
            
        if 'job_roles' not in questions_data:
            logger.error("questions.json missing 'job_roles' key")
            return None
            
        if not isinstance(questions_data['job_roles'], list):
            logger.error("'job_roles' must be a list")
            return None
        
        # Prepare documents for vector store
        documents = []
        metadatas = []
        
        for role_data in questions_data['job_roles']:
            if not isinstance(role_data, dict):
                logger.warning("Skipping invalid role_data entry")
                continue
                
            role = role_data.get('role')
            questions = role_data.get('questions', [])
            
            if not role or not isinstance(questions, list):
                logger.warning(f"Skipping invalid role entry: {role}")
                continue
            
            for question in questions:
                if question and isinstance(question, str):
                    documents.append(question)
                    metadatas.append({"role": role})
        
        if not documents:
            logger.error("No valid questions found in questions.json")
            return None
        
        # Create vector store
        vector_store = FAISS.from_texts(
            texts=documents,
            embedding=embeddings,
            metadatas=metadatas
        )
        
        logger.info(f"Vector store initialized with {len(documents)} questions")
        return vector_store
        
    except Exception as e:
        logger.error(f"Error initializing vector store: {str(e)}")
        logger.error(traceback.format_exc())
        return None

# Function to get similar questions based on context
def get_similar_questions(vector_store, context, role=None, k=3):
    if vector_store is None:
        logger.error("Vector store not initialized")
        return []
    
    try:
        # Search for similar questions
        if role:
            # Filter by role if provided
            results = vector_store.similarity_search_with_score(
                context, 
                k=k*2,  # Get more results to filter
                filter={"role": role}
            )
            # If not enough results with role filter, try without filter
            if len(results) < k:
                results = vector_store.similarity_search_with_score(context, k=k)
        else:
            results = vector_store.similarity_search_with_score(context, k=k)
        
        # Extract questions
        questions = [doc[0].page_content for doc in results[:k]]
        return questions
    
    except Exception as e:
        logger.error(f"Error getting similar questions: {str(e)}")
        return [] 

# Add these global variables at the module level
llm = None
assessment_chain = None
question_chain = None
vector_store = None

# Initialize all components
def initialize_ai_components():
    """Initialize all AI components with proper error handling."""
    global llm, assessment_chain, question_chain, vector_store
    
    try:
        logger.info("Initializing AI components...")
        
        # Initialize LLM
        llm = init_gemini()
        if llm is None:
            logger.error("Failed to initialize Gemini model")
            return False
            
        # Initialize chains
        assessment_chain = create_assessment_chain(llm)
        question_chain = create_question_chain(llm)
        
        # Initialize vector store
        vector_store = init_vector_store()
        if vector_store is None:
            logger.error("Failed to initialize vector store")
            return False
            
        logger.info("AI components initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during AI components initialization: {e}")
        logger.error(traceback.format_exc())
        return False

# Call this function when the module is imported
initialize_ai_components() 