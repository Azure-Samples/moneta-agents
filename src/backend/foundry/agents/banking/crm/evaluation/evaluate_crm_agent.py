"""
CRM Agent Cloud Evaluation - Microsoft Foundry

This module provides cloud-based evaluation for the CRM agent using
Microsoft Foundry's evaluation framework.

The evaluation tests the CRM agent's ability to:
1. Correctly identify and use client data
2. Provide relevant responses based on CRM queries
3. Handle edge cases appropriately

Usage:
    python evaluate_crm_agent.py
"""

import os
import json
import time
import asyncio
from datetime import datetime
from pathlib import Path
from pprint import pprint
from typing import Optional

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import DatasetVersion

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent.parent.parent / ".env")


def get_project_endpoint() -> str:
    """Get the Foundry project endpoint from environment."""
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT") or os.environ.get("PROJECT_ENDPOINT")
    if not endpoint:
        raise ValueError(
            "AZURE_AI_PROJECT_ENDPOINT or PROJECT_ENDPOINT environment variable is required"
        )
    return endpoint


def get_model_deployment_name() -> str:
    """Get the model deployment name from environment."""
    return os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4.1-mini")


def create_evaluation_dataset() -> list[dict]:
    """
    Create a test dataset for CRM agent evaluation.
    
    Returns a list of test cases with:
    - query: The user's input question
    - context: Additional context for evaluation
    - ground_truth: Expected correct answer elements
    - response: (Will be filled by agent or left for agent-target evaluation)
    """
    # Load actual client data for ground truth comparison
    client_data_path = Path(__file__).parent.parent / "client_sample.json"
    with open(client_data_path, 'r') as f:
        client_data = json.load(f)
    
    test_cases = [
        {
            "query": "What is the risk profile for client Pete Mitchell?",
            "context": "CRM query about client investment profile",
            "ground_truth": f"The risk profile is {client_data['investmentProfile']['riskProfile']}",
            "expected_function": "load_from_crm_by_client_fullname",
        },
        {
            "query": "Show me the portfolio performance for client ID 123456",
            "context": "CRM query about portfolio performance metrics",
            "ground_truth": f"YTD performance: {client_data['portfolio']['performanceYTD']}, Since inception: {client_data['portfolio']['performanceSinceInception']}",
            "expected_function": "load_from_crm_by_client_id",
        },
        {
            "query": "What are the contact details for Pete Mitchell?",
            "context": "CRM query about client contact information",
            "ground_truth": f"Email: {client_data['contactDetails']['email']}, Phone: {client_data['contactDetails']['phone']}",
            "expected_function": "load_from_crm_by_client_fullname",
        },
        {
            "query": "What is the investment objective for client 123456?",
            "context": "CRM query about investment goals",
            "ground_truth": f"Investment objective: {client_data['investmentProfile']['investmentObjectives']}",
            "expected_function": "load_from_crm_by_client_id",
        },
        {
            "query": "Tell me about the net income for Pete Mitchell",
            "context": "CRM query about financial information",
            "ground_truth": f"Net income: ${client_data['financialInformation']['netIncome']}",
            "expected_function": "load_from_crm_by_client_fullname",
        },
        # Edge case: No client identifier provided
        {
            "query": "What is the portfolio performance?",
            "context": "CRM query without client identifier - should not provide answer",
            "ground_truth": "Agent should not provide an answer without client ID or name",
            "expected_function": None,
        },
        # Edge case: Non-existent client
        {
            "query": "Show me the portfolio for client John Doe",
            "context": "CRM query for non-existent client",
            "ground_truth": "Client not found in CRM",
            "expected_function": "load_from_crm_by_client_fullname",
        },
    ]
    
    return test_cases


