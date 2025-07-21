import json
import os
import re
import boto3
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional
from langchain_aws.embeddings import BedrockEmbeddings

VECTOR_BUCKET_NAME = os.environ["VECTOR_BUCKET_NAME"]
VECTOR_INDEX_NAME = os.environ["VECTOR_INDEX_NAME"]


def sanitise_input(text: str) -> str:
    """Sanitise input text to prevent injection attacks."""
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    
    # Remove potential script tags and malicious content
    sanitised = re.sub(r'<[^>]*>', '', text)
    sanitised = re.sub(r'[^\w\s\.\?\!\,\-\'\"]', '', sanitised)
    
    return sanitised.strip()


def query_vectors(question: str) -> List[Dict]:
    """Query S3 Vectors for similar documents with enhanced error handling."""
    
    try:
        # Initialize Bedrock client and embedding model
        bedrock_client = boto3.client("bedrock-runtime", "us-east-1")
        embedding_model = BedrockEmbeddings(
            client=bedrock_client,
            model_id="amazon.titan-embed-text-v2:0",
        )
        
        # Generate embedding for the question
        embedding = embedding_model.embed_query(question)
        
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        raise RuntimeError(f"Failed to generate embedding: {str(e)}")
    
    try:
        # Query S3 Vectors
        s3vectors_client = boto3.client("s3vectors", "us-east-1")
        response = s3vectors_client.query_vectors(
            vectorBucketName=VECTOR_BUCKET_NAME,
            indexName=VECTOR_INDEX_NAME,
            queryVector={
                "float32": embedding,
            },
            topK=3,
            returnMetadata=True,
            returnDistance=True,
        )
        
        return response.get("vectors", [])
        
    except s3vectors_client.exceptions.ResourceNotFoundException:
        print(f"Vector index not found: {VECTOR_INDEX_NAME}")
        raise RuntimeError("Vector database not initialised")
    except s3vectors_client.exceptions.ValidationException as e:
        print(f"Invalid query parameters: {str(e)}")
        raise RuntimeError("Invalid query format")
    except Exception as e:
        print(f"Error querying vectors: {str(e)}")
        raise RuntimeError(f"Vector query failed: {str(e)}")


