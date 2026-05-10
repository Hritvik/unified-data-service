import asyncio
import os
import sys

# Ensure PYTHONPATH includes current directory
sys.path.append(os.getcwd())

import os
os.environ["UDS_CONFIG_DIRECTORY"] = "/Users/hritvikdinkar/repositories/unified-data-service/config/services"

from factories.service_factory import ServiceFactory
from config.settings import Settings

async def test():
    # Mock settings
    settings = Settings()
    os.environ["UDS_CONFIG_DIRECTORY"] = "/Users/hritvikdinkar/repositories/unified-data-service/config/services"
    
    factory = ServiceFactory(settings)
    print("Loading services...")
    try:
        await factory.load_services_from_config()
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
