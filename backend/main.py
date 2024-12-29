from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio
from fastapi.responses import StreamingResponse
from langchain.memory import ConversationBufferMemory

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("Gemini API key not found. Please configure GEMINI_API_KEY in the .env file.")

genai.configure(api_key=API_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)

class UserInput(BaseModel):
    query: str

# Initialize memory buffer, this will hold the entire conversation
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

@app.post("/generate")
async def generate_response(user_input: UserInput):
    logging.info(f"Received query: {user_input.query}")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Load all history from memory
        history = memory.load_memory_variables({})
        past_messages = history.get("chat_history", [])

        # Construct the full prompt with all conversation history
        full_prompt = f"""
        You are a helpful assistant. Your task is to respond to the user query as clearly and concisely as possible. 
        Maintain a friendly and informative tone. With a slightly big response message, you can break it down into smaller

        History of conversation so far:
        {past_messages}
        
        User: {user_input.query}
        """

        # Generate the response from the model
        response = model.generate_content(full_prompt)
        result = response.text

        # Save the conversation context (user's query and AI's response) to memory
        memory.save_context({"input": user_input.query}, {"output": result})

        async def stream_response():
            buffer = ""
            for word in result.split():
                buffer += word + " "
                if len(buffer) > 20:  # Send in chunks of 50 words
                    yield f"{buffer.strip()}\n\n"  
                    buffer = ""
                    await asyncio.sleep(0.05)
            if buffer:
                yield f"{buffer.strip()}\n\n" 

        return StreamingResponse(stream_response(), media_type="text/event-stream")

    except genai.GenerationError as e:
        logging.error("API Error: %s", e)
        raise HTTPException(status_code=500, detail="AI generation error.")
    except Exception as e:
        logging.error("Error: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error.")



# from fastapi import FastAPI, WebSocket, WebSocketDisconnect
# import google.generativeai as genai
# import os
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()
# API_KEY = os.getenv("GEMINI_API_KEY")

# if not API_KEY:
#     raise RuntimeError("Gemini API key not found. Please configure GEMINI_API_KEY in the .env file.")

# genai.configure(api_key=API_KEY)

# app = FastAPI()
# @app.websocket("/ws/generate")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()  # Accept the incoming WebSocket connection
#     try:
#         while True:
#             query = await websocket.receive_text()  # Receive message from client
#             # Process the query and send response
#             result = "Processed response"
#             await websocket.send_text(result)  # Send response to client
#     except WebSocketDisconnect:
#         print("Client disconnected.")
