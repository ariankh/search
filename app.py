from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel
import openai
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from typing import List
from fastapi.security.api_key import APIKeyHeader, APIKey
from fastapi.middleware.cors import CORSMiddleware
from starlette.status import HTTP_403_FORBIDDEN
from functools import lru_cache
import os
import logging
import time

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Environment variables for sensitive information
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'YOUR_OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY
API_KEY = os.getenv('API_KEY', 'YOUR_API_KEY')

# Security
api_key_header = APIKeyHeader(name='X-API-KEY')

# Rate limiting (requests per minute)
RATE_LIMIT = 60
rate_limit_cache = {}

def get_api_key(request: Request, api_key_header: str = Depends(api_key_header)):
    if api_key_header != API_KEY:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials")
    return api_key_header

def rate_limiter(api_key: APIKey):
    current_time = time.time()
    if api_key not in rate_limit_cache:
        rate_limit_cache[api_key] = []
    requests = rate_limit_cache[api_key]
    requests = [req for req in requests if current_time - req < 60]
    if len(requests) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    requests.append(current_time)
    rate_limit_cache[api_key] = requests

# Define the request body for querying the language model
class QueryRequest(BaseModel):
    user_input: str
    search_url: str

@app.post("/query", dependencies=[Depends(get_api_key)])
async def query_language_model(query_request: QueryRequest, api_key: APIKey = Depends(get_api_key)):
    rate_limiter(api_key)
    
    try:
        # Generate a response from the language model
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=query_request.user_input,
            max_tokens=100
        )
        generated_text = response.choices[0].text.strip()
        
        # Perform search on the specified URL
        search_results = perform_search(query_request.search_url, generated_text)
        
        return {"generated_text": generated_text, "search_results": search_results}
    except openai.error.OpenAIError as e:
        logging.error(f"OpenAI API error: {e}")
        raise HTTPException(status_code=500, detail="Language model service error")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

def perform_search(url, query):
    # Configure Selenium
    options = Options()
    options.headless = True
    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get(url)
        search_box = driver.find_element(By.NAME, "q")  # This assumes the search box's name attribute is 'q'
        search_box.send_keys(query)
        search_box.submit()
        
        # Extract search results
        results = driver.find_elements(By.CSS_SELECTOR, 'h3')  # Example selector for search results
        search_results = [result.text for result in results[:5]]  # Get the top 5 results
        
        return search_results
    finally:
        driver.quit()

# Run the API with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
