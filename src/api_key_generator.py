import json
import boto3
import random
import string
import cfnresponse


def generate_random_key(length=32):
    """Generate cryptographically secure random API key."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.SystemRandom().choice(characters) for _ in range(length))


def handler(event, context):
    """CloudFormation Custom Resource handler for API key generation."""
    try:
        request_type = event['RequestType']
        
        if request_type == 'Create':
            # Generate new random API key
            api_key = generate_random_key(32)
            
            response_data = {
                'ApiKey': api_key
            }
            
            print(f"Generated new API key: {api_key[:8]}...")
            cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)
            
        elif request_type == 'Update':
            # For updates, generate new key
            api_key = generate_random_key(32)
            
            response_data = {
                'ApiKey': api_key
            }
            
            print(f"Updated API key: {api_key[:8]}...")
            cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)
            
        elif request_type == 'Delete':
            # Nothing to clean up for API key generation
            print("API key generator - delete operation completed")
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
            
    except Exception as e:
        print(f"Error in API key generation: {str(e)}")
        cfnresponse.send(event, context, cfnresponse.FAILED, {})