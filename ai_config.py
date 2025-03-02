from langchain_community.llms import Ollama
from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler
from langchain_core.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate
)
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain.chains import LLMChain
from ollama_setup import OllamaManager
import os
import logging
import json
import time
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Ollama manager
ollama_manager = OllamaManager()

# Callback manager for streaming output
callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])

# System prompts
SYSTEM_TEMPLATE = """You are an expert AI technical interviewer and coding assistant. 
Provide detailed assessments and constructive feedback for interview responses.
Always respond in English and maintain a professional tone.
IMPORTANT: Always respond with clean, properly formatted JSON. Do not include any <think> tags, markdown formatting, or explanations outside of the JSON structure.
"""

# Initialize Ollama model
def init_llama():
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            # Connect to Ollama server
            if not ollama_manager.start_ollama():
                logger.error(f"Failed to connect to Ollama server (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None

            # Check if model exists without pulling
            try:
                response = requests.get(f"{ollama_manager.base_url}/api/tags")
                models = response.json().get("models", [])
                model_exists = any(m.get("name") == "deepseek-r1" or m.get("name") == "deepseek-r1:latest" for m in models)
                
                if not model_exists:
                    logger.warning("Model not found, attempting to pull...")
                    ollama_manager.pull_model("deepseek-r1")
                else:
                    logger.info("Model deepseek-r1 found")
                    
            except Exception as e:
                logger.error(f"Model check failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None

            # Initialize the model with improved settings
            llm = Ollama(
                model="deepseek-r1",
                temperature=0.2,  # Lower temperature for more deterministic outputs
                callback_manager=callback_manager,
                num_ctx=4096,  # Ensure sufficient context window
                num_predict=1024,  # Limit output length
                stop=["</s>", "<think>", "</think>"]  # Stop generation at these tokens
            )
            
            # Test the model with a simple prompt
            try:
                test_response = llm.invoke("test")
                logger.info("Model initialized and tested successfully")
                return llm
            except Exception as e:
                logger.error(f"Model test failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
                
        except Exception as e:
            logger.error(f"Error initializing Ollama (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return None
    
    logger.error("Failed to initialize LLM after all retries")
    return None

# Output parser for JSON responses
class InterviewAssessmentParser(JsonOutputParser):
    def parse(self, text):
        try:
            # Clean the text to ensure it's valid JSON
            text = text.strip()
            
            # Remove any <think> tags that might be in the output
            text = text.replace('<think>', '').replace('</think>', '')
            
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
            return json.loads(text)
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

IMPORTANT: Respond ONLY with a valid JSON object. Do not include any explanations, markdown formatting, or <think> tags.
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

IMPORTANT: Respond ONLY with a valid JSON object. Do not include any explanations, markdown formatting, or <think> tags.
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