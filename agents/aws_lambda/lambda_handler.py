# lambda_handler.py
import json
import os
import boto3
import time
import random
import uuid
from typing import Dict, Any, List
from botocore.config import Config

# Configure boto3 client with retry settings
config = Config(
    retries={
        'max_attempts': 10,  # Default is 3
        'mode': 'adaptive'   # Automatically adjusts retry rate based on response
    }
)

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', config=config)
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Configuration
MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
CONVERSATION_TABLE = os.environ.get('CONVERSATION_TABLE', 'ai_agent_conversations')
MAX_REQUESTS_PER_MINUTE = int(os.environ.get('MAX_REQUESTS_PER_MINUTE', '50'))

# Global request tracking
request_timestamps: List[float] = []

def wait_for_capacity():
    """Implements rate limiting based on requests per minute with improved backoff."""
    global request_timestamps
    
    # Remove timestamps older than 1 minute
    current_time = time.time()
    request_timestamps = [ts for ts in request_timestamps 
                         if current_time - ts < 60]
    
    # If at capacity, wait until we have room
    if len(request_timestamps) >= MAX_REQUESTS_PER_MINUTE:
        oldest_timestamp = min(request_timestamps)
        # Calculate sleep time with jitter for better distribution
        base_sleep_time = 60 - (current_time - oldest_timestamp)
        jitter = random.uniform(0.1, 1.0)  # Add jitter
        sleep_time = base_sleep_time + jitter
        
        print(f"Rate limit reached. Waiting for {sleep_time:.2f} seconds before next request.")
        
        if sleep_time > 0:
            time.sleep(sleep_time)
            
        # Recursive call to ensure we're under the limit after waiting
        wait_for_capacity()

def invoke_bedrock(prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
    """Invoke Bedrock model with improved throttling management and exponential backoff."""
    global request_timestamps
    
    # Wait if we're at capacity
    wait_for_capacity()
    
    # Prepare request based on model type
    if "anthropic.claude" in MODEL_ID:
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
    elif "amazon.titan" in MODEL_ID:
        request_body = {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": max_tokens,
                "temperature": temperature,
            }
        }
    else:
        raise ValueError(f"Unsupported model: {MODEL_ID}")
    
    # Track this request
    request_timestamps.append(time.time())
    
    # Implement retry with exponential backoff
    max_retries = 5
    base_delay = 1  # Start with 1 second
    
    for attempt in range(max_retries):
        try:
            response = bedrock_runtime.invoke_model(
                modelId=MODEL_ID,
                body=json.dumps(request_body)
            )
            response_body = json.loads(response['body'].read())
            
            # Extract response based on model type
            if "anthropic.claude" in MODEL_ID:
                return response_body['content'][0]['text']
            elif "amazon.titan" in MODEL_ID:
                return response_body['results'][0]['outputText']
            else:
                return str(response_body)
                
        except bedrock_runtime.exceptions.ThrottlingException as e:
            # Calculate exponential backoff with jitter
            if attempt < max_retries - 1:  # Don't sleep on the last attempt
                retry_delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"Throttling exception on attempt {attempt+1}/{max_retries}. Retrying in {retry_delay:.2f} seconds.")
                time.sleep(retry_delay)
            else:
                print(f"Throttling exception: Maximum retries ({max_retries}) exceeded.")
                raise
            
        except Exception as e:
            print(f"Error invoking Bedrock model on attempt {attempt+1}: {e}")
            raise
    
    # This should not be reached due to the raise in the last exception block
    raise Exception("Maximum retries exceeded for Bedrock invocation")

def save_conversation(conversation_id: str, user_input: str, ai_response: str):
    """Save conversation to DynamoDB."""
    table = dynamodb.Table(CONVERSATION_TABLE)
    timestamp = int(time.time() * 1000)  # milliseconds
    
    try:
        table.put_item(
            Item={
                'conversation_id': conversation_id,
                'timestamp': timestamp,
                'user_input': user_input,
                'ai_response': ai_response
            }
        )
        return True
    except Exception as e:
        print(f"Error saving to DynamoDB: {e}")
        return False

def get_conversation_history(conversation_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve conversation history from DynamoDB."""
    table = dynamodb.Table(CONVERSATION_TABLE)
    
    try:
        response = table.query(
            KeyConditionExpression='conversation_id = :cid',
            ExpressionAttributeValues={':cid': conversation_id},
            ScanIndexForward=False,  # descending order (newest first)
            Limit=limit
        )
        return response.get('Items', [])
    except Exception as e:
        print(f"Error retrieving from DynamoDB: {e}")
        return []

def format_conversation_history(history: List[Dict[str, Any]]) -> str:
    """Format conversation history for the AI prompt."""
    # Reverse to get chronological order
    history = sorted(history, key=lambda x: x['timestamp'])
    
    formatted = ""
    for item in history:
        formatted += f"Human: {item['user_input']}\n"
        formatted += f"AI: {item['ai_response']}\n\n"
    
    return formatted

# Import API helper
from api_helper import format_response, parse_event, validate_request, handle_options_request, error_response

def lambda_handler(event, context):
    """AWS Lambda handler function with improved error handling and API integration."""
    # Handle OPTIONS request for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return handle_options_request()
    
    try:
        # Parse request body
        body = parse_event(event)
        
        # Validate required fields
        validation = validate_request(body, ['input'])
        if not validation['valid']:
            return error_response(400, validation['error'])
        
        # Extract parameters with defaults
        user_input = body.get('input', '')
        conversation_id = body.get('conversation_id', str(uuid.uuid4()))
        include_history = body.get('include_history', True)
        max_tokens = int(body.get('max_tokens', 1000))
        temperature = float(body.get('temperature', 0.7))
        
        # Log request information
        print(f"Processing request: conversation_id={conversation_id}, include_history={include_history}")
        
        # Get conversation history if needed
        prompt = user_input
        if include_history:
            history = get_conversation_history(conversation_id)
            if history:
                conversation_context = format_conversation_history(history)
                prompt = f"{conversation_context}\nHuman: {user_input}\nAI:"
        
        # Generate response using Bedrock
        ai_response = invoke_bedrock(prompt, max_tokens, temperature)
        
        # Save conversation
        save_conversation(conversation_id, user_input, ai_response)
        
        # Return successful response
        return format_response(200, {
            'success': True,
            'conversation_id': conversation_id,
            'response': ai_response
        })
        
    except ValueError as e:
        # Handle validation errors
        print(f"Validation error: {str(e)}")
        return error_response(400, str(e))
        
    except Exception as e:
        # Handle unexpected errors
         print(f"Error processing request: {str(e)}")
         return error_response(500, "Internal server error")