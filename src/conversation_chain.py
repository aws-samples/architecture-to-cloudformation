from langchain_community.chat_models import BedrockChat
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import PromptTemplate

from botocore.exceptions import EventStreamError
from boto3.session import Session

import streamlit as st

import base64
import time
import random


def invoke_model(model, messages, data_placeholder=None):

    cfn_code = str()
    for chunk in model.stream(messages):
        cfn_code += chunk.content
        with data_placeholder.container():
            st.write(cfn_code)

    return cfn_code


def backoff_mechanism(func, model, messages, data_placeholder=None):
    MAX_RETRIES = 5  # Maximum number of retries
    INITIAL_DELAY = 1  # Initial delay in seconds
    MAX_DELAY = 60  # Maximum delay in second

    delay = INITIAL_DELAY
    retries = 0

    while retries < MAX_RETRIES:
        try:
            return func(model, messages, data_placeholder)
        except EventStreamError as e:
            print(f"Retry {retries + 1}/{MAX_RETRIES}: {e}")
            time.sleep(delay + random.uniform(0, 1))  # Add a random jitter
            delay = min(delay * 2, MAX_DELAY)
            retries += 1


class ConvoChain:
    def __init__(self, inference_params) -> None:
        self._inference_params = inference_params
        
        self._explain_prompt = """
            You are an AWS Certified Solutions Architect with extensive experience in interpreting and explaining AWS Architecture diagrams. Given an architecture diagram as input, your task is to provide a detailed, step-by-step description of the components and their interactions within the architecture.

            When describing the architecture, follow these guidelines:

            1. Identify the main components and services depicted in the diagram.
            2. Explain the flow of data and requests through the architecture, starting from the client or user interface and tracing the path through various components.
            3. Describe the purpose and role of each component in the architecture, highlighting its responsibilities and how it contributes to the overall system.

            """
        
        self._code_prompt = PromptTemplate.from_template(
            """
            
            Create CLoudFormation code only for AWS Servies present in <explain></explain>
            <explain>
            {explain}
            </explain>
            
            Mimic the practices of example CloudFormation templates.
            
            - Use AWS CloudFormaton Pseudo parameters where necessary.
            
            Do not return examples, only the generated CloudFormation YAML encapsulated between triple backticks (``` ```)
            """
        )

        self._sys_explain_prompt = "Your goal is to provide a concise and easily understandable step-by-step explaination of the AWS Architecture diagram. Skip the preamble."
        
        self._sys_code_prompt = """
            You are an expert AWS CloudFormation developer. Your task is to convert instuctions to valid CloudFormation template in YAML format.
            Example CloudFormation YAML code is given in <example></example> XML tags to understand best practices. 
            Accept step-by-step explaination of the AWS Architecture encapsulated between <explain></explain> XML tags and generate its CloudFormation code. 
            Use AWS CloudFormaton Pseudo parameters where necessary.
        """
        
        self._sys_update_prompt = """
            You are an expert AWS CloudFormation developer tasked with updating CloudFormation code given in YAML format.

            1. You will be provided with an explaination of architecture diagram in <explain></explain> and the associated CloudFormation YAML code. 
            2. You will receive update instructions from the user. Based on these instructions, you will make the necessary updates to the CloudFormation YAML code.
            3. Please note that you should not make any changes to the code until you receive specific instructions from the user. Your role is to accurately interpret the user's requirements and modify the CloudFormation YAML code accordingly.
            
            Once you have completed the updates, you will output the revised CloudFormation YAML code, enclosing it between triple backticks (``` ```). Skip the preamble.
            """
        
    def get_explain_messages(self, image, image_type):
        human_message = [
            {"type": "text", "text": self._explain_prompt},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image_type,
                    "data": base64.b64encode(image.getvalue()).decode("utf-8"),
                },
            },
        ]

        return [
            SystemMessage(
                content=self._sys_explain_prompt
            ),
            HumanMessage(content=human_message),
        ]
        
    def read_examples(self, file_path):
        with open(file_path, "r") as template_file:
            return template_file.read()
        
    def get_code_messages(self, explain):

        human_message = [
            {
                "type": "text",
                "text": f"""
            Take this example CloudFormation YAML code as reference:
                <example1>
                    {self.read_examples("util/examples/example1.yaml")}
                </example1>      
            """,
            },
            {
                "type": "text",
                "text": f"""
            Take this example CloudFormation YAML code as reference:
                <example2>
                    {self.read_examples("util/examples/example2.yaml")}
                </example2>
            """,
            },
            {
                "type": "text",
                "text": f"""
            Take this example CloudFormation YAML code as reference:
                <example3>
                    {self.read_examples("util/examples/example3.yaml")}
                </example3>
             """,
            },
            {"type": "text", "text": self._code_prompt.format(explain=explain)},
        ]
        return [
            SystemMessage(
                content=self._sys_code_prompt
            ),
            HumanMessage(content=human_message),
        ]

    def get_update_messages(self, initial_cfn_code, explain):

        human_message = [
            {
                "type": "text",
                "text": f"""
            Take this example CloudFormation YAML code as a refernce <example1></example1>:
                <example1>
                    {self.read_examples("util/examples/example1.yaml")}
                </example1>      
            """,
            },
            {
                "type": "text",
                "text": f"""
            Take this example CloudFormation YAML code as a refernce <example2></example2>:
                <example2>
                    {self.read_examples("util/examples/example2.yaml")}
                </example2>
            """,
            },
            {
                "type": "text",
                "text": f"""
            Take this example CloudFormation YAML code as a refernce <example3></example3>:
                <example3>
                    {self.read_examples("util/examples/example3.yaml")}
                </example3>
             """,
            },
            {
                "type": "text",
                "text": f"Step-by-step explaination of Architecture Diagram \n <explain> {explain} </explain>",
            },
        ]

        ai_message = [
            {"type": "text", "text": initial_cfn_code},
        ]

        return [
            SystemMessage(content=self._sys_update_prompt),
            HumanMessage(content=human_message),
            AIMessage(content=ai_message),
        ]

    def get_llm(self, streaming=True):
        model_kwargs = {
            "max_tokens": 4096,
            "temperature": self._inference_params["temperature"],
            "top_k": self._inference_params["top_k"],
            "top_p": self._inference_params["top_p"],
            "stop_sequences": ["\n\nHuman:"],
        }

        return BedrockChat(
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            model_kwargs=model_kwargs,
            client=Session().client("bedrock-runtime"),
            streaming=streaming,
        )
