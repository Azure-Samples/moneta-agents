import azure.functions as func
import json
import logging
import os
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from conversation_store import ConversationStore
from handlers import VanillaAgenticHandler
from sk.sk_handler import SemanticKernelHandler

import asyncio
load_dotenv()

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="http_trigger")
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Empowering RMs - HTTP trigger function processed a request.')

    try:
        req_body = req.get_json()
    except ValueError as e:
        logging.error(f"Invalid JSON: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON format"}),
            status_code=400,
            mimetype="application/json"
        )

    user_id = req_body.get('user_id')
    chat_id = req_body.get('chat_id')  # None if starting a new chat
    user_message = req_body.get('message')
    load_history = req_body.get('load_history')
    usecase_type = req_body.get('use_case')

    if not user_id:
        return func.HttpResponse(
            json.dumps({"error": "<user_id> is required!"}),
            status_code=400,
            mimetype="application/json"
        )

    if load_history is not True and not user_message:
        return func.HttpResponse(
            json.dumps({"error": "<message> is required when not loading history!"}),
            status_code=400,
            mimetype="application/json"
        )

    if not usecase_type:
        return func.HttpResponse(
            json.dumps({"error": "<usecase_type> is required!"}),
            status_code=400,
            mimetype="application/json"
        )

    # A helper class that stores and retrieves messages by conversation from an Azure Cosmos DB
    key = DefaultAzureCredential()

    # Select use case container
    if 'fsi_insurance' == usecase_type:
        container_name = os.getenv("COSMOSDB_CONTAINER_FSI_INS_USER_NAME")
    elif 'fsi_banking' == usecase_type:
        container_name = os.getenv("COSMOSDB_CONTAINER_FSI_BANK_USER_NAME")
    else:
        return func.HttpResponse(
            json.dumps({"error": "Use case not recognized/not implemented..."}),
            status_code=400,
            mimetype="application/json"
        )

    db = ConversationStore(
        url=os.getenv("COSMOSDB_ENDPOINT"),
        key=key,
        database_name=os.getenv("COSMOSDB_DATABASE_NAME"),
        container_name=container_name
    )

    if not db.read_user_info(user_id):
        user_data = {'chat_histories': {}}
        db.create_user(user_id, user_data)

    user_data = db.read_user_info(user_id)

    # Decide which handler to use based on environment variable
    handler_type = 'semantickernel'  # TODO via env var -> Expected values: "vanilla", "semantickernel"

    if handler_type == "vanilla":
        handler = VanillaAgenticHandler(db)
    elif handler_type == "semantickernel":
        handler = SemanticKernelHandler(db)
    else:
        return func.HttpResponse(
            json.dumps({"error": "Invalid HANDLER_TYPE"}),
            status_code=400,
            mimetype="application/json"
        )

    try:
        result = asyncio.run(handler.handle_request(
            user_id=user_id,
            chat_id=chat_id,
            user_message=user_message,
            load_history=load_history,
            usecase_type=usecase_type,
            user_data=user_data
        ))
    except Exception as e:
        logging.error(f"Error in handler: {e}")
        return func.HttpResponse(
            json.dumps({"error": "agent-error"}),
            status_code=500,
            mimetype="application/json"
        )
        
    status_code = result.get("status_code", 200)
    print(f"status result = {result}")
    if status_code != 200:
        error_message = result.get("error", "Unknown error")
        return func.HttpResponse(
            json.dumps({"error": error_message}),
            status_code=status_code,
            mimetype="application/json"
        )

    # If loading history
    if load_history is True:
        conversation_list = result.get("data", [])
        #logging.info(f"conv history= {conversation_list}")
        return func.HttpResponse(
            json.dumps(conversation_list),
            status_code=200,
            mimetype="application/json"
        )

    # Otherwise, return the chat_id and reply to the client
    chat_id = result.get("chat_id")
    new_messages = result.get("reply", [])

    return func.HttpResponse(
        json.dumps({"chat_id": chat_id, "reply": new_messages}),
        status_code=200,
        mimetype="application/json"
    )