def save_evaluation_dataset(test_cases: list[dict], output_path: Path) -> Path:
    """
    Save test cases to JSONL format for Foundry evaluation.
    
    Args:
        test_cases: List of test case dictionaries
        output_path: Path to save the JSONL file
        
    Returns:
        Path to the saved file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        for case in test_cases:
            # Create evaluation-compatible format
            eval_case = {
                "query": case["query"],
                "context": case["context"],
                "ground_truth": case["ground_truth"],
            }
            # Add response if available (for pre-computed responses)
            if "response" in case:
                eval_case["response"] = case["response"]
            
            f.write(json.dumps(eval_case) + "\n")
    
    print(f"✅ Saved evaluation dataset to: {output_path}")
    return output_path


async def generate_agent_responses(test_cases: list[dict]) -> list[dict]:
    """
    Generate responses from the CRM agent for each test case.
    
    This runs the actual CRM agent to get responses, which will then
    be evaluated.
    
    Args:
        test_cases: List of test cases with queries
        
    Returns:
        Test cases with agent responses added
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from crm_agent import create_crm_agent, chat_with_crm_agent
    from agent_framework.azure import AzureOpenAIChatClient
    from azure.identity.aio import AzureCliCredential
    
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "aga-gpt-4.1-mini")
    
    async with AzureCliCredential() as credential:
        chat_client = AzureOpenAIChatClient(
            endpoint=endpoint,
            deployment_name=deployment_name,
            credential=credential
        )
        
        agent = await create_crm_agent(chat_client)
        
        for i, case in enumerate(test_cases):
            print(f"  Generating response for test case {i+1}/{len(test_cases)}...")
            try:
                response = await chat_with_crm_agent(agent, case["query"])
                case["response"] = response
            except Exception as e:
                case["response"] = f"Error: {str(e)}"
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(1)
    
    return test_cases


