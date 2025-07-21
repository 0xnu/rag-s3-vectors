import json
import os
import boto3
from langchain_aws.embeddings import BedrockEmbeddings

VECTOR_BUCKET_NAME = os.environ["VECTOR_BUCKET_NAME"]
VECTOR_INDEX_NAME = os.environ["VECTOR_INDEX_NAME"]


def query_vectors(question: str) -> list:
    """Query S3 Vectors for similar documents."""
    
    # Initialize Bedrock client and embedding model
    bedrock_client = boto3.client("bedrock-runtime", "us-east-1")
    embedding_model = BedrockEmbeddings(
        client=bedrock_client,
        model_id="amazon.titan-embed-text-v2:0",
    )
    
    # Generate embedding for the question
    embedding = embedding_model.embed_query(question)
    
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
    
    return response["vectors"]


def generate_response(question: str, context_docs: list) -> str:
    """Generate response using Amazon Titan Text via direct Bedrock API."""
    
    # Format documents as simple text context
    context_text = "\n\n".join([
        f"Document {i+1}:\n{doc['metadata']['text']}"
        for i, doc in enumerate(context_docs)
    ])
    
    # Create the prompt for Titan Text
    system_prompt = (
        "You are a chatbot that answers questions about Shakespeare's Hamlet. "
        "Generate responses based on the content in the reference documents provided. "
        "If the documents don't contain relevant information, say so politely. "
        "Provide detailed, thoughtful responses based on the Shakespearean content."
    )
    
    user_prompt = f"Reference Documents:\n{context_text}\n\nQuestion: {question}"
    
    # Combine system and user prompts
    full_prompt = f"{system_prompt}\n\nHuman: {user_prompt}\n\nAssistant:"
    
    # Use direct Bedrock API call instead of LangChain
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
    
    # Titan Text response format: get the generated text
    if "results" in response_body and len(response_body["results"]) > 0:
        generated_text = response_body["results"][0]["outputText"].strip()
    else:
        # Fallback if response format is different
        generated_text = str(response_body.get("outputText", "No response generated"))
    
    return generated_text


def validate_api_key(event: dict) -> tuple[bool, str]:
    """Validate API key from request headers."""
    
    # Extract API key from headers
    headers = event.get("headers", {})
    
    # API Gateway passes headers in lowercase
    api_key = headers.get("x-api-key") or headers.get("X-Api-Key")
    
    if not api_key:
        return False, "Missing API key in request headers"
    
    # Log API key usage (first 8 characters only for security)
    print(f"API key used: {api_key[:8]}...")
    
    # Note: API Gateway handles actual key validation
    # This function is for additional logging/monitoring
    return True, "Valid API key"


def create_response(status_code: int, body_dict: dict) -> dict:
    """Create a standardised Lambda response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Api-Key",
            "Access-Control-Allow-Methods": "POST, OPTIONS"
        },
        "body": json.dumps(body_dict, ensure_ascii=False)
    }


def handler(event, context):
    """Main Lambda handler for RAG queries with API key authentication."""
    
    try:
        # Log request details for monitoring
        print(f"Received event: {json.dumps(event, default=str)}")
        
        # Handle CORS preflight requests
        if event.get("httpMethod") == "OPTIONS":
            return create_response(200, {"message": "CORS preflight response"})
        
        # Validate API key (for additional monitoring)
        is_valid, validation_message = validate_api_key(event)
        if not is_valid:
            print(f"API key validation failed: {validation_message}")
            # Note: API Gateway should have already blocked invalid keys
            # This is additional logging for monitoring purposes
        
        # Parse request body
        if isinstance(event.get("body"), str):
            request = json.loads(event["body"])
        else:
            request = event.get("body", {})
        
        question = request.get("question")
        if not question:
            return create_response(400, {
                "error": "Question parameter is required",
                "usage": "Send POST request with JSON body containing 'question' field"
            })
        
        # Validate question length
        if len(question.strip()) < 3:
            return create_response(400, {
                "error": "Question must be at least 3 characters long"
            })
        
        if len(question) > 500:
            return create_response(400, {
                "error": "Question must be less than 500 characters"
            })
        
        print(f"Processing question: {question}")
        
        # Query vectors for similar documents
        context_docs = query_vectors(question)
        print(f"Found {len(context_docs)} similar documents")
        
        if not context_docs:
            return create_response(200, {
                "answer": "I couldn't find relevant information about your question in my knowledge base. Please try rephrasing your question about Hamlet.",
                "sources": []
            })
        
        # Generate response using the context
        answer = generate_response(question, context_docs)
        print(f"Generated response: {answer[:100]}...")
        
        # Create sources list safely
        sources = []
        for doc in context_docs:
            try:
                source = {
                    "title": doc["metadata"].get("title", "Unknown"),
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
                "processing_successful": True
            }
        }
        
        return create_response(200, response_body)
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        return create_response(400, {
            "error": "Invalid JSON in request body"
        })
        
    except Exception as e:
        print(f"Error in handler: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return create_response(500, {
            "error": "Internal server error occurred",
            "support": "Please contact support if this persists"
        })