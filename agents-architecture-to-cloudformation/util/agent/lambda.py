import sys
from pip._internal import main

main(
    [
        "install",
        "-I",
        "-q",
        "boto3",
        "--target",
        "/tmp/",
        "--no-cache-dir",
        "--disable-pip-version-check",
    ]
)
sys.path.insert(0, "/tmp/")

from botocore.exceptions import ClientError, ValidationError
from boto3.session import Session
from botocore.config import Config

import generateCloudFormationPrompt, reiterateCloudFormationPrompt, resolveErrorPrompt, updateInstructionPrompt, sys_generateCloudFormationPrompt, sys_reiterateCloudFormationPrompt, sys_resolveErrorPrompt, sys_updateInstructionPrompt

import random
import time
import os
import datetime

KnowledgeBaseId = os.environ["KnowledgeBaseId"]
EnvironmentName = os.environ["EnvironmentName"]
BedrockModelId = os.environ["BedrockModelId"]

bedrock = Session().client(
    "bedrock-runtime", config=Config(read_timeout=600, connect_timeout=600)
)
cfn = Session().client("cloudformation")
bedrock_agent = Session().client("bedrock-agent-runtime")
s3 = Session().client("s3")
table = Session().resource("dynamodb").Table(f"templatestorage-atc-{EnvironmentName}")


############################
##### Invoke Bedrock ######
##########################
def invoke_model(modelId, system_prompt, messages):
    """
    Invokes Amazon Bedrock Foundational model.

    Args:
        modelId (str): The ID or name of the foundational model to be invoked.
        system_prompt (str): The prompt or instruction to be provided to the model, setting the context or guiding the model's behavior.
        messages (list): A list of messages or input data to be processed by the model.

    Returns:
        str: The response or output generated by the model.
    """

    response = bedrock.converse(
        modelId=modelId,
        messages=messages,
        system=[{"text": system_prompt}],
        inferenceConfig={"temperature": 0.2, "maxTokens": 4000},
    )
    return response["output"]["message"]["content"][0]["text"]


def backoff_mechanism(func, modelId, system_prompt, messages):
    """
    Implements a backoff mechanism to handle throttling exceptions.

    Args:
        func (function): The function to be called with backoff.
        modelId (str): The ID or name of the foundational model to be invoked.
        system_prompt (str): The prompt or instruction to be provided to the model, setting the context or guiding the model's behavior.
        messages (list): A list of messages or input data to be processed by the model.

    Returns:
        str: The response or output generated by the model.
    """
    MAX_RETRIES = 5  # Maximum number of retries
    INITIAL_DELAY = 1  # Initial delay in seconds
    MAX_DELAY = 60  # Maximum delay in second

    delay = INITIAL_DELAY
    retries = 0

    while retries < MAX_RETRIES:
        try:
            return func(modelId=modelId, system_prompt=system_prompt, messages=messages)
        except bedrock.exceptions.ThrottlingException as e:
            print(f"Retry {retries + 1}/{MAX_RETRIES}: {e}")
            time.sleep(delay + random.uniform(0, 1))  # Add a random jitter
            delay = min(delay * 2, MAX_DELAY)
            retries += 1

    return False


#########################
##### Cache and KB #####
#######################


def put_validity_cloudformation(sessionId, template, is_valid):
    """
    Stores the validity of a CloudFormation template in DynamoDB.

    Args:
        sessionId (str): The ID of the session.
        template (str): The CloudFormation template.
        is_valid (bool): Whether the template is valid or not.

    Returns:
        bool: True if the validity is stored successfully, False otherwise.
    """
    try:
        creationDate = str(
            int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())
        )
        ttl = str(
            int((datetime.datetime.now() + datetime.timedelta(seconds=900)).timestamp())
        )

        response = table.update_item(
            Key={"sessionId": sessionId, "version": "v0"},
            # Atomic counter is used to increment the latest version
            UpdateExpression="SET Latest = if_not_exists(Latest, :defaultval) + :incrval, #creationDate = :creationDate, #template = :template, #ttl = :ttl, #is_valid = :is_valid",
            ExpressionAttributeNames={
                "#creationDate": "creationDate",
                "#template": "template",
                "#ttl": "ttl",
                "#is_valid": "is_valid",
            },
            ExpressionAttributeValues={
                ":creationDate": creationDate,
                ":is_valid": is_valid,
                ":template": template,
                ":ttl": ttl,
                ":defaultval": 0,
                ":incrval": 1,
            },
            # return the affected attribute after the update
            ReturnValues="UPDATED_NEW",
        )

        # Get the updated version
        latest_version = response["Attributes"]["Latest"]

        # Add the new item with the latest version
        table.put_item(
            Item={
                "sessionId": sessionId,
                "is_valid": is_valid,
                "version": "v" + str(latest_version),
                "creationDate": creationDate,
                "template": template,
                "ttl": ttl,
            }
        )
    except Exception as ex:
        print(f"Error at put_generated_cloudformation {ex}")
        return False
    else:
        return True


