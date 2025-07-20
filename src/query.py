import os
import argparse
import json

import boto3
from langchain_aws.embeddings import BedrockEmbeddings


def query_vectors(question: str, vector_bucket: str, index_name: str, top_k: int = 3) -> None:
    """Query S3 Vectors and display results."""
    
    print(f"🔍 Searching for: {question}")
    print(f"📦 Vector Bucket: {vector_bucket}")
    print(f"📊 Index: {index_name}")
    print("-" * 50)
    
    # Initialize Bedrock client and embedding model
    bedrock_client = boto3.client("bedrock-runtime", "us-east-1")
    embedding_model = BedrockEmbeddings(
        client=bedrock_client,
        model_id="amazon.titan-embed-text-v2:0",
    )
    
    try:
        # Generate embedding for the question
        print("🧠 Generating embedding...")
        embedding = embedding_model.embed_query(question)
        print(f"✅ Embedding generated (dimension: {len(embedding)})")
        
        # Query S3 Vectors
        print("🔎 Querying vectors...")
        s3vectors_client = boto3.client("s3vectors", "us-east-1")
        response = s3vectors_client.query_vectors(
            vectorBucketName=vector_bucket,
            indexName=index_name,
            queryVector={
                "float32": embedding,
            },
            topK=top_k,
            returnMetadata=True,
            returnDistance=True,
        )
        
        vectors = response["vectors"]
        print(f"✅ Found {len(vectors)} similar documents")
        print("=" * 50)
        
        # Display results
        for i, vector in enumerate(vectors, 1):
            metadata = vector.get("metadata", {})
            distance = vector.get("distance", 0.0)
            text = metadata.get("text", "No text available")
            title = metadata.get("title", "Unknown")
            
            print(f"📄 Result {i}")
            print(f"   Title: {title}")
            print(f"   Distance: {distance:.4f}")
            print(f"   Key: {vector.get('key', 'Unknown')}")
            print(f"   Text Preview: {text[:200]}{'...' if len(text) > 200 else ''}")
            print("-" * 50)
        
        # Summary statistics
        if vectors:
            distances = [v.get("distance", 0.0) for v in vectors]
            print(f"📊 Distance Statistics:")
            print(f"   Best Match: {min(distances):.4f}")
            print(f"   Worst Match: {max(distances):.4f}")
            print(f"   Average: {sum(distances) / len(distances):.4f}")
        
    except Exception as e:
        print(f"❌ Error during query: {str(e)}")
        raise


def test_embeddings() -> None:
    """Test embedding generation without querying vectors."""
    
    print("🧪 Testing embedding generation...")
    
    bedrock_client = boto3.client("bedrock-runtime", "us-east-1")
    embedding_model = BedrockEmbeddings(
        client=bedrock_client,
        model_id="amazon.titan-embed-text-v2:0",
    )
    
    test_text = "This is a test sentence for embedding generation."
    
    try:
        embedding = embedding_model.embed_query(test_text)
        print(f"✅ Embedding test successful")
        print(f"   Text: {test_text}")
        print(f"   Embedding dimension: {len(embedding)}")
        print(f"   Sample values: {embedding[:5]}")
        
    except Exception as e:
        print(f"❌ Embedding test failed: {str(e)}")
        raise


def main():
    """Main function with CLI interface."""
    
    parser = argparse.ArgumentParser(description="Query S3 Vectors for similarity search")
    parser.add_argument("-q", "--question", type=str, help="Question to search for")
    parser.add_argument("-b", "--bucket", type=str, help="Vector bucket name")
    parser.add_argument("-i", "--index", type=str, help="Vector index name")
    parser.add_argument("-k", "--top-k", type=int, default=3, help="Number of results to return")
    parser.add_argument("--test-embeddings", action="store_true", help="Test embedding generation only")
    
    args = parser.parse_args()
    
    # Test embeddings only
    if args.test_embeddings:
        test_embeddings()
        return
    
    # Get configuration from arguments or environment
    question = args.question or input("Enter your question: ")
    bucket = args.bucket or os.environ.get("VECTOR_BUCKET_NAME")
    index = args.index or os.environ.get("VECTOR_INDEX_NAME")
    
    if not bucket:
        print("❌ Vector bucket name required (use -b flag or set VECTOR_BUCKET_NAME env var)")
        return
        
    if not index:
        print("❌ Vector index name required (use -i flag or set VECTOR_INDEX_NAME env var)")
        return
    
    # Execute query
    query_vectors(question, bucket, index, args.top_k)


if __name__ == "__main__":
    # Example environment setup for direct execution
    if not os.environ.get("VECTOR_BUCKET_NAME"):
        os.environ["VECTOR_BUCKET_NAME"] = "shakespeare-rag-vector-bucket"
    if not os.environ.get("VECTOR_INDEX_NAME"):
        os.environ["VECTOR_INDEX_NAME"] = "hamlet-shakespeare-index"
    
    main()