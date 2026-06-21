import asyncio
from app.services.youtube import youtube_service

async def test():
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    video_id = youtube_service.extract_video_id(video_url)
    print(f"Video ID: {video_id}")
    
    try:
        metadata = await youtube_service.get_metadata(video_id)
        print(f"Metadata: {metadata}")
    except Exception as e:
        print(f"Metadata error: {e}")

    try:
        transcript = youtube_service.get_transcript(video_id)
        print(f"Transcript source: {transcript['source']}")
        print(f"Transcript snippet: {transcript['raw'][:100]}...")
    except Exception as e:
        print(f"Transcript error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
