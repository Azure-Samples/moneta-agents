import os  
import logging  
import subprocess
import json
import datetime
from fastapi import FastAPI, HTTPException, Body  
from fastapi.responses import JSONResponse  
from azure.identity import DefaultAzureCredential  
from opentelemetry.trace import get_tracer

from conversation_store import ConversationStore  
from gbb.handler import VanillaAgenticHandler  
from sk.handler import SemanticKernelHandler  
  
import util

util.load_dotenv_from_azd()

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s.%(msecs)03d - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
handler.setFormatter(formatter)

# Clear existing handlers and set the new one
root_logger.handlers.clear()
root_logger.addHandler(handler)

logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
logging.getLogger('azure.monitor.opentelemetry.exporter.export').setLevel(logging.WARNING)

app = FastAPI()

@app.post("/http_trigger")
async def http_trigger(request_body: dict = Body(...)):
    logging.info('Empowering RMs - HTTP trigger function processed a request.')
        

    # Extract parameters from the request body  
    user_id = request_body.get('user_id')
    chat_id = request_body.get('chat_id')  # None if starting a new chat
    user_message = request_body.get('message')
    load_history = request_body.get('load_history')
    usecase_type = request_body.get('use_case')
  
    # Validate required parameters
    if not user_id:
        raise HTTPException(status_code=400, detail="<user_id> is required!")
  
    if load_history is not True and not user_message:  
        raise HTTPException(status_code=400, detail="<message> is required when not loading history!")
  
    if not usecase_type:  
        raise HTTPException(status_code=400, detail="<usecase_type> is required!")
    
    tracer = get_tracer(__name__)
    # UNIQUE SESSION ID is a must : get the name of the provider
    # Define current timestamp
    current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    session_id = f"{user_id}-{current_time}"
   
    with tracer.start_as_current_span(session_id):
        # Authenticate using DefaultAzureCredential  
        key = DefaultAzureCredential()
    
        # Select use case container based on usecase_type  
        if usecase_type == 'fsi_insurance':  
            container_name = os.getenv("COSMOSDB_CONTAINER_FSI_INS_USER_NAME")  
        elif usecase_type == 'fsi_banking':  
            container_name = os.getenv("COSMOSDB_CONTAINER_FSI_BANK_USER_NAME")  
        else:  
            raise HTTPException(status_code=400, detail="Use case not recognized/not implemented...")  
    
        # Initialize the ConversationStore with Cosmos DB configurations  
        # TODO: 1. This part needs t be moved to handler
        db = ConversationStore(  
            url=os.getenv("COSMOSDB_ENDPOINT"),  
            key=key,  
            database_name=os.getenv("COSMOSDB_DATABASE_NAME"),  
            container_name=container_name  
        )  
    
        # Check if user exists, if not create a new user  
        if not db.read_user_info(user_id):  
            user_data = {'chat_histories': {}}  
            db.create_user(user_id, user_data)  
    
        user_data = db.read_user_info(user_id)  
        # //: 1

        # Decide which handler to use based on the HANDLER_TYPE environment variable  
        handler_type = os.getenv("HANDLER_TYPE", "semantickernel")  # Expected values: "vanilla", "semantickernel"  

        if handler_type == "vanilla":  
            handler = VanillaAgenticHandler(db)  
        elif handler_type == "semantickernel":  
            handler = SemanticKernelHandler(db)  
        else:  
            raise HTTPException(status_code=400, detail="Invalid HANDLER_TYPE")  
    
        logging.info(f"Handling request with {handler_type} handler...")

        try:  
            result = await handler.handle_request(
                user_id=user_id,
                chat_id=chat_id,
                user_message=user_message,
                load_history=load_history,
                usecase_type=usecase_type,
                user_data=user_data
            )  
        except Exception as e:  
            logging.error(f"Error in handler: {e}")  
            raise HTTPException(status_code=500, detail="agent-error")  
    
        status_code = result.get("status_code", 200)  
        logging.info(f"Status result = {result}")  
    
        if status_code != 200:  
            error_message = result.get("error", "Unknown error")  
            raise HTTPException(status_code=status_code, detail=error_message)  
    
        # If loading history, return the conversation list  
        if load_history is True:  
            conversation_list = result.get("data", [])  
            return JSONResponse(  
                content=conversation_list,  
                status_code=200  
            )  
    
        # Otherwise, return the chat_id and reply to the client  
        chat_id = result.get("chat_id")  
        new_messages = result.get("reply", [])  
    
        return JSONResponse(  
            content={"chat_id": chat_id, "reply": new_messages},  
            status_code=200  
    )  