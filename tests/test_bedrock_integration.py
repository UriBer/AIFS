import unittest
import sys
import os
import time
import json
from unittest.mock import patch, MagicMock

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modules to test
from agents.aws_lambda.lambda_handler import wait_for_capacity, invoke_bedrock

class TestBedrockIntegration(unittest.TestCase):
    """Test AWS Bedrock integration with rate limiting and throttling management."""
    
    @patch('agents.aws_lambda.lambda_handler.request_timestamps')
    @patch('agents.aws_lambda.lambda_handler.time.time')
    @patch('agents.aws_lambda.lambda_handler.time.sleep')
    def test_wait_for_capacity_under_limit(self, mock_sleep, mock_time, mock_timestamps):
        """Test wait_for_capacity when under the rate limit."""
        # Setup
        mock_time.return_value = 1000.0
        mock_timestamps[:] = [999.0, 998.0, 997.0]  # 3 recent requests
        
        # Execute
        wait_for_capacity()
        
        # Assert
        mock_sleep.assert_not_called()  # Should not sleep when under limit
        self.assertEqual(len(mock_timestamps), 4)  # Should add current timestamp
        self.assertEqual(mock_timestamps[-1], 1000.0)  # Should add current time
    
    @patch('agents.aws_lambda.lambda_handler.MAX_REQUESTS_PER_MINUTE', 5)
    @patch('agents.aws_lambda.lambda_handler.request_timestamps')
    @patch('agents.aws_lambda.lambda_handler.time.time')
    @patch('agents.aws_lambda.lambda_handler.time.sleep')
    @patch('agents.aws_lambda.lambda_handler.random.uniform')
    def test_wait_for_capacity_at_limit(self, mock_random, mock_sleep, mock_time, mock_timestamps):
        """Test wait_for_capacity when at the rate limit."""
        # Setup
        mock_time.side_effect = [1000.0, 1000.0]  # First call and after sleep
        mock_timestamps[:] = [995.0, 996.0, 997.0, 998.0, 999.0]  # 5 recent requests (at limit)
        mock_random.return_value = 0.5  # Fixed jitter
        
        # Execute
        with patch('agents.aws_lambda.lambda_handler.wait_for_capacity', side_effect=lambda: None):
            wait_for_capacity()
        
        # Assert
        mock_sleep.assert_called_once()  # Should sleep when at limit
        sleep_time = mock_sleep.call_args[0][0]
        self.assertGreater(sleep_time, 0)  # Should sleep for positive time
    
    @patch('agents.aws_lambda.lambda_handler.bedrock_runtime')
    @patch('agents.aws_lambda.lambda_handler.wait_for_capacity')
    @patch('agents.aws_lambda.lambda_handler.request_timestamps')
    def test_invoke_bedrock_success(self, mock_timestamps, mock_wait, mock_bedrock):
        """Test successful invocation of Bedrock model."""
        # Setup
        mock_response = MagicMock()
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'Test response'}]
        })
        mock_bedrock.invoke_model.return_value = mock_response
        
        # Execute
        result = invoke_bedrock("Test prompt", 100, 0.7)
        
        # Assert
        self.assertEqual(result, "Test response")
        mock_wait.assert_called_once()  # Should call wait_for_capacity
        mock_bedrock.invoke_model.assert_called_once()  # Should call invoke_model
    
    @patch('agents.aws_lambda.lambda_handler.bedrock_runtime')
    @patch('agents.aws_lambda.lambda_handler.wait_for_capacity')
    @patch('agents.aws_lambda.lambda_handler.request_timestamps')
    @patch('agents.aws_lambda.lambda_handler.time.sleep')
    def test_invoke_bedrock_throttling(self, mock_sleep, mock_timestamps, mock_wait, mock_bedrock):
        """Test handling of throttling exception in Bedrock invocation."""
        # Setup
        throttling_exception = type('ThrottlingException', (Exception,), {})
        mock_bedrock.exceptions.ThrottlingException = throttling_exception
        
        # First call raises throttling, second succeeds
        mock_bedrock.invoke_model.side_effect = [
            throttling_exception("Rate exceeded"),
            MagicMock(body=MagicMock(read=lambda: json.dumps({'content': [{'text': 'Test response after retry'}]}))),
        ]
        
        # Execute
        result = invoke_bedrock("Test prompt", 100, 0.7)
        
        # Assert
        self.assertEqual(result, "Test response after retry")
        self.assertEqual(mock_bedrock.invoke_model.call_count, 2)  # Should retry after throttling
        mock_sleep.assert_called_once()  # Should sleep before retry

if __name__ == '__main__':
    unittest.main()