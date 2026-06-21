import asyncio
import os
from app.agents.summary_agent import VideoSummaryOrchestrator

# Mocking Anthropic client for a quick check if it's reachable or if it fails on init
# Since I don't have an API key here, I'll just check if the code runs up to the client call

async def test():
    orchestrator = VideoSummaryOrchestrator()
    print("Orchestrator initialized.")
    
    # This will fail due to missing API key, but we want to see if the imports and logic are sound
    try:
        result = await orchestrator.process(
            raw_transcript="Hola a todos, bienvenidos a este video sobre inteligencia artificial.",
            transcript_with_timestamps="[00:00] Hola a todos, bienvenidos a este video sobre inteligencia artificial.",
            title="Video de prueba",
            duration_seconds=60,
            language="es"
        )
        print(f"Result: {result}")
    except Exception as e:
        print(f"AI Error (expected if no key): {e}")

if __name__ == "__main__":
    # Set a dummy key to see if it reaches the API call
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
    asyncio.run(test())
