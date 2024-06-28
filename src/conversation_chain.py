import streamlit as st

from jinja2 import Environment, select_autoescape, FileSystemLoader

from botocore.exceptions import EventStreamError
from boto3.session import Session

import base64
import time
import random
import os


def invoke_model(
    modelId, inference_params, messages, system_prompt, data_placeholder=None
):
    bedrock = Session().client(
        service_name="bedrock-runtime",
    )
    result = str()
    response = bedrock.converse_stream(
        modelId=modelId,
        messages=messages,
        system=[{"text": system_prompt}],
        inferenceConfig={
            "maxTokens": 4000,
            "temperature": inference_params["temperature"],
            "topP": inference_params["top_p"],
        },
        additionalModelRequestFields={"top_k": inference_params["top_k"]},
    )

    stream = response.get("stream")
    if stream:
        for event in stream:

            if "contentBlockDelta" in event:
                result += event["contentBlockDelta"]["delta"]["text"]
                with data_placeholder.container():
                    st.write(result)

    return result


def backoff_mechanism(
    func, modelId, inference_params, messages, system_prompt, data_placeholder=None
):
    MAX_RETRIES = 5  # Maximum number of retries
    INITIAL_DELAY = 1  # Initial delay in seconds
    MAX_DELAY = 60  # Maximum delay in second

    delay = INITIAL_DELAY
    retries = 0

    while retries < MAX_RETRIES:
        try:
            return func(
                modelId=modelId,
                inference_params=inference_params,
                messages=messages,
                system_prompt=system_prompt,
                data_placeholder=data_placeholder,
            )
        except EventStreamError as e:
            print(f"Retry {retries + 1}/{MAX_RETRIES}: {e}")
            time.sleep(delay + random.uniform(0, 1))  # Add a random jitter
            delay = min(delay * 2, MAX_DELAY)
            retries += 1


class ConvoChain:
    def __init__(self) -> None:

        jinja = Environment(
            loader=FileSystemLoader(f"{os.path.dirname(__file__)}/prompt_templates"),
            autoescape=select_autoescape(
                enabled_extensions=("jinja"),
                disabled_extensions=("txt",),
                default_for_string=True,
                default=True,
            ),
        )

        self._explain_prompt = jinja.get_template("explain_prompt.txt.jinja")

        self._code_prompt = jinja.get_template("code_prompt.txt.jinja")

        self._sys_explain_prompt = jinja.get_template("sys_explain_prompt.txt.jinja")

        self._sys_code_prompt = jinja.get_template("sys_code_prompt.txt.jinja")

        self._sys_update_prompt = jinja.get_template("sys_update_prompt.txt.jinja")

    def get_explain_messages(self, image, image_type):
        messages = list()

        messages.append(
            {
                "role": "user",
                "content": [
                    {"text": self._explain_prompt.render()},
                    {
                        "image": {
                            "format": image_type,
                            "source": {
                                "bytes": image.getvalue(),
                            },
                        }
                    },
                ],
            }
        )

        return self._sys_explain_prompt.render(), messages

    def read_examples(self, file_path):
        with open(file_path, "r") as template_file:
            return template_file.read()

    def get_code_messages(self, explain):
        messages = list()

        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "text": f"""
                    Take this example CloudFormation YAML code as reference:
                        <example1>
                            {self.read_examples("util/examples/example1.yaml")}
                        </example1>      
                    """,
                    },
                    {
                        "text": f"""
                    Take this example CloudFormation YAML code as reference:
                        <example2>
                            {self.read_examples("util/examples/example2.yaml")}
                        </example2>
                    """,
                    },
                    {
                        "text": f"""
                    Take this example CloudFormation YAML code as reference:
                        <example3>
                            {self.read_examples("util/examples/example3.yaml")}
                        </example3>
                    """,
                    },
                    {"text": self._code_prompt.render(explain=explain)},
                ],
            }
        )

        return self._sys_code_prompt.render(), messages

    def get_update_messages(self, initial_cfn_code, explain):
        messages = list()

        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "text": f"""
                    Take this example CloudFormation YAML code as a refernce <example1></example1>:
                        <example1>
                            {self.read_examples("util/examples/example1.yaml")}
                        </example1>      
                    """,
                    },
                    {
                        "text": f"""
                    Take this example CloudFormation YAML code as a refernce <example2></example2>:
                        <example2>
                            {self.read_examples("util/examples/example2.yaml")}
                        </example2>
                    """,
                    },
                    {
                        "text": f"""
                    Take this example CloudFormation YAML code as a refernce <example3></example3>:
                        <example3>
                            {self.read_examples("util/examples/example3.yaml")}
                        </example3>
                    """,
                    },
                    {
                        "text": f"Step-by-step explaination of Architecture Diagram \n <explain> {explain} </explain>",
                    },
                ],
            }
        )

        messages.append(
            {
                "role": "assistant",
                "content": [
                    {"text": initial_cfn_code},
                ],
            }
        )

        return self._sys_update_prompt.render(), messages
