# dynamodb_helper.py
import boto3
import time
import json
import os
from typing import Dict, Any, List, Optional
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

# Initialize DynamoDB resources
dynamodb = boto3.resource('dynamodb')
CONVERSATION_TABLE = os.environ.get('CONVERSATION_TABLE', 'ai_agent_conversations')

def save_conversation(conversation_id: str, user_input: str, ai_response: str, 
                     metadata: Optional[Dict[str, Any]] = None, ttl: Optional[int] = None) -> Dict[str, Any]:
    """Save conversation to DynamoDB.
    
    Args:
        conversation_id: Unique identifier for the conversation
        user_input: User's message
        ai_response: AI's response
        metadata: Additional metadata to store
        ttl: Time-to-live in seconds from now
        
    Returns:
        Dict with save status
    """
    table = dynamodb.Table(CONVERSATION_TABLE)
    timestamp = int(time.time() * 1000)  # milliseconds
    
    item = {
        'conversation_id': conversation_id,
        'timestamp': timestamp,
        'user_input': user_input,
        'ai_response': ai_response
    }
    
    # Add optional fields
    if metadata:
        item['metadata'] = metadata
    
    if ttl:
        item['ttl'] = int(time.time()) + ttl
    
    try:
        table.put_item(Item=item)
        return {
            'success': True,
            'conversation_id': conversation_id,
            'timestamp': timestamp
        }
    except ClientError as e:
        return {
            'success': False,
            'error': str(e)
        }

def get_conversation_history(conversation_id: str, limit: int = 10, 
                            start_time: Optional[int] = None) -> Dict[str, Any]:
    """Retrieve conversation history from DynamoDB.
    
    Args:
        conversation_id: Unique identifier for the conversation
        limit: Maximum number of messages to retrieve
        start_time: Optional timestamp to start from (milliseconds)
        
    Returns:
        Dict with retrieval status and conversation items
    """
    table = dynamodb.Table(CONVERSATION_TABLE)
    
    try:
        # Build query parameters
        query_params = {
            'KeyConditionExpression': Key('conversation_id').eq(conversation_id),
            'ScanIndexForward': False,  # descending order (newest first)
            'Limit': limit
        }
        
        # Add start_time if provided
        if start_time:
            query_params['KeyConditionExpression'] = Key('conversation_id').eq(conversation_id) & \
                                                    Key('timestamp').lt(start_time)
        
        response = table.query(**query_params)
        
        return {
            'success': True,
            'items': response.get('Items', []),
            'count': len(response.get('Items', [])),
            'last_evaluated_key': response.get('LastEvaluatedKey')
        }
    except ClientError as e:
        return {
            'success': False,
            'error': str(e)
        }

def delete_conversation(conversation_id: str) -> Dict[str, Any]:
    """Delete all messages in a conversation.
    
    Args:
        conversation_id: Unique identifier for the conversation
        
    Returns:
        Dict with deletion status
    """
    table = dynamodb.Table(CONVERSATION_TABLE)
    
    try:
        # First, query all items with this conversation_id
        response = table.query(
            KeyConditionExpression=Key('conversation_id').eq(conversation_id),
            ProjectionExpression='conversation_id, #ts',
            ExpressionAttributeNames={'#ts': 'timestamp'}
        )
        
        # Batch delete all items
        with table.batch_writer() as batch:
            for item in response.get('Items', []):
                batch.delete_item(
                    Key={
                        'conversation_id': item['conversation_id'],
                        'timestamp': item['timestamp']
                    }
                )
        
        return {
            'success': True,
            'conversation_id': conversation_id,
            'deleted_count': len(response.get('Items', []))
        }
    except ClientError as e:
        return {
            'success': False,
            'error': str(e)
        }

def list_conversations(limit: int = 100) -> Dict[str, Any]:
    """List unique conversation IDs.
    
    Args:
        limit: Maximum number of conversations to retrieve
        
    Returns:
        Dict with listing status and conversation IDs
    """
    table = dynamodb.Table(CONVERSATION_TABLE)
    
    try:
        # Use scan with a filter to get unique conversation_ids
        response = table.scan(
            Select='SPECIFIC_ATTRIBUTES',
            ProjectionExpression='conversation_id',
            Limit=limit
        )
        
        # Extract unique conversation IDs
        conversation_ids = set()
        for item in response.get('Items', []):
            conversation_ids.add(item['conversation_id'])
        
        return {
            'success': True,
            'conversation_ids': list(conversation_ids),
            'count': len(conversation_ids)
        }
    except ClientError as e:
        return {
            'success': False,
            'error': str(e)
        }