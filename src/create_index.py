import os
import uuid
import json
from pathlib import Path

import boto3
from langchain_aws.embeddings import BedrockEmbeddings
from langchain_text_splitters import MarkdownTextSplitter
from tqdm import tqdm


def create_index(source_text: str, title: str) -> None:
    """Create vector index from source text."""
    
    # Initialize Bedrock client and embedding model
    bedrock_client = boto3.client("bedrock-runtime", "us-east-1")
    embedding_model = BedrockEmbeddings(
        client=bedrock_client,
        model_id="amazon.titan-embed-text-v2:0",
    )
    
    # Split text into chunks
    text_splitter = MarkdownTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    chunks = text_splitter.split_text(source_text)
    
    print(f"● Split text into {len(chunks)} chunks")
    
    # Create vectors from chunks
    vectors = []
    print("● Creating vectors from source text...")
    
    for chunk in tqdm(chunks):
        try:
            embedding = embedding_model.embed_query(chunk)
            vectors.append({
                "key": str(uuid.uuid4()),
                "data": {
                    "float32": embedding,
                },
                "metadata": {
                    "text": chunk,
                    "title": title,
                },
            })
        except Exception as e:
            print(f"Error creating embedding for chunk: {e}")
            continue
    
    # Store vectors in S3 Vectors
    s3vectors_client = boto3.client("s3vectors", "us-east-1")
    
    try:
        s3vectors_client.put_vectors(
            vectorBucketName=os.environ["VECTOR_BUCKET_NAME"],
            indexName=os.environ["VECTOR_INDEX_NAME"],
            vectors=vectors,
        )
        print(f"● Successfully stored {len(vectors)} vectors")
    except Exception as e:
        print(f"Error storing vectors: {e}")
        raise


def load_sample_data() -> tuple[str, str]:
    """Load sample Shakespearean text for demonstration."""
    sample_text = """
    # The Chronicle of Hamlet, Prince of Denmark

    ## Act I - The Ghost's Revelation
    
    Upon the battlements of Elsinore Castle, where the bitter Danish winds doth blow, young Hamlet encounters the spectre of his father most dear. The ghost, clad in armour complete, doth speak of murder most foul and unnatural. "Revenge his foul and most unnatural murder," the spirit commands, revealing that Claudius, now king and husband to Gertrude, did pour poison in the sleeping king's ear.
    
    Hamlet, struck with grief and doubt, vows to remember naught but this commandment from his father's spirit. Yet doubt gnaws at his noble heart - is this ghost a demon sent to damn his soul, or truly his father's spirit seeking justice?
    
    ## Act II - The Prince's Feigned Madness
    
    To better observe the court and plan his revenge, Hamlet assumes an antic disposition, speaking in riddles and behaving as one touched by lunacy. His beloved Ophelia, daughter to Polonius the king's counsellor, bears witness to this transformation with heavy heart.
    
    "Get thee to a nunnery," Hamlet doth cry to fair Ophelia, believing all women to be false and corrupted. His harsh words wound her gentle spirit, though he speaks thus to protect her from the corruption of the court.
    
    ## Act III - The Play Within the Play
    
    Hamlet, still uncertain of Claudius's guilt, devises a cunning stratagem. He commissions a play called "The Mousetrap" that mirrors his father's murder, hoping to catch the conscience of the king. "The play's the thing wherein I'll catch the conscience of the king," declares the prince.
    
    As the players enact the poisoning scene, Claudius rises in evident guilt and storms from the hall, confirming Hamlet's suspicions. The king's reaction provides the proof that Hamlet sought - Claudius is indeed his father's murderer.
    
    ## The Tragedy of Ophelia
    
    Sweet Ophelia, caught between her love for Hamlet and loyalty to her father Polonius, descends into true madness after Hamlet accidentally slays Polonius behind the arras in Gertrude's chamber. She wanders the castle singing fragments of old songs, distributing flowers with symbolic meaning.
    
    "There's rosemary, that's for remembrance," she tells the court, her mind unravelled by grief. Her brother Laertes returns from France to find his sister thus afflicted and his father dead by Hamlet's hand.
    
    ## The Final Duel
    
    Claudius, seeking to rid himself of the troublesome prince, arranges a duel between Hamlet and Laertes, who seeks revenge for his father's death. The king poisons Laertes's sword and prepares poisoned wine as backup treachery.
    
    In the final catastrophe, both Hamlet and Laertes are wounded by the poisoned blade. Gertrude drinks the poisoned wine intended for Hamlet. As death approaches, Hamlet finally strikes down Claudius, achieving his father's commanded revenge.
    
    ## The Prince's Final Words
    
    With his dying breath, Hamlet speaks to his faithful friend Horatio: "The rest is silence." He charges Horatio to tell his story to the world, that all might know the truth of what transpired in the cursed court of Denmark.
    
    Young Fortinbras of Norway arrives to restore order to the kingdom, finding the stage littered with the noble dead. He commands that Hamlet be borne like a soldier to his rest, "for he was likely, had he been put on, to have proved most royally."
    
    ## Themes of the Noble Tragedy
    
    ### Revenge and Justice
    The play explores the nature of revenge - whether it brings justice or merely perpetuates cycles of violence and death.
    
    ### Appearance versus Reality
    Throughout the drama, characters struggle to distinguish truth from deception, reality from performance.
    
    ### Death and Mortality
    From the ghost's appearance to the final bloodbath, death haunts every scene, reminding mortals of their finite nature.
    
    ### Madness and Reason
    Both feigned and real madness serve as responses to an unbearable reality, questioning the boundaries of sanity.
    """
    
    return sample_text, "Hamlet"


def handler(event, context):
    """Lambda handler for vector creation."""
    try:
        # For Lambda deployment, load from event or use sample data
        if event.get("source_text") and event.get("title"):
            source_text = event["source_text"]
            title = event["title"]
        else:
            # Use sample data for demonstration
            source_text, title = load_sample_data()
        
        create_index(source_text, title)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Vector index created successfully",
                "title": title
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        print(f"Error in handler: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e)
            }, ensure_ascii=False)
        }


if __name__ == "__main__":
    # For local execution
    os.environ["VECTOR_BUCKET_NAME"] = "shakespeare-rag-vector-bucket"
    os.environ["VECTOR_INDEX_NAME"] = "hamlet-shakespeare-index"
    
    source_text, title = load_sample_data()
    create_index(source_text, title)
