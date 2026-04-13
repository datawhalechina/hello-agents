import sys
from pathlib import Path

# Add src to sys.path
# backend/scripts/test_agent_workflow.py -> backend/src
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src"))

from dotenv import load_dotenv

# Load env from backend/.env
env_path = project_root / ".env"
if env_path.exists():
    print(f"Loading environment from {env_path}")
    load_dotenv(env_path)
else:
    print(f"Warning: .env file not found at {env_path}")

import logging
import shutil

from agent import DeepResearchAgent
from config import Configuration, SearchAPI


def configure_logging():
    # Set global level to INFO first
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    # Suppress verbose logs from specific loggers
    loggers_to_silence = [
        "services.tool_events", 
        "services.planner",
        "services.search",
        "services.audio_generator",
        "services.audio_synthesizer",
        "services.script_generator",
        "httpx",
        "httpcore",
        "urllib3",
        "hello_agents"
    ]
    for logger_name in loggers_to_silence:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

def main():
    configure_logging()
    print("Initializing DeepResearchAgent...")
    # Initialize with default config (will load from env)
    config = Configuration.from_env()
    
    # Override for testing speed
    config.max_web_research_loops = 1
    # Enable TTS for full workflow test
    # config.tts_api_key = None 
    # Use Tavily for search as DDG is flaky
    config.search_api = SearchAPI.TAVILY
    
    print(f"Max Web Research Loops: {config.max_web_research_loops} (Overridden for testing)")

    
    # Print some config to verify
    print("\nCurrent Configuration:")
    print(f"LLM Provider: {config.llm_provider}")
    print(f"Model: {config.resolved_model()}")
    print(f"Smart Model: {config.smart_llm_model}")
    print(f"Fast Model: {config.fast_llm_model}")
    print(f"Search API: {config.search_api}")
    print(f"TTS Enabled: {bool(config.tts_api_key)}")
    print(f"FFmpeg Path: {config.ffmpeg_path}")
    
    agent = DeepResearchAgent(config=config)
    
    # Clean up previous audio outputs
    output_dir = Path(config.audio_output_dir)
    if output_dir.exists():
        print(f"Cleaning up output directory: {output_dir}")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    topic = "DeepSeek Technical Report"
    print(f"Starting research on topic: {topic}")
    
    try:
        result = agent.run(topic)
        
        print("\n" + "="*50)
        print("WORKFLOW COMPLETED SUCCESSFULLY")
        print("="*50)
        
        # running_summary may be None; guard against calling len(None)
        summary_len = len(result.running_summary) if result.running_summary else 0
        print(f"Report Summary Length: {summary_len}")
        
        print("\n" + "="*20 + " REPORT CONTENT " + "="*20)
        if result.running_summary:
            print(result.running_summary)
        else:
            print("(No report generated)")
        print("="*56 + "\n")
        
        if result.podcast_script:
            print(f"Podcast Script Generated: Yes ({len(result.podcast_script)} dialogue items)")
        else:
            print("Podcast Script Generated: No")
            
        # Check output files
        output_dir = Path(config.audio_output_dir)
        if output_dir.exists():
            print(f"\nAudio Output Directory: {output_dir}")
            files = list(output_dir.glob("*"))
            print(f"Files generated ({len(files)}):")
            for f in files:
                print(f" - {f.name}")
        else:
            print(f"\nAudio Output Directory not found: {output_dir}")
            
    except Exception as e:
        print(f"\nERROR: Workflow failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
