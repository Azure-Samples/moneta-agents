import argparse
import asyncio
import logging

from .remote import AskableHost, RESTHost, find_askables
from .grpc import GRPCHost

from dotenv import load_dotenv
load_dotenv(override=True)

# Configure logging
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Run the RESTHost server.")
    parser.add_argument("--type", type=str, default="rest", help="Type of server to run (rest or grpc).")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on.")
    parser.add_argument("--port", type=int, default=7000, help="Port to run the server on.")
    parser.add_argument("--source-dir", type=str, default=None, help="Directory to search for askables.")
    parser.add_argument('--log-level', default='INFO', help='Set the logging level')
    
    args = parser.parse_args()
    
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logging.basicConfig(level=log_level)
    logger.setLevel(log_level)

    askables = find_askables(args.source_dir)
    
    if len(askables) == 0:
        logger.error("No askables found")
        return
    
    logger.info("Found %d askables", len(askables))
    host: AskableHost = None
    if args.type == "rest":
        host = RESTHost(askables, args.host, args.port)
    elif args.type == "grpc":
        host = GRPCHost(askables, args.host, args.port)
    else:
        raise ValueError(f"Invalid server type: {args.type}")
    
    try:
        logger.info(f"Starting {args.type} server on {args.host}:{args.port}...")
        host.start()
        loop = asyncio.get_event_loop()
        try:
            loop.run_forever()
        finally:
            loop.close()
    except KeyboardInterrupt:
        logger.info("Stopping server...")
        host.stop()

if __name__ == "__main__":
    main()