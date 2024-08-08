import boto3

from opensearchpy import (
    OpenSearch,
    RequestsHttpConnection,
    AWSV4SignerAuth,
    RequestError,
)


import sys
import json
from time import sleep

boto3_session = boto3.session.Session()
region_name = boto3_session.region_name

credentials = boto3.Session().get_credentials()
awsauth = auth = AWSV4SignerAuth(credentials, region_name, "aoss")

host = sys.argv[1].replace("https://", "")

index_name = f"cfn-knowledge-index"
body_json = {
    "settings": {
        "index.knn": "true",
        "number_of_shards": 1,
        "knn.algo_param.ef_search": 512,
        "number_of_replicas": 0,
    },
    "mappings": {
        "properties": {
            "cfn-vector-field": {
                "type": "knn_vector",
                "dimension": 1536,
                "method": {"name": "hnsw", "engine": "faiss", "space_type": "l2"},
            },
            "text": {"type": "text"},
            "metadata": {"type": "text"},
        }
    },
}

# Build the OpenSearch client
oss_client = OpenSearch(
    hosts=[{"host": host, "port": 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=300,
)

try:
    response = oss_client.indices.create(index=index_name, body=json.dumps(body_json))
    print("\nCreating index:")
    print(response)

    # index creation can take up to a minute
    sleep(60)
except RequestError as e:
    # you can delete the index if its already exists
    # oss_client.indices.delete(index=index_name)
    print(
        f"Error while trying to create the index, with error {e.error}\nyou may unmark the delete above to delete, and recreate the index"
    )