def put_generated_cloudformation(sessionId, template):
    """
    Stores the generated CloudFormation template in DynamoDB.

    Args:
        sessionId (str): The ID of the session.
        template (str): The generated CloudFormation template.

    Returns:
        bool: True if the template is stored successfully, False otherwise.
    """
    try:
        creationDate = str(
            int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())
        )
        ttl = str(
            int((datetime.datetime.now() + datetime.timedelta(seconds=900)).timestamp())
        )

        response = table.update_item(
            Key={"sessionId": sessionId, "version": "v0"},
            # Atomic counter is used to increment the latest version
            UpdateExpression="SET Latest = if_not_exists(Latest, :defaultval) + :incrval, #creationDate = :creationDate, #template = :template, #ttl = :ttl, #is_valud = :is_valid",
            ExpressionAttributeNames={
                "#creationDate": "creationDate",
                "#template": "template",
                "#ttl": "ttl",
                "#is_valud": "is_valid",
            },
            ExpressionAttributeValues={
                ":creationDate": creationDate,
                ":template": template,
                ":ttl": ttl,
                ":defaultval": 0,
                ":incrval": 1,
                ":is_valid": None,
            },
            # return the affected attribute after the update
            ReturnValues="UPDATED_NEW",
        )

        # Get the updated version
        latest_version = response["Attributes"]["Latest"]

        # Add the new item with the latest version
        table.put_item(
            Item={
                "sessionId": sessionId,
                "version": "v" + str(latest_version),
                "creationDate": creationDate,
                "template": template,
                "ttl": ttl,
            }
        )
    except Exception as ex:
        print(f"Error at put_generated_cloudformation {ex}")
        return False
    else:
        return True


def get_generated_cloudformation(sessionId, version="v0"):
    """
    Retrieves the generated CloudFormation template from DynamoDB.

    Args:
        sessionId (str): The ID of the session.
        version (str): The version of the template to retrieve.

    Returns:
        str: The generated CloudFormation template.
    """
    return table.get_item(Key={"sessionId": sessionId, "version": version})["Item"][
        "template"
    ]


def get_kb_yaml(sessionId, version="METADATA"):
    """
    Retrieves the YAML metadata from DynamoDB.

    Args:
        sessionId (str): The ID of the session.
        version (str): The version of the metadata to retrieve.

    Returns:
        dict: The YAML metadata.
    """
    return table.get_item(Key={"sessionId": sessionId, "version": version})


def retrieve_relevant_documents(sessionId, query):
    """
    Retrieves relevant documents from the knowledge base.

    Args:
        sessionId (str): The ID of the session.
        query (str): The query to search for relevant documents.

    Returns:
        dict: The relevant documents.
    """
    creationDate = str(int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp()))
    ttl = str(
        int((datetime.datetime.now() + datetime.timedelta(seconds=900)).timestamp())
    )

    relevant_documents = bedrock_agent.retrieve(
        retrievalQuery={"text": get_summary_document(query)},
        knowledgeBaseId=KnowledgeBaseId,
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": 3,
                "overrideSearchType": "HYBRID",
            }
        },
    )

    for idx, metadata in enumerate(
        [result["metadata"] for result in relevant_documents["retrievalResults"]]
    ):

        response = table.update_item(
            Key={"sessionId": sessionId, "version": "METADATA"},
            UpdateExpression=f"SET #document{idx} = :document{idx}, #creationDate = :creationDate, #ttl = :ttl",
            ExpressionAttributeNames={
                f"#document{idx}": f"document{idx}",
                "#creationDate": "creationDate",
                "#ttl": "ttl",
            },
            ExpressionAttributeValues={
                f":document{idx}": metadata,
                ":creationDate": creationDate,
                ":ttl": ttl,
            },
            # return the affected attribute after the update
            ReturnValues="ALL_NEW",
        )
    return response["Attributes"]


