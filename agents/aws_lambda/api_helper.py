# api_helper.py
import json
import logging
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def format_response(status_code: int, body: Dict[str, Any], cors: bool = True) -> Dict[str, Any]:
    """Format API Gateway response with proper headers.
    
    Args:
        status_code: HTTP status code
        body: Response body as dictionary
        cors: Whether to include CORS headers
        
    Returns:
        Formatted API Gateway response
    """
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Add CORS headers if enabled
    if cors:
        headers.update({
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        })
    
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body)
    }

def parse_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Parse and validate API Gateway event.
    
    Args:
        event: API Gateway event
        
    Returns:
        Parsed request body
    """
    try:
        # Handle different event sources
        if 'body' in event:
            if event['body'] is None:
                return {}
            
            # Parse JSON body
            try:
                return json.loads(event['body'])
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in request body: {event['body']}")
                return {}
        elif 'queryStringParameters' in event and event['queryStringParameters']:
            # Handle query string parameters
            return event['queryStringParameters']
        else:
            # Default to empty dict if no recognizable format
            return {}
    except Exception as e:
        logger.error(f"Error parsing event: {str(e)}")
        return {}

def validate_request(body: Dict[str, Any], required_fields: Optional[list] = None) -> Dict[str, Any]:
    """Validate request body against required fields.
    
    Args:
        body: Request body
        required_fields: List of required field names
        
    Returns:
        Dict with validation result
    """
    if required_fields is None:
        return {'valid': True}
    
    missing_fields = [field for field in required_fields if field not in body]
    
    if missing_fields:
        return {
            'valid': False,
            'error': f"Missing required fields: {', '.join(missing_fields)}"
        }
    
    return {'valid': True}

def handle_options_request() -> Dict[str, Any]:
    """Handle OPTIONS request for CORS preflight.
    
    Returns:
        API Gateway response for OPTIONS request
    """
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
            'Access-Control-Max-Age': '86400'
        },
        'body': ''
    }

def error_response(status_code: int, message: str, cors: bool = True) -> Dict[str, Any]:
    """Generate error response.
    
    Args:
        status_code: HTTP status code
        message: Error message
        cors: Whether to include CORS headers
        
    Returns:
        Formatted error response
    """
    return format_response(
        status_code=status_code,
        body={
            'success': False,
            'error': message
        },
        cors=cors
    )