def generate_response(question: str, context_docs: List[Dict]) -> str:
    """Generate response using Amazon Titan Text with enhanced error handling."""
    
    if not context_docs:
        return "No relevant context found for your question."
    
    try:
        # Format documents as simple text context
        context_text = "\n\n".join([
            f"Document {i+1}:\n{doc['metadata']['text']}"
            for i, doc in enumerate(context_docs)
            if 'metadata' in doc and 'text' in doc['metadata']
        ])
        
        if not context_text:
            return "Context documents are malformed or empty."
        
        # Create the prompt for Titan Text
        system_prompt = (
            "You are a knowledgeable assistant that answers questions about Shakespeare's Hamlet. "
            "Generate accurate responses based solely on the reference documents provided. "
            "If the documents don't contain relevant information, state this clearly. "
            "Provide detailed, thoughtful responses whilst staying faithful to the source material."
        )
        
        user_prompt = f"Reference Documents:\n{context_text}\n\nQuestion: {question}"
        
        # Combine system and user prompts
        full_prompt = f"{system_prompt}\n\nHuman: {user_prompt}\n\nAssistant:"
        
        # Use direct Bedrock API call
        bedrock_client = boto3.client("bedrock-runtime", "us-east-1")
        
        # Prepare the request body for Titan Text
        request_body = {
            "inputText": full_prompt,
            "textGenerationConfig": {
                "temperature": 0.3,
                "topP": 0.9,
                "maxTokenCount": 1000
            }
        }
        
        # Call Bedrock directly
        response = bedrock_client.invoke_model(
            modelId="amazon.titan-text-premier-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        # Parse the response
        response_body = json.loads(response["body"].read())
        
        # Titan Text response format
        if "results" in response_body and len(response_body["results"]) > 0:
            generated_text = response_body["results"][0]["outputText"].strip()
        else:
            generated_text = response_body.get("outputText", "No response generated")
        
        return generated_text
        
    except bedrock_client.exceptions.ThrottlingException:
        print("Bedrock API throttling encountered")
        raise RuntimeError("Service temporarily unavailable due to high demand")
    except bedrock_client.exceptions.ValidationException as e:
        print(f"Invalid Bedrock request: {str(e)}")
        raise RuntimeError("Invalid request format")
    except Exception as e:
        print(f"Error generating response: {str(e)}")
        raise RuntimeError("Failed to generate response")


def validate_api_key(event: Dict) -> Tuple[bool, str]:
    """Validate API key from request headers."""
    
    headers = event.get("headers", {})
    
    # API Gateway passes headers in lowercase
    api_key = headers.get("x-api-key") or headers.get("X-Api-Key")
    
    if not api_key:
        return False, "Missing API key in request headers"
    
    # Basic validation - ensure it's alphanumeric and reasonable length
    if not re.match(r'^[a-zA-Z0-9]{20,50}$', api_key):
        return False, "Invalid API key format"
    
    # Log API key usage (first 8 characters only for security)
    print(f"API key used: {api_key[:8]}...")
    
    return True, "Valid API key"


def validate_question(question: str) -> Tuple[bool, str]:
    """Validate question input with comprehensive checks."""
    
    if not question:
        return False, "Question parameter is required"
    
    if not isinstance(question, str):
        return False, "Question must be a string"
    
    question = question.strip()
    
    if len(question) < 3:
        return False, "Question must be at least 3 characters long"
    
    if len(question) > 500:
        return False, "Question must be less than 500 characters"
    
    # Check for potentially malicious content
    suspicious_patterns = [
        r'<script',
        r'javascript:',
        r'eval\(',
        r'exec\(',
        r'import\s+os',
        r'__import__'
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, question, re.IGNORECASE):
            return False, "Question contains prohibited content"
    
    return True, "Valid question"


def create_response(status_code: int, body_dict: Dict) -> Dict:
    """Create a standardised Lambda response with security headers."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Api-Key",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block"
        },
        "body": json.dumps(body_dict, ensure_ascii=False)
    }


def handler(event, context):
    """Main Lambda handler for RAG queries with comprehensive error handling."""
    
    try:
        # Log request details for monitoring (sanitised)
        sanitised_event = {
            "httpMethod": event.get("httpMethod"),
            "path": event.get("path"),
            "headers": {k: "***" if k.lower() in ["authorization", "x-api-key"] else v 
                       for k, v in event.get("headers", {}).items()}
        }
        print(f"Received request: {json.dumps(sanitised_event)}")
        
        # Handle CORS preflight requests
        if event.get("httpMethod") == "OPTIONS":
            return create_response(200, {"message": "CORS preflight response"})
        
        # Validate API key
        is_valid_key, key_message = validate_api_key(event)
        if not is_valid_key:
            print(f"API key validation failed: {key_message}")
            return create_response(401, {"error": "Unauthorised", "message": key_message})
        
        # Parse request body safely
        try:
            if isinstance(event.get("body"), str):
                request = json.loads(event["body"])
            else:
                request = event.get("body", {})
        except json.JSONDecodeError:
            return create_response(400, {"error": "Invalid JSON in request body"})
        
        question = request.get("question")
        
        # Validate question
        is_valid_question, question_message = validate_question(question)
        if not is_valid_question:
            return create_response(400, {"error": question_message})
        
        # Sanitise question
        question = sanitise_input(question)
        print(f"Processing sanitised question: {question}")
        
        # Query vectors for similar documents
        try:
            context_docs = query_vectors(question)
            print(f"Found {len(context_docs)} similar documents")
        except RuntimeError as e:
            return create_response(503, {
                "error": "Service temporarily unavailable",
                "message": str(e)
            })
        
        if not context_docs:
            return create_response(200, {
                "answer": "I couldn't find relevant information about your question in my knowledge base. Please try rephrasing your question about Hamlet.",
                "sources": [],
                "metadata": {
                    "question_length": len(question),
                    "sources_found": 0,
                    "processing_successful": True
                }
            })
        
        # Generate response using the context
        try:
            answer = generate_response(question, context_docs)
            print(f"Generated response: {answer[:100]}...")
        except RuntimeError as e:
            return create_response(503, {
                "error": "Response generation failed",
                "message": str(e)
            })
        
        # Create sources list safely
        sources = []
        for doc in context_docs:
            try:
                metadata = doc.get('metadata', {})
                source = {
                    "title": metadata.get("title", "Unknown"),
                    "distance": float(doc.get("distance", 0.0)),
                    "relevance_score": round(1.0 - float(doc.get("distance", 0.0)), 3)
                }
                sources.append(source)
            except (KeyError, TypeError, ValueError) as e:
                print(f"Error processing source: {e}")
                continue
        
        response_body = {
            "answer": answer,
            "sources": sources,
            "metadata": {
                "question_length": len(question),
                "sources_found": len(context_docs),
                "processing_successful": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": context.aws_request_id
            }
        }
        
        return create_response(200, response_body)
        
    except Exception as e:
        print(f"Unexpected error in handler: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return create_response(500, {
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later."
        })