def retrieve_yaml(sessionId, query=None):
    """
    Retrieves the yaml from DynamoDB if it exists there, or from the knowledge base if the metadata is not found in DynamoDB.

    Args:
        sessionId (str): The ID of the session.
        query (str): The query to search for relevant documents.

    Returns:
        dict: The YAML metadata.
    """
    response = get_kb_yaml(sessionId=sessionId, version="METADATA")

    if "Item" in response:
        relevant_documents = response["Item"]
        print(f"Found item in dynamodb {sessionId}")
    else:
        print(f"Item with key {sessionId} not found.")
        relevant_documents = retrieve_relevant_documents(
            sessionId=sessionId, query=query
        )

    documents = list()

    for docs in [v for k, v in relevant_documents.items() if "document" in k]:
        bucket, key = docs["cfn_stack"].replace("s3://", "").split("/", 1)

        try:
            # Retrieve the object contents
            response = s3.get_object(Bucket=bucket, Key=key)
            contents = response["Body"].read().decode("utf-8")
            documents.append(contents)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                print("The specified object does not exist.")
            else:
                print(f"An error occurred: {e}")

    return documents


###############################
##### Utility Functions  #####
#############################


def get_summary_document(explain):
    """
    Generating an explanation with less than 1000 characters to accommodate the character limit for the knowledge base query.

    Args:
        explain (str): Current architecture explanation recieved from the streamlit app.

    Returns:
        str: New architecture explanation with less than 1000 characters.
    """
    _system_prompt = """
        List all the AWS Services in the document. Do output anything else.
    """
    _prompt = f"""
        <document>
        {explain}
        </document>

    """
    _messages = [{"role": "user", "content": [{"text": _prompt}]}]
    # func, modelId, system_prompt, messages
    return backoff_mechanism(
        func=invoke_model,
        modelId=BedrockModelId,
        system_prompt=_system_prompt,
        messages=_messages,
    )


#########################
##### Generate CFN #####
#######################


def generate_cloudformation(architectureExplanation, sessionId):
    """
    Generates a CloudFormation template from an architecture explanation. Stores this generated template in DynamoDB.

    Args:
        event (dict): The event data.

    Returns:
        bool: Indicating if the template was generated successfully.
    """
    try:

        documents = retrieve_yaml(sessionId=sessionId, query=architectureExplanation)

        _system_prompt = sys_generateCloudFormationPrompt.SYS_GENERATE_CLOUDFORMATION_PROMPT

        _prompt = generateCloudFormationPrompt.GENERATE_CLOUDFORMATION_PROMPT.replace("{{architectureExplanation}}", architectureExplanation)
        
        message_document = [
            {
                "role": "user",
                "content": [
                    {
                        "text": f"""Take this example CloudFormation YAML code as a refernce <example{idx}></example{idx}>:
                            <example{idx}>
                                {document}
                            </example{idx}>
                            """,
                    }
                    for idx, document in enumerate(documents)
                ],
            }
        ]
        message_document[0]["content"].append(
            {
                "text": _prompt,
            },
        )
        _messages = message_document
    except Exception as ex:
        return False, ex
    else:
        # func, modelId, system_prompt, messages
        generated_cloudformation_stack = backoff_mechanism(
            func=invoke_model,
            modelId=BedrockModelId,
            system_prompt=_system_prompt,
            messages=_messages,
        )

        if not generated_cloudformation_stack:
            return False, f"Bedrock call was unsuccessful"

        if put_generated_cloudformation(
            sessionId=sessionId, template=generated_cloudformation_stack
        ):
            return True, {"CloudformationTemplate": True}
        else:
            return False, f"Template storage unsuccessful"


#########################
##### Validate CFN #####
#######################


def validate_cloudformtaion(sessionId):
    """
    Validates the CloudFormation template stored in version vo (latest) in DynamoDB.

    Args:
        event (dict): The event data.

    Returns:
        dict: {"isValid": True/False, "error": Error Message}
    """
    try:
        cloudformationTemplate = get_generated_cloudformation(sessionId=sessionId)
    except Exception as ex:
        return False, ex

    validation_errors = str()
    try:
        response = cfn.validate_template(
            TemplateBody=cloudformationTemplate,
        )
    except Exception as ex:
        print(f"Cloudformation template invalid: {ex}")
        validation_errors = f"Cloudformation template invalid: {ex}"
        is_valid = False
    else:
        is_valid = True
        print("Cloudformation valid")

    if put_validity_cloudformation(
        sessionId=sessionId, template=cloudformationTemplate, is_valid=is_valid
    ):
        return True, {"isValid": is_valid, "error": str(validation_errors)}
    else:
        return False, f"Template storage unsuccessful"


