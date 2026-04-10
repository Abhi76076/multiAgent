import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Import the existing Agent class
from simulation import Agent

load_dotenv()

app = FastAPI()

# Mount the static directory to serve front-end files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.websocket("/ws/simulate")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        # Wait for the topic from the client
        data = await websocket.receive_json()
        topic = data.get("topic", "").strip()
        if not topic:
            topic = "The impact of Artificial General Intelligence (AGI) on human creativity and jobs."
            
        # Instantiate agents
        moderator = Agent(
            "Moderator", 
            "You are the moderator of a mature and formal debate. You introduce the topic objectively, keep the debaters on track, and provide a balanced final summary."
        )
        agent_a = Agent(
            "Agent Alpha", 
            "You are an optimistic proponent. You strongly believe in the positive potential of the given topic and focus on benefits, opportunities, and progress."
        )
        agent_b = Agent(
            "Agent Beta", 
            "You are a cautious skeptic. You believe the current topic poses significant risks and focus on challenges, drawbacks, and the need for strict regulation or caution."
        )
        
        rounds = 2
        transcript = f"Topic of Discussion: {topic}\n"

        async def send_status(agent_name, status):
            # Tell the frontend if an agent is thinking or idle
            await websocket.send_json({"type": "status", "agent": agent_name, "status": status})

        async def send_message(agent_name, text):
            # Send the completed message from an agent
            await websocket.send_json({"type": "message", "agent": agent_name, "text": text})

        # 1. Moderator Intro
        await send_status("Moderator", "thinking")
        intro = await moderator.respond_async( 
            transcript, 
            "Provide a brief introduction to the topic (1 paragraph) and invite Agent Alpha to begin."
        )
        transcript += f"\nModerator: {intro}\n"
        await send_message("Moderator", intro)
        await send_status("Moderator", "idle")
        
        for i in range(rounds):
            await websocket.send_json({"type": "round", "number": i+1})
            
            # Agent Alpha
            await send_status("Agent Alpha", "thinking")
            resp_a = await agent_a.respond_async(
                transcript, 
                "Provide your argument/response. Keep it concise, around 1-2 paragraphs."
            )
            transcript += f"\nAgent Alpha: {resp_a}\n"
            await send_message("Agent Alpha", resp_a)
            await send_status("Agent Alpha", "idle")
            
            # Agent Beta
            await send_status("Agent Beta", "thinking")
            resp_b = await agent_b.respond_async(
                transcript, 
                "Provide your counter-argument/response. Keep it concise, around 1-2 paragraphs."
            )
            transcript += f"\nAgent Beta: {resp_b}\n"
            await send_message("Agent Beta", resp_b)
            await send_status("Agent Beta", "idle")
            
        await websocket.send_json({"type": "round", "number": "Conclusion"})
        
        # Moderator Conclusion
        await send_status("Moderator", "thinking")
        conclusion = await moderator.respond_async(
            transcript, 
            "The debate has concluded. Please provide a fair summary of the main points from both sides and offer a brief concluding thought."
        )
        await send_message("Moderator", conclusion)
        await send_status("Moderator", "idle")

        # Finished
        await websocket.send_json({"type": "finished"})

    except WebSocketDisconnect:
        print("Client WebSocket disconnected")
    except Exception as e:
        await websocket.send_json({"type": "error", "message": f"Simulation Error: {str(e)}"})
