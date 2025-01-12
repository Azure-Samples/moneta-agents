import base64
import json
import logging
import os
import requests
import streamlit as st
from dotenv import load_dotenv
from config import (
    INS_AGENTS, 
    BANK_AGENTS, 
    INS_PREDEFINED_QUESTIONS, 
    BANK_PREDEFINED_QUESTIONS,
    AGENT_STYLES,
    GENERAL_STYLES
)
# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Set page config
st.set_page_config(
    page_title="Moneta - Agentic Assistant for Insurance",
    initial_sidebar_state="expanded",
    layout="wide"
)

# Constants
BACKEND_ENDPOINT = os.getenv('BACKEND_ENDPOINT', 'http://localhost:8000')
REDIRECT_URI = os.getenv("WEB_REDIRECT_URI")

st.markdown("""
    <style>
    .big-font {
        font-size:30px !important;
        font-weight: bold;
    }
    .medium-font {
        font-size:20px !important;
    }
    .stButton>button {
        border-radius: 10px;
        height: 3em;
        width: auto;
    }
    .stTextInput>div>div>input {
        color: #4F8BF9;
    }
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
        background-image: url('resources/insurance_logo.png');
        background-repeat: no-repeat;
        background-position: center;
        background-size: contain;
        background-attachment: fixed;
    }
    .login-box {
        background-color: rgba(255, 255, 255, 0.8);
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)


# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "conversations" not in st.session_state:
    st.session_state.conversations = []
if "current_conversation_index" not in st.session_state:
    st.session_state.current_conversation_index = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "display_name" not in st.session_state:
    st.session_state.display_name = None
if "user_input" not in st.session_state:
    st.session_state.user_input = ""
if "last_selected_question" not in st.session_state:
    st.session_state.last_selected_question = None
if "use_case" not in st.session_state:
    st.session_state.use_case = 'fsi_insurance'  # Default use case
if "AGENTS" not in st.session_state:
    st.session_state.AGENTS = INS_AGENTS  # Default agents

def fetch_conversations():
    payload = {
        "user_id": st.session_state.user_id,
        "load_history": True,
        "use_case" : st.session_state.use_case  # Use selected use case
    }

    try:
        response = call_backend(payload)
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching conversations: {e}")
        return []

def extract_assistant_messages(data):
    reply = data.get('reply', [])
    assistant_contents = [message.get('content') for message in reply if message.get('role') == 'assistant']
    return assistant_contents[0] if assistant_contents else 'Could not find any message...'

def select_conversation(index):
    st.session_state.current_conversation_index = index

def display_sidebar():
    with st.sidebar:
        st.title("Moneta Assistant")
        st.write("Empowering Advisors with AI")
        st.write(f"Welcome, {st.session_state.display_name}!")

        use_case_options = ['fsi_insurance', 'fsi_banking']
        selected_use_case = st.selectbox('Select Use Case', use_case_options, index=use_case_options.index(st.session_state.use_case), key='use_case_selectbox')
        if selected_use_case != st.session_state.use_case:
            st.session_state.use_case = selected_use_case
            if st.session_state.use_case == 'fsi_insurance':
                st.session_state.AGENTS = INS_AGENTS
            else:
                st.session_state.AGENTS = BANK_AGENTS
            st.session_state.conversations = fetch_conversations()
            st.session_state.current_conversation_index = None

        # Initialize AGENTS based on use_case
        if st.session_state.use_case == 'fsi_insurance':
            st.session_state.AGENTS = INS_AGENTS
        else:
            st.session_state.AGENTS = BANK_AGENTS

        # Apply styles
        st.markdown(AGENT_STYLES, unsafe_allow_html=True)

        st.markdown("<h4 style='margin-bottom: 0px;'>Agents Online:</h4>", unsafe_allow_html=True)
        # Display agents with tooltips
        agents_container = st.container()
        with agents_container:
            for agent_name, details in st.session_state.AGENTS.items():
                st.markdown(f"""
                    <div class="agent-item">
                        <div class="agent-emoji" style="background-color: {details['color']};">
                            {details['emoji']}
                        </div>
                        <div class="agent-name">
                            {agent_name} Agent
                        </div>
                        <div class="agent-status">
                            ● Online
                        </div>
                        <div class="agent-tooltip">
                            {details['description']}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        st.write("")
        # New Conversation Button
        if st.button("✨ New Conversation ✨", key="new_conv_button", use_container_width=True):
            start_new_conversation()

        # Simplified Conversation History
        st.markdown("<h4 style='margin: 0px 0 0px 0;'>Recent Conversations:</h4>", unsafe_allow_html=True)

        for idx, conv_dict in enumerate(st.session_state.conversations):
            messages = conv_dict.get('messages', [])
            first_user_message = next((msg['content'] for msg in messages if msg['role'] == 'user'), "New Conversation")
            title = (first_user_message[:43] + '...') if len(first_user_message) > 43 else first_user_message
            message_count = len(messages)

            button_text = f"{title}\n\n({0 if message_count == 0 else message_count-1} messages)"
            if st.button(button_text, key=f'conv_{idx}', use_container_width=True):
                select_conversation(idx)

        st.write("---")
        if st.button("🚪 Logout", use_container_width=True):
            logout()

def display_online_agents():
    st.markdown(
        """
        <style>
        .agent-indicator {
            display: inline-block;
            margin: 0 10px;
            text-align: center;
        }
        .agent-circle {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            color: white;
            margin-bottom: 5px;
        }
        .agent-name {
            font-size: 14px;
        }
        .checkmark {
            font-size: 20px;
            color: #4CAF50;
            margin-left: 5px;
            font-weight: bold;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def display_chat():
    display_online_agents()

    if st.session_state.current_conversation_index is None:
        st.write("Please start a new conversation or select an existing one from the sidebar.")
        return

    question_options = []
    # Get the current conversation
    conversation_dict = st.session_state.conversations[st.session_state.current_conversation_index]
    if 'messages' not in conversation_dict:
        conversation_dict['messages'] = []

    messages = conversation_dict['messages']

    # Display predefined questions based on use case
    predefined_questions = BANK_PREDEFINED_QUESTIONS if st.session_state.use_case == 'fsi_banking' else INS_PREDEFINED_QUESTIONS
    question_options = ["Select a predefined question or type your own below"] + predefined_questions
    selected_question = st.selectbox("", question_options, key="question_selectbox")

    # Handle predefined question selection
    if selected_question != "Select a predefined question or type your own below":
        if 'last_selected_question' not in st.session_state or st.session_state.last_selected_question != selected_question:
            st.session_state.last_selected_question = selected_question
            messages.append({'role': 'user', 'content': selected_question})
            with st.spinner('Moneta agents are collaborating to find the best answer...'):
                assistant_responses = send_message_to_backend(selected_question, conversation_dict)
                if isinstance(assistant_responses, list):
                    messages.extend(assistant_responses)
                else:
                    messages.append(assistant_responses)
            st.rerun()

    # Display message history
    for message in messages:
        # Skip messages with empty content
        if not message.get('content'):
            continue

        if message['role'] == 'user':
            with st.chat_message(message['role']):
                st.write(message['content'])
        else:
            if 'name' in message:
                agent_name = message.get('name', '')
                agent_info = st.session_state.AGENTS.get(agent_name)
                if agent_info:
                    with st.chat_message(message['role'], avatar=agent_info['emoji']):
                        st.markdown(
                            f"""
                            <div style='border-left: 5px solid {agent_info['color']}; padding-left: 10px;'>
                                <strong>{agent_name} Agent:</strong> 
                                <div>{message['content']}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    # Handle the case where the agent is not in AGENTS
                    with st.chat_message(message['role']):
                        st.write(f"{agent_name}: {message['content']}")

    # Handle user input
    user_input = st.chat_input("Ask Moneta anything...")
    if user_input:
        messages.append({'role': 'user', 'content': user_input})
        with st.spinner('Moneta agents are collaborating to find the best answer...'):
            assistant_responses = send_message_to_backend(user_input, conversation_dict)
            if isinstance(assistant_responses, list):
                messages.extend(assistant_responses)
            else:
                messages.append(assistant_responses)
        st.rerun()

def send_message_to_backend(user_input, conversation_dict):
    payload = {
        "user_id": st.session_state.user_id,
        "message": user_input,
        "use_case": st.session_state.use_case
    }
    if conversation_dict.get('name') != 'New Conversation':
        payload["chat_id"] = conversation_dict.get('name')

    try:
        response = call_backend(payload)
        assistant_response = response.json()
        st.session_state.conversations[st.session_state.current_conversation_index]['name'] = assistant_response['chat_id']

        # Extract all assistant messages from the reply and filter out empty messages
        reply = assistant_response.get('reply', [])
        assistant_messages = [
            message for message in reply 
            if message['role'] == 'assistant' and message.get('content')
        ]

        # If no valid assistant messages found, return a default message
        if not assistant_messages:
            return {"role": "assistant", "name": "System", "content": "Sorry, I cannot help you with that."}

        # Return all non-empty assistant messages
        return assistant_messages

    except requests.exceptions.RequestException as e:
        st.error(f"Error: {e}")
        logging.error(e, exc_info=True)
        return {"role": "assistant", "name": "System", "content": "Sorry, an error occurred while processing your request."}

def call_backend(payload):
    """
    Call the backend API with the given payload. Raises and exception if HTTP response code is not 200.
    """
    url = f'{BACKEND_ENDPOINT}/http_trigger'
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response

def start_new_conversation():
    st.session_state.conversations.append({
        'messages': [],
        'name': 'New Conversation'
    })
    st.session_state.current_conversation_index = len(st.session_state.conversations) - 1
    st.session_state.last_selected_question = "Select a predefined question or type your own below"

    # reset choice of dropdown
    st.session_state['question_selectbox'] = 'Select a predefined question or type your own below'


def main():
    # Apply general styles
    st.markdown(GENERAL_STYLES, unsafe_allow_html=True)

    st.session_state.user_id = st.context.headers.get('x-ms-client-principal-id', "default_user_id")
    principal = st.context.headers.get('x-ms-client-principal')
    if principal:
        principal = json.loads(base64.b64decode(principal).decode('utf-8'))
        claims = principal.get("claims", [])
        st.session_state.display_name = next((claim["val"] for claim in claims if claim["typ"] == "name"), "Default User")
    else:
        st.session_state.display_name = "Default User"
    
    # Initialize AGENTS based on use_case
    if st.session_state.use_case == 'fsi_insurance':
        st.session_state.AGENTS = INS_AGENTS
    else:
        st.session_state.AGENTS = BANK_AGENTS

    if not st.session_state.conversations:
        st.session_state.conversations = fetch_conversations()

    display_sidebar()
    display_chat()

if __name__ == "__main__":
    main()