##########################
##### Reiterate CFN #####
########################


def reiterate_cloudformation(sessionId):
    """
    Reiterates the CloudFormation template stored in version vo (latest) in DynamoDB. Stores the new generated template in DynamoDB.

    Args:
        event (dict): The event data.

    Returns:
        bool: Indicating if the template was generated successfully.
    """
    try:

        cloudformationTemplate = get_generated_cloudformation(sessionId=sessionId)

        documents = retrieve_yaml(
            sessionId=sessionId,
        )
        _system_prompt = sys_reiterateCloudFormationPrompt.SYS_REITERATE_CLOUDFORMATION_PROMPT
        _prompt = reiterateCloudFormationPrompt.REITERATE_CLOUDFORMATION_PROMPT.replace("{{cloudformationTemplate}}", cloudformationTemplate)

        message_document = [
            {
                "role": "user",
                "content": [
                    {
                        "text": f"""Take this example CloudFormation YAML code as a refernce <example{idx}></example{idx}>:
                            <example{idx}>
                                {document}
                            </example{idx}>
                            """,
                    }
                    for idx, document in enumerate(documents)
                ],
            }
        ]

        message_document[0]["content"].append(
            {
                "text": _prompt,
            },
        )
        _messages = message_document
    except Exception as ex:
        return False, ex
    else:
        # func, modelId, system_prompt, messages

        updated_cloudformation = backoff_mechanism(
            func=invoke_model,
            modelId=BedrockModelId,
            system_prompt=_system_prompt,
            messages=_messages,
        )
        if not updated_cloudformation:
            return False, f"Bedrock call was unsuccessful"

        if put_generated_cloudformation(
            sessionId=sessionId, template=updated_cloudformation
        ):
            return True, {"reiteratedCloudformationTemplate": True}
        else:
            return False, "Template storage unsuccessful"


#######################
##### Update CFN #####
#####################


def update_cloudformation(updateInstruction, sessionId):
    """
    Updates the CloudFormation template stored in version vo (latest) in DynamoDB. Stores the new generated template in DynamoDB.

    Args:
        event (dict): The event data.

    Returns:
        bool: Indicating if the template was generated successfully.
    """
    try:

        cloudformationTemplate = get_generated_cloudformation(sessionId=sessionId)

        documents = retrieve_yaml(sessionId=sessionId, query=None)

        _system_prompt = sys_updateInstructionPrompt.SYS_UPDATE_CLOUDFORMATION_PROMPT
        
        _prompt = updateInstructionPrompt.UPDATE_CLOUDFORMATION_PROMPT.replace("{{cloudformationTemplate}}", cloudformationTemplate).replace("{{updateInstruction}}", updateInstruction)
        
        message_document = [
            {
                "role": "user",
                "content": [
                    {
                        "text": f"""Take this example CloudFormation YAML code as a refernce <example{idx}></example{idx}>:
                            <example{idx}>
                                {document}
                            </example{idx}>
                            """,
                    }
                    for idx, document in enumerate(documents)
                ],
            }
        ]

        message_document[0]["content"].append(
            {
                "text": _prompt,
            },
        )
        _messages = message_document
    except Exception as ex:
        return False, ex
    else:

        # func, modelId, system_prompt, messages

        updated_cloudformation = backoff_mechanism(
            func=invoke_model,
            modelId=BedrockModelId,
            system_prompt=_system_prompt,
            messages=_messages,
        )
        if not updated_cloudformation:
            return False, "Bedrock call was unsuccessful"

        if put_generated_cloudformation(
            sessionId=sessionId, template=updated_cloudformation
        ):
            return True, {"updatedCloudformationTemplate": True}
        else:
            return False, "Template storage unsuccessful"


##########################
##### Resolve Error #####
########################


