## RAG S3 Vectors

[![Lint](https://github.com/0xnu/rag-s3-vectors/actions/workflows/lint.yaml/badge.svg)](https://github.com/0xnu/rag-s3-vectors/actions/workflows/lint.yaml)
[![Release](https://img.shields.io/github/release/0xnu/rag-s3-vectors.svg)](https://github.com/0xnu/rag-s3-vectors/releases/latest)
[![License](https://img.shields.io/badge/License-Modified_MIT-f5de53?&color=f5de53)](/LICENSE)

A system using [Amazon S3 Vectors](https://aws.amazon.com/s3/features/vectors/) and [Amazon Bedrock](https://aws.amazon.com/bedrock/) to create a [RAG](https://en.wikipedia.org/wiki/Retrieval-augmented_generation) (Retrieval-Augmented Generation) system for Shakespearean plays. The system is designed to answer questions about the plays based on the text and embeddings stored in the vector database.

> [!NOTE]
> [I am available](mailto:f@finbarrs.eu) for consultations on AI and RAG.

### Prerequisite

Here are the steps to deploy your Shakespeare RAG system:

1. Manual S3 Vector Infrastructure Setup

Create Vector Bucket (AWS Console):
+ Navigate to Amazon S3 in us-east-1 region
+ Look for `Vector Buckets` in the sidebar (preview feature)
+ Create bucket named: `shakespeare-rag-vector-bucket`
+ Note: Must be globally unique, so add suffix if needed

Create Vector Index:
+ Within your vector bucket, create index: hamlet-shakespeare-index
+ Set dimensions to 1024 (Titan Embed v2 default)
+ Choose cosine distance metric
+ Exclude text metadata from filter targets (only title should be filterable)

2. AWS Bedrock Model Access

Enable Required Models:
+ Go to Amazon Bedrock console
+ Request access to `amazon.titan-embed-text-v2:0`
+ Request access to `amazon.titan-text-premier-v1:0`
+ Wait for approval (usually immediate for Titan models)

### Deployment Commands

```sh
# Install SAM CLI via Homebrew
brew tap aws/tap
brew install aws-sam-cli

# Verify installation
sam --version

# Build the SAM application
sam build

# Deploy with guided setup (first time)
sam deploy --guided

# Use these parameters when prompted:
# Stack Name: shakespeare-rag-system
# AWS Region: us-east-1 (or your preferred region)
# VectorBucketName: shakespeare-rag-vector-bucket
# VectorIndexName: hamlet-shakespeare-index

# For subsequent deployments
sam deploy

# To destroy everything deployed by SAM, use:
sam delete

# Delete S3 Vectors resources
aws s3vectors delete-index --vector-bucket-name "shakespeare-rag-vector-bucket" --index-name "hamlet-shakespeare-index" --region us-east-1
aws s3vectors delete-vector-bucket --vector-bucket-name "shakespeare-rag-vector-bucket" --region us-east-1
```

### Testing Locally

You can now test the system locally with Shakespearean queries:

```sh
# Test embedding generation
python3 -m src.query --test-embeddings

# Query with command line arguments
python3 -m src.query -q "Tell me about Hamlet's relationship with Ophelia"

# Interactive query mode
python3 -m src.query
```

### Testing API

Once deployed, test with Shakespearean queries:

```sh
curl -X POST "https://5hbsiaq1c4.execute-api.us-east-1.amazonaws.com/prod/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "How did Ophelia go mad?"}'

#### Example Shakespearean Test Queries
"What was the play within the play about?"
"Tell me about Hamlet'\''s feigned madness"
"What happened in the final duel?"
```

#### Response

```json
{"answer": "Ophelia goes mad due to her father's death and Hamlet's behavior towards her.", "sources": []}%
```

### Vector Database Pricing Comparison 2025

| Vector Database | Pricing Model | Monthly Cost (Example) | Key Features | Best For |
|---|---|---|---|---|
| **Amazon S3 Vectors** | Pay-as-you-use: <br/>• Data upload: $0.20/GB <br/>• Storage: $0.06/GB/month <br/>• Queries: Variable by request count | **$1,216/month** <br/>(400M vectors, 40 indexes, 10M queries) <br/>• Storage: $141 <br/>• Upload: $78 <br/>• Queries: $997 | • **90% cost reduction** vs traditional DBs <br/>• Native S3 integration <br/>• Serverless, no infrastructure <br/>• Sub-second query performance | Long-term storage, <br/>infrequent access, <br/>cost-sensitive workloads |
| **Pinecone** | Tiered plans: <br/>• Starter: Free (100K vectors) <br/>• Standard: $50/month minimum <br/>• Enterprise: $500/month minimum | **$480/month** <br/>(Multiple p1.x2 pods with replicas) <br/>Single pod: ~$160/month | • Fully managed <br/>• Sub-100ms latency <br/>• Auto-scaling <br/>• 50x cost reduction with serverless | Production apps, <br/>real-time search, <br/>high QPS requirements |
| **Qdrant** | Usage-based: <br/>• Free: 1GB cluster forever <br/>• Cloud: ~$0.03494/hour <br/>• Hybrid: $0.014/hour | **$25-50/month** <br/>(Small to medium clusters) <br/>Scales with RAM, CPU, storage | • Open-source option <br/>• 4x higher RPS than competitors <br/>• Built in Rust for performance <br/>• Advanced filtering | Performance-critical apps, <br/>open-source preference, <br/>custom deployments |
| **Chroma** | Open-source + Cloud: <br/>• Open-source: Free <br/>• Cloud Starter: $0/month + $5 credits <br/>• Cloud Team: $100 credits then usage-based | **$0-150/month** <br/>(Self-hosted on AWS m4.xlarge: ~$150) <br/>Cloud version: Usage-based | • Completely free open-source <br/>• Easy local development <br/>• Python/JS focused <br/>• Simple API | Prototyping, <br/>development, <br/>budget-conscious projects |
| **Weaviate** | Dimension-based: <br/>• $0.05 per million dimensions <br/>• Serverless and managed options | **$50-200/month** <br/>($1 for 20M dimensions) <br/>Enterprise: Custom pricing | • GraphQL + REST APIs <br/>• Built-in vectorization modules <br/>• Multi-modal support <br/>• Open-source available | Enterprise applications, <br/>multi-modal data, <br/>flexible deployment |

## Key Insights

### 🏆 **Best Value: Amazon S3 Vectors**
- Up to 90% cost reduction compared to traditional vector databases
- Ideal for large-scale, infrequently accessed vector data
- No infrastructure management required

### ⚡ **Best Performance: Qdrant**
- Up to 4x higher RPS than competitors
- Built in Rust for maximum performance
- Flexible deployment options

### 🎯 **Best for Production: Pinecone**
- Mature platform with proven scalability
- 50x cost reduction with new serverless architecture
- Strong enterprise support and SLAs

### 💰 **Best for Budgets: Chroma**
- Completely free and open-source
- Perfect for prototyping and small projects
- Easy local development

### 🔧 **Best for Flexibility: Weaviate**
- Transparent per-dimension pricing starting at $0.05 per million dimensions
- Strong open-source ecosystem
- Multi-modal capabilities

#### Decision Framework

**Choose S3 Vectors if:** You need cost-effective storage for large datasets with moderate query frequency and already use AWS infrastructure.

**Choose Pinecone if:** You need a fully managed solution with guaranteed performance SLAs and enterprise support.

**Choose Qdrant if:** Performance is critical and you want the flexibility of open-source with optional managed services.

**Choose Chroma if:** You're prototyping, learning, or building small-scale applications on a tight budget.

**Choose Weaviate if:** You need multi-modal support, prefer GraphQL APIs, or want enterprise features with open-source flexibility.

---
*Pricing data current as of July 2025. Costs may vary based on specific usage patterns, regions, and enterprise agreements.*

### License

This project is licensed under the [Modified MIT License](./LICENSE).

### Citation

```tex
@misc{rags3vectors,
  author       = {Oketunji, A.F.},
  title        = {RAG S3 Vectors},
  year         = 2025,
  version      = {0.0.1},
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.16203571},
  url          = {https://doi.org/10.5281/zenodo.16203571}
}
```

### Copyright

(c) 2025 [Finbarrs Oketunji](https://finbarrs.eu). All Rights Reserved.
