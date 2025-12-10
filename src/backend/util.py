"""
Utility functions for the Moneta backend.
"""
from io import StringIO
from subprocess import run, PIPE
import logging
from dotenv import load_dotenv


def load_dotenv_from_azd():
    """Load environment variables from azd or fall back to .env file."""
    result = run("azd env get-values", stdout=PIPE, stderr=PIPE, shell=True, text=True)
    if result.returncode == 0:
        logging.info("Found AZD environment. Loading...")
        load_dotenv(stream=StringIO(result.stdout))
    else:
        logging.info("AZD environment not found. Trying to load from .env file...")
        load_dotenv()