def resolve_cloudformation(cloudformationInstruction, sessionId):
    """
    Resolves the error message stored in version vo (latest) in DynamoDB. Stores the new generated template in DynamoDB.

    Args:
        event (dict): The event data.

    Returns:
        bool: Indicating if the template was generated successfully.
    """
    try:

        cloudformationTemplate = get_generated_cloudformation(sessionId=sessionId)

        documents = retrieve_yaml(sessionId=sessionId, query=None)
        _system_prompt = sys_resolveErrorPrompt.SYS_RESOLVE_CLOUDFORMATION_PROMPT

        _prompt = resolveErrorPrompt.RESOLVE_CLOUDFORMATION_PROMPT.replace("{{cloudformationTemplate}}", cloudformationTemplate).replace("{{cloudformationInstruction}}", cloudformationInstruction)

        message_document = [
            {
                "role": "user",
                "content": [
                    {
                        "text": f"""Take this example CloudFormation YAML code as a refernce <example{idx}></example{idx}>:
                            <example{idx}>
                                {document}
                            </example{idx}>
                            """,
                    }
                    for idx, document in enumerate(documents)
                ],
            }
        ]

        message_document[0]["content"].append(
            {
                "text": _prompt,
            },
        )
        _messages = message_document
    except Exception as ex:
        return False, ex
    else:
        # func, modelId, system_prompt, messages

        updated_cloudformation = backoff_mechanism(
            func=invoke_model,
            modelId=BedrockModelId,
            system_prompt=_system_prompt,
            messages=_messages,
        )
        if not updated_cloudformation:
            return False, "Bedrock call was unsuccessful"
        if put_generated_cloudformation(
            sessionId=sessionId, template=updated_cloudformation
        ):
            return True, {"updatedCloudformationTemplate": True}
        else:
            return False, "Template storage unsuccessful"


###########################
##### Lambda Handler #####
#########################


def lambda_handler(event, context):
    print(event)

    response_code = 200
    action_group = event["actionGroup"]
    api_path = event["apiPath"]
    http_method = event["httpMethod"]
    parameters = event.get("parameters", [])
    session_attributes = event.get("sessionAttributes", {})
    validate_counter = int(session_attributes.get("validate_counter", ""))

    architectureExplanation, updateInstruction, cloudformationInstruction = (
        None,
        None,
        None,
    )

    if validate_counter == 0 or validate_counter == 1:

        if api_path == "/generateCloudFormation":

            for param in parameters:
                if param["name"] == "architectureExplanation":
                    architectureExplanation = param["value"]

            if not architectureExplanation:
                valid, result = (
                    False,
                    "Missing mandatory parameter: architectureExplanation",
                )
            else:
                valid, result = generate_cloudformation(
                    architectureExplanation=architectureExplanation,
                    sessionId=event["sessionId"],
                )

        elif api_path == "/validateCloudFormation":
            validate_counter += 1

            valid, result = validate_cloudformtaion(sessionId=event["sessionId"])

        elif api_path == "/reiterateCloudFormation":

            valid, result = reiterate_cloudformation(
                sessionId=event["sessionId"],
            )

        elif api_path == "/updateCloudFormation":

            for param in parameters:
                if param["name"] == "updateInstruction":
                    updateInstruction = param["value"]

            if not updateInstruction:
                valid, result = False, "Missing mandatory parameter: updateInstruction"
            else:
                valid, result = update_cloudformation(
                    updateInstruction=updateInstruction,
                    sessionId=event["sessionId"],
                )
        elif api_path == "/resolveCloudFormation":
            for param in parameters:
                if param["name"] == "cloudformationInstruction":
                    cloudformationInstruction = param["value"]

            if not cloudformationInstruction:
                valid, result = (
                    False,
                    "Missing mandatory parameter: cloudformationInstruction",
                )
            else:
                valid, result = resolve_cloudformation(
                    cloudformationInstruction=cloudformationInstruction,
                    sessionId=event["sessionId"],
                )
        else:
            valid, result = False, f"Unrecognized api path: {action_group}::{api_path}"
    else:
        response_code = 423
        valid, result = (
            True,
            f"/validateCloudFormation has been called twice returning control",
        )

    if not valid:
        response_code = 404
        response_body = {
            "application/json": {
                "body": {
                    "error_message": f"Api path {action_group}::{api_path} returned an error: {result}"
                }
            }
        }
    else:
        response_body = {"application/json": {"body": result}}

    response = {
        "actionGroup": action_group,
        "apiPath": api_path,
        "httpMethod": http_method,
        "httpStatusCode": response_code,
        "responseBody": response_body,
        "sessionState": {
            "sessionAttributes": {"validate_counter": str(validate_counter)},
        },
    }

    api_response = {"messageVersion": "1.0", "response": response}
    return api_response