def run_cloud_evaluation(
    dataset_path: Path,
    eval_name: str = "crm-agent-evaluation",
    dataset_name: Optional[str] = None,
) -> dict:
    """
    Run cloud evaluation on the CRM agent using Foundry.
    
    Args:
        dataset_path: Path to the JSONL evaluation dataset
        eval_name: Name for the evaluation run
        dataset_name: Optional name for the dataset in Foundry
        
    Returns:
        Evaluation results
    """
    endpoint = get_project_endpoint()
    model_deployment = get_model_deployment_name()
    
    if dataset_name is None:
        dataset_name = f"crm-eval-{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"\n🚀 Starting Cloud Evaluation")
    print(f"   Endpoint: {endpoint}")
    print(f"   Model: {model_deployment}")
    print(f"   Dataset: {dataset_name}")
    print()
    
    with DefaultAzureCredential() as credential:
        with AIProjectClient(endpoint=endpoint, credential=credential) as project_client:
            # 1. Upload the evaluation dataset
            print("📤 Uploading evaluation dataset...")
            dataset: DatasetVersion = project_client.datasets.upload_file(
                name=dataset_name,
                version="1",
                file_path=str(dataset_path),
            )
            print(f"   Dataset ID: {dataset.id}")
            
            # 2. Get OpenAI client for evaluation API
            print("🔧 Creating OpenAI client...")
            openai_client = project_client.get_openai_client()
            
            # 3. Define evaluation schema and criteria
            data_source_config = {
                "type": "custom",
                "item_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "response": {"type": "string"},
                        "context": {"type": "string"},
                        "ground_truth": {"type": "string"},
                    },
                    "required": ["query", "response"],
                },
                "include_sample_schema": True,
            }
            
            # Define testing criteria using built-in evaluators
            testing_criteria = [
                {
                    "type": "azure_ai_evaluator",
                    "name": "coherence",
                    "evaluator_name": "builtin.coherence",
                    "data_mapping": {
                        "query": "{{item.query}}",
                        "response": "{{item.response}}",
                    },
                    "initialization_parameters": {
                        "deployment_name": model_deployment
                    },
                },
                {
                    "type": "azure_ai_evaluator",
                    "name": "relevance",
                    "evaluator_name": "builtin.relevance",
                    "data_mapping": {
                        "query": "{{item.query}}",
                        "response": "{{item.response}}",
                        "context": "{{item.context}}",
                    },
                    "initialization_parameters": {
                        "deployment_name": model_deployment
                    },
                },
                {
                    "type": "azure_ai_evaluator",
                    "name": "fluency",
                    "evaluator_name": "builtin.fluency",
                    "data_mapping": {
                        "query": "{{item.query}}",
                        "response": "{{item.response}}",
                    },
                    "initialization_parameters": {
                        "deployment_name": model_deployment
                    },
                },
                {
                    "type": "azure_ai_evaluator",
                    "name": "groundedness",
                    "evaluator_name": "builtin.groundedness",
                    "data_mapping": {
                        "query": "{{item.query}}",
                        "response": "{{item.response}}",
                        "context": "{{item.ground_truth}}",
                    },
                    "initialization_parameters": {
                        "deployment_name": model_deployment
                    },
                },
            ]
            
            # 4. Create the evaluation group
            print("📊 Creating evaluation group...")
            eval_object = openai_client.evals.create(
                name=eval_name,
                data_source_config=data_source_config,
                testing_criteria=testing_criteria,
            )
            print(f"   Eval ID: {eval_object.id}")
            
            # 5. Create and run the evaluation
            print("▶️  Starting evaluation run...")
            from openai.types.evals.create_eval_jsonl_run_data_source_param import (
                CreateEvalJSONLRunDataSourceParam,
                SourceFileID,
            )
            
            eval_run = openai_client.evals.runs.create(
                eval_id=eval_object.id,
                name=f"{eval_name}-run-{datetime.utcnow().strftime('%H%M%S')}",
                metadata={
                    "agent": "bank-crm-agent",
                    "type": "cloud-evaluation",
                    "timestamp": datetime.utcnow().isoformat(),
                },
                data_source=CreateEvalJSONLRunDataSourceParam(
                    type="jsonl",
                    source=SourceFileID(
                        type="file_id",
                        id=dataset.id if dataset.id else "",
                    ),
                ),
            )
            print(f"   Run ID: {eval_run.id}")
            
            # 6. Poll for completion
            print("\n⏳ Waiting for evaluation to complete...")
            while True:
                run = openai_client.evals.runs.retrieve(
                    run_id=eval_run.id,
                    eval_id=eval_object.id,
                )
                print(f"   Status: {run.status}")
                
                if run.status in ("completed", "failed"):
                    break
                
                time.sleep(5)
            
            # 7. Get and display results
            if run.status == "completed":
                print("\n✅ Evaluation completed!")
                print(f"📈 Report URL: {run.report_url}")
                
                # Get output items
                output_items = list(
                    openai_client.evals.runs.output_items.list(
                        run_id=run.id,
                        eval_id=eval_object.id,
                    )
                )
                
                print(f"\n📋 Results ({len(output_items)} items):")
                for item in output_items:
                    print("-" * 50)
                    pprint(item)
                
                return {
                    "status": "completed",
                    "eval_id": eval_object.id,
                    "run_id": run.id,
                    "report_url": run.report_url,
                    "output_items": output_items,
                }
            else:
                print(f"\n❌ Evaluation failed: {run.status}")
                return {
                    "status": "failed",
                    "eval_id": eval_object.id,
                    "run_id": run.id,
                    "error": str(run),
                }


async def main():
    """
    Main function to run CRM agent evaluation.
    """
    print("=" * 60)
    print("CRM Agent Cloud Evaluation")
    print("=" * 60)
    
    # Create evaluation directory
    eval_dir = Path(__file__).parent
    eval_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Create test dataset
    print("\n📝 Creating evaluation test cases...")
    test_cases = create_evaluation_dataset()
    print(f"   Created {len(test_cases)} test cases")
    
    # Step 2: Generate agent responses
    print("\n🤖 Generating CRM agent responses...")
    test_cases_with_responses = await generate_agent_responses(test_cases)
    
    # Step 3: Save to JSONL
    dataset_path = eval_dir / "crm_evaluation_data.jsonl"
    save_evaluation_dataset(test_cases_with_responses, dataset_path)
    
    # Step 4: Run cloud evaluation
    print("\n☁️  Running cloud evaluation in Foundry...")
    results = run_cloud_evaluation(
        dataset_path=dataset_path,
        eval_name="crm-agent-quality-eval",
    )
    
    # Step 5: Summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Status: {results['status']}")
    if results.get('report_url'):
        print(f"Report: {results['report_url']}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
