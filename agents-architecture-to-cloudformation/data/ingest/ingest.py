import boto3
from botocore.exceptions import ClientError

import sys
import os
import json

bedrock_agent_client = boto3.client("bedrock-agent")
s3 = boto3.client("s3")
s3_bucket_name = sys.argv[1]
knowledgeBaseId = sys.argv[2]
dataSourceId = sys.argv[3]

current_dir = os.path.dirname(os.path.realpath(__file__))


def create_metadata_file(response, metadata_filename):
    with open(os.path.join(current_dir, metadata_filename), "w") as f:
        meta_data = {
            "metadataAttributes": {
                "cfn_stack": response["cfn_stack"],
                "architecture_image": response["architecture_image"],
            }
        }
        f.write(json.dumps(meta_data))


def upload_s3(domain, domain_file, domain_file_path, s3_folder):
    try:
        s3.upload_file(
            domain_file_path,
            s3_bucket_name,
            os.path.join(s3_folder, domain, domain_file),
        )
        print(f"Uploaded {domain_file} to {s3_bucket_name} to data")
    except ClientError as e:
        print(f"Error uploading {domain_file}: {e}")


def ingest_knowledge_s3(response):
    # list all folders in a directory
    for domain in os.listdir(current_dir):
        domain_path = os.path.join(current_dir, domain)
        try:
            domain_files = os.listdir(domain_path)
        except Exception as e:
            print(e)
            continue

        for domain_file in domain_files:

            if domain_file.endswith(".txt"):
                domain_file_path = os.path.join(domain_path, domain_file)
                upload_s3(domain, domain_file, domain_file_path, "ingest")
                metadata_filename = domain_file + ".metadata.json"
                example_name = domain_file.split(".")[0]
                create_metadata_file(
                    response=response[f"data/{domain}/{example_name}"],
                    metadata_filename=metadata_filename,
                )
                upload_s3(
                    domain,
                    metadata_filename,
                    os.path.join(current_dir, metadata_filename),
                    "ingest",
                )


def ingest_data_s3():
    response = dict()
    for domain in os.listdir(current_dir):
        domain_path = os.path.join(current_dir, domain)
        try:
            domain_files = os.listdir(domain_path)
        except Exception as e:
            print(e)
            continue

        for domain_file in domain_files:

            if not domain_file.endswith(".txt"):
                domain_file_path = os.path.join(domain_path, domain_file)
                example_name = domain_file.split(".")[0]
                if f"data/{domain}/{example_name}" not in response:
                    response[f"data/{domain}/{example_name}"] = {
                        "cfn_stack": None,
                        "architecture_image": None,
                    }

                if domain_file.endswith(".yaml"):
                    response[f"data/{domain}/{example_name}"][
                        "cfn_stack"
                    ] = f"s3://{s3_bucket_name}/data/{domain}/{domain_file}"
                    upload_s3(domain, domain_file, domain_file_path, "data")
                elif (
                    domain_file.endswith(".jpeg")
                    or domain_file.endswith(".png")
                    or domain_file.endswith(".jpg")
                ):
                    response[f"data/{domain}/{example_name}"][
                        "architecture_image"
                    ] = f"s3://{s3_bucket_name}/data/{domain}/{domain_file}"
                    upload_s3(domain, domain_file, domain_file_path, "data")
    return response


def sync_data_source():
    start_job_response = bedrock_agent_client.start_ingestion_job(
        knowledgeBaseId=knowledgeBaseId, dataSourceId=dataSourceId
    )

    job = start_job_response["ingestionJob"]
    while job["status"] != "COMPLETE":
        get_job_response = bedrock_agent_client.get_ingestion_job(
            knowledgeBaseId=knowledgeBaseId,
            dataSourceId=dataSourceId,
            ingestionJobId=job["ingestionJobId"],
        )
        job = get_job_response["ingestionJob"]


if __name__ == "__main__":
    response = ingest_data_s3()
    ingest_knowledge_s3(response)
    sync_data_source()
