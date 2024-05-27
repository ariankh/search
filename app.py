from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

app = FastAPI()

# Define your OpenAI API key
openai.api_key = 'YOUR_OPENAI_API_KEY'

# Define the request body for querying the language model
class QueryRequest(BaseModel):
    user_input: str
    search_url: str

@app.post("/query")
async def query_language_model(query_request: QueryRequest):
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
