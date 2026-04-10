import os
import time
import asyncio
from google import genai
from google.genai import types
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from groq import AsyncGroq

def log_retry(retry_state):
    print(f"    [!] API is busy. Retrying in {retry_state.next_action.sleep:.1f} seconds (Attempt {retry_state.attempt_number}/8)...")

# Load environment variables from .env file
load_dotenv()

# Initialize the Gemini Client
# It automatically picks up GEMINI_API_KEY from environment variables
try:
    client = genai.Client()
except Exception as e:
    print(f"Error initializing Google GenAI Client: {e}")
    print("Please ensure you have set GEMINI_API_KEY in your .env file.")
    exit(1)

# Initialize Groq Client
try:
    groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY", ""))
except Exception as e:
    print(f"Error initializing Groq Client: {e}. Groq fallbacks will fail.")

class Agent:
    def __init__(self, name, role, model_name="gemini-2.5-flash"):
        self.name = name
        self.role = role
        self.model_name = model_name
        self.system_instruction = f"You are {name}. {role}"

    @retry(stop=stop_after_attempt(8), wait=wait_exponential(multiplier=2, min=4, max=30), reraise=True, before_sleep=log_retry)
    def _generate_with_retry(self, prompt):
        return client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                temperature=0.7,
            )
        )

    def respond(self, context, extra_instructions=""):
        print(f"[{self.name} is thinking...]")
        prompt = "Here is the conversation so far:\n" + context + f"\n\nNow {self.name}, provide your next response. {extra_instructions}"
        try:
            response = self._generate_with_retry(prompt)
            time.sleep(2)
            return response.text.strip()
        except Exception as e:
            return f"Error computing response: {str(e)}"

    async def respond_async(self, context, extra_instructions=""):
        print(f"[{self.name} is thinking async...]")
        prompt = "Here is the conversation so far:\n" + context + f"\n\nNow {self.name}, provide your next response. {extra_instructions}"
        
        fallback_models = ["gemini-2.5-flash", "gemini-2.0-flash", "llama3-8b-8192", "llama-3.3-70b-versatile"]
        
        for model_name in fallback_models:
            print(f"    [!] Attempting free model API: {model_name}")
            try:
                if "gemini" in model_name:
                    response = await asyncio.wait_for(
                        client.aio.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=self.system_instruction,
                                temperature=0.7,
                            )
                        ),
                        timeout=10.0
                    )
                    await asyncio.sleep(1) # brief pause
                    return response.text.strip()
                else:
                    response = await asyncio.wait_for(
                        groq_client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {"role": "system", "content": self.system_instruction},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.7
                        ),
                        timeout=10.0
                    )
                    await asyncio.sleep(1)
                    return response.choices[0].message.content.strip()

            except asyncio.TimeoutError:
                print(f"    [!] Model {model_name} did not respond within 10 seconds. Switching to next model...")
                continue
            except Exception as e:
                print(f"    [!] Model {model_name} failed: {e}. Switching to next model...")
                continue
                
        return "Error computing response: All fallback models either timed out or failed to respond."

def main():
    print("="*60)
    print("   Multi-Agent System Simulation (Powered by Gemini)   ")
    print("="*60)
    
    topic = input("Enter a topic for debate/discussion (or press Enter for default): ")
    if not topic.strip():
        topic = "The impact of Artificial General Intelligence (AGI) on human creativity and jobs."
        
    print(f"\n--- Simulation Started: {topic} ---\n")
    
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
    
    # Context holds the transcript of the simulation
    transcript = f"Topic of Discussion: {topic}\n"
    
    # 1. Moderator Intro
    intro = moderator.respond(transcript, "Provide a brief introduction to the topic (1 paragraph) and invite Agent Alpha to begin.")
    print(f"\n[ MODERATOR ]\n{intro}\n")
    transcript += f"\nModerator: {intro}\n"
    
    for i in range(rounds):
        print(f"\n{'='*20} ROUND {i+1} {'='*20}")
        
        # 2. Agent Alpha's Turn
        resp_a = agent_a.respond(transcript, "Provide your argument/response. Keep it concise, around 1-2 paragraphs.")
        print(f"\n[ AGENT ALPHA ]\n{resp_a}\n")
        transcript += f"\nAgent Alpha: {resp_a}\n"
        
        # 3. Agent Beta's Turn
        resp_b = agent_b.respond(transcript, "Provide your counter-argument/response. Keep it concise, around 1-2 paragraphs.")
        print(f"\n[ AGENT BETA ]\n{resp_b}\n")
        transcript += f"\nAgent Beta: {resp_b}\n"
        
    print(f"\n{'='*20} CONCLUSION {'='*20}")
    
    # 4. Moderator Conclusion
    conclusion = moderator.respond(transcript, "The debate has concluded. Please provide a fair summary of the main points from both sides and offer a brief concluding thought.")
    print(f"\n[ MODERATOR ]\n{conclusion}\n")

if __name__ == "__main__":
    main()
