# aws_bedrock.py
import boto3
import time
import random
import json
from langchain.tools import tool
from botocore.config import Config
from typing import Dict, Any, Optional, List

# Configure boto3 client with retry settings
config = Config(
    retries={
        'max_attempts': 10,  # Default is 3
        'mode': 'adaptive'   # Automatically adjusts retry rate based on response
    }
)

class BedrockClient:
    """AWS Bedrock client with built-in throttling management."""
    
    def __init__(self, model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0", region: str = "us-east-1"):
        """Initialize Bedrock client with specified model and region.
        
        Args:
            model_id: The Bedrock model ID to use
            region: AWS region where Bedrock is available
        """
        self.model_id = model_id
        self.region = region
        self.client = boto3.client('bedrock-runtime', region_name=region, config=config)
        self.request_timestamps: List[float] = []
        self.max_requests_per_minute = 50  # Default limit, can be adjusted
        
    def _wait_for_capacity(self):
        """Implements rate limiting based on requests per minute."""
        # Remove timestamps older than 1 minute
        current_time = time.time()
        self.request_timestamps = [ts for ts in self.request_timestamps 
                                 if current_time - ts < 60]
        
        # If at capacity, wait until we have room
        if len(self.request_timestamps) >= self.max_requests_per_minute:
            oldest_timestamp = min(self.request_timestamps)
            sleep_time = 60 - (current_time - oldest_timestamp) + random.uniform(0.1, 1.0)  # Add jitter
            if sleep_time > 0:
                time.sleep(sleep_time)
            # Clean up timestamps again after waiting
            self.request_timestamps = [ts for ts in self.request_timestamps 
                                     if time.time() - ts < 60]
    
    def invoke_model(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """Invoke Bedrock model with throttling management.
        
        Args:
            prompt: The text prompt to send to the model
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0 to 1.0)
            
        Returns:
            Generated text response
        """
        # Wait if we're at capacity
        self._wait_for_capacity()
        
        # Prepare request based on model type
        if "anthropic.claude" in self.model_id:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
        elif "amazon.titan" in self.model_id:
            request_body = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": max_tokens,
                    "temperature": temperature,
                }
            }
        else:
            raise ValueError(f"Unsupported model: {self.model_id}")
        
        # Track this request
        self.request_timestamps.append(time.time())
        
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            response_body = json.loads(response['body'].read())
            
            # Extract response based on model type
            if "anthropic.claude" in self.model_id:
                return response_body['content'][0]['text']
            elif "amazon.titan" in self.model_id:
                return response_body['results'][0]['outputText']
            else:
                return str(response_body)
                
        except self.client.exceptions.ThrottlingException as e:
            # Add the timestamp anyway to prevent retry storms
            print(f"Throttling exception: {e}")
            # Implement exponential backoff
            retry_delay = random.uniform(1, 3)  # Start with 1-3 seconds
            time.sleep(retry_delay)
            # Recursive retry with exponential backoff
            return self.invoke_model(prompt, max_tokens, temperature)
            
        except Exception as e:
            print(f"Error invoking Bedrock model: {e}")
            raise

# Create a singleton instance for reuse
bedrock = BedrockClient()

@tool("bedrock_generate", return_direct=True)
def bedrock_generate(prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
    """Generate text using AWS Bedrock with built-in throttling management.
    
    Args:
        prompt: The text prompt to send to the model
        max_tokens: Maximum number of tokens to generate
        temperature: Controls randomness (0.0 to 1.0)
        
    Returns:
        Generated text response
    """
    return bedrock.invoke_model(prompt, max_tokens, temperature)