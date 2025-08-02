# AWS Bedrock AI Agent Integration

This project implements an AI agent using AWS services including Bedrock, Lambda, DynamoDB, S3, and API Gateway. The implementation includes robust rate limiting and throttling management to handle API quotas effectively.

## Architecture Overview

![Architecture Diagram](https://mermaid.ink/img/pako:eNqFksFuwjAMhl_F8qkgwYEDh0mTJnHYpE1CahdUNXJJC9GapJlTVMq7L6WFwTRtPtn-_X-2ZXdEaRQiRJnrXJUGnkqjbQlPcAcPMIXH-XQymU_vYQYzWCzg9Xk2nc_gYTKdwOPrYjqZviwXkzuYwTJJYJkkL0kCq9VqtVol8BZiXVkHuXGlLVXVQK6VdpBp7QwUqgRTKetBOdDWoYON0gV8oXPgvEMHtdKlg1xbVIWyJZTKGFDOoYOVKhwo5dCBRlOBRlc6cPvGwVZZB1_ooFSNg2_UDrZo0EGhKgcb1A72qJt_dVvn4IAWvtE5OKLdO3TfOTihPZzRwRkdXNDBFe0PdJWyJXyg-0HnGx380P1c0f1c0P1c0f38ovsJ8T-4RJmhxBCTWpdYhdhXWIbYU1hgGGCfY4A9hgJjP8AY-xwF9gOMsc9RYIw9jjH2OAqMfY4Ce_8AyELKQQ?type=png)

## Features

- **AWS Bedrock Integration**: Utilizes AWS Bedrock for AI model inference with support for Claude and Titan models
- **Rate Limiting**: Implements client-side rate limiting to respect AWS Bedrock quotas
- **Throttling Management**: Handles throttling exceptions with exponential backoff and jitter
- **Conversation History**: Stores conversation history in DynamoDB for context preservation
- **File Storage**: Uses S3 for file uploads and downloads
- **REST API**: Exposes the AI agent functionality through API Gateway

## Rate Limiting and Throttling Management

The implementation includes two levels of protection against rate limits:

1. **Proactive Rate Limiting**: Client-side tracking of request frequency to stay within quota
2. **Reactive Throttling Handling**: Exponential backoff with jitter when throttling occurs

### Proactive Rate Limiting

The `wait_for_capacity()` function implements a token bucket-like algorithm:

```python
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
```

### Reactive Throttling Handling

The `invoke_bedrock()` function implements exponential backoff with jitter when throttling occurs:

```python
# Implement retry with exponential backoff
max_retries = 5
base_delay = 1  # Start with 1 second

for attempt in range(max_retries):
    try:
        # API call...
    except bedrock_runtime.exceptions.ThrottlingException as e:
        # Calculate exponential backoff with jitter
        if attempt < max_retries - 1:  # Don't sleep on the last attempt
            retry_delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            print(f"Throttling exception on attempt {attempt+1}/{max_retries}. Retrying in {retry_delay:.2f} seconds.")
            time.sleep(retry_delay)
        else:
            print(f"Throttling exception: Maximum retries ({max_retries}) exceeded.")
            raise
```

## Deployment

The project includes a CloudFormation template (`template.yaml`) and a deployment script (`deploy.py`) to simplify deployment to AWS.

### Prerequisites

- AWS CLI installed and configured
- Python 3.9 or higher
- Boto3 library installed

### Deployment Steps

1. Clone the repository
2. Run the deployment script:

```bash
python deploy.py --stack-name ai-agent-stack --region us-east-1 --model-id anthropic.claude-3-sonnet-20240229-v1:0 --max-rpm 50
```

Options:
- `--stack-name`: CloudFormation stack name (default: ai-agent-stack)
- `--region`: AWS region to deploy to (default: us-east-1)
- `--model-id`: AWS Bedrock model ID (default: anthropic.claude-3-sonnet-20240229-v1:0)
- `--max-rpm`: Maximum requests per minute to AWS Bedrock (default: 50)
- `--profile`: AWS CLI profile to use (optional)

## Usage

After deployment, you can interact with the AI agent through the API Gateway endpoint:

```bash
curl -X POST https://{api-id}.execute-api.{region}.amazonaws.com/prod/chat \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello, how can you help me?", "conversation_id": "optional-id", "include_history": true}'
```

## Monitoring and Troubleshooting

- **CloudWatch Logs**: Check Lambda function logs for errors and throttling events
- **CloudWatch Metrics**: Monitor API Gateway and Lambda metrics
- **AWS Service Quotas**: Monitor and request increases for Bedrock quotas if needed

## Best Practices

1. **Adjust Rate Limits**: Set `MAX_REQUESTS_PER_MINUTE` based on your AWS Bedrock quota
2. **Use Provisioned Throughput**: For production workloads, consider using Provisioned Throughput
3. **Implement Client-Side Caching**: Cache responses to reduce API calls
4. **Monitor Usage**: Set up CloudWatch alarms for throttling events
5. **Distribute Load**: For high-volume applications, distribute requests across regions