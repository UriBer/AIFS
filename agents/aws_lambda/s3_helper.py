# s3_helper.py
import boto3
import json
import os
from typing import Dict, Any, Optional, BinaryIO
from botocore.exceptions import ClientError

# Initialize S3 client
s3 = boto3.client('s3')
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'ai-agent-storage')

def upload_file(file_obj: BinaryIO, key: str, content_type: Optional[str] = None) -> Dict[str, Any]:
    """Upload a file to S3 bucket.
    
    Args:
        file_obj: File-like object to upload
        key: S3 object key (path)
        content_type: MIME type of the file
        
    Returns:
        Dict with upload status and URL
    """
    try:
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
            
        s3.upload_fileobj(file_obj, BUCKET_NAME, key, ExtraArgs=extra_args)
        
        # Generate URL
        url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{key}"
        
        return {
            'success': True,
            'key': key,
            'url': url
        }
    except ClientError as e:
        return {
            'success': False,
            'error': str(e)
        }

def download_file(key: str) -> Dict[str, Any]:
    """Download a file from S3 bucket.
    
    Args:
        key: S3 object key (path)
        
    Returns:
        Dict with download status and file content
    """
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        return {
            'success': True,
            'content': response['Body'].read(),
            'content_type': response.get('ContentType', 'application/octet-stream'),
            'metadata': response.get('Metadata', {})
        }
    except ClientError as e:
        return {
            'success': False,
            'error': str(e)
        }

def generate_presigned_url(key: str, expiration: int = 3600, operation: str = 'get_object') -> Dict[str, Any]:
    """Generate a presigned URL for S3 operations.
    
    Args:
        key: S3 object key (path)
        expiration: URL expiration time in seconds
        operation: S3 operation ('get_object' or 'put_object')
        
    Returns:
        Dict with URL generation status and URL
    """
    try:
        url = s3.generate_presigned_url(
            ClientMethod=operation,
            Params={
                'Bucket': BUCKET_NAME,
                'Key': key
            },
            ExpiresIn=expiration
        )
        
        return {
            'success': True,
            'url': url,
            'expiration': expiration
        }
    except ClientError as e:
        return {
            'success': False,
            'error': str(e)
        }

def list_files(prefix: str = '', max_items: int = 1000) -> Dict[str, Any]:
    """List files in the S3 bucket with optional prefix.
    
    Args:
        prefix: S3 key prefix for filtering
        max_items: Maximum number of items to return
        
    Returns:
        Dict with listing status and files
    """
    try:
        response = s3.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=prefix,
            MaxKeys=max_items
        )
        
        files = []
        if 'Contents' in response:
            for item in response['Contents']:
                files.append({
                    'key': item['Key'],
                    'size': item['Size'],
                    'last_modified': item['LastModified'].isoformat(),
                    'url': f"https://{BUCKET_NAME}.s3.amazonaws.com/{item['Key']}"
                })
        
        return {
            'success': True,
            'files': files,
            'count': len(files)
        }
    except ClientError as e:
        return {
            'success': False,
            'error': str(e)
        }

def delete_file(key: str) -> Dict[str, Any]:
    """Delete a file from S3 bucket.
    
    Args:
        key: S3 object key (path)
        
    Returns:
        Dict with deletion status
    """
    try:
        s3.delete_object(Bucket=BUCKET_NAME, Key=key)
        return {
            'success': True,
            'key': key
        }
    except ClientError as e:
        return {
            'success': False,
            'error': str(e)
        }