from botocore.config import Config
from boto3.session import Session

import streamlit as st


import uuid
import json


class BedrockAgent:
    """BedrockAgent class for invoking an Amazon Bedrock agents.

    This class provides a wrapper for invoking an AI agent hosted on Amazon Bedrock platform.

    Usage:

    agent = BedrockAgent(environmentName=environmentName)

    # The invoke_agent() method sends the input text to the agent and returnsthe agent's response text and trace information.
    response_text, trace_text = agent.invoke_agent(text, trace, instruction)

    # Get the current session id.
    session_id = agent.get_session_id()

    # Reset the session.
    agent.new_session()

    The class initializes session state on first run. It reuses the session for subsequent calls for continuity.
    """

    def __init__(self, environmentName) -> None:
        if "AGENT_RUNTIME_CLIENT" not in st.session_state:

            st.session_state["AGENT_RUNTIME_CLIENT"] = Session().client(
                "bedrock-agent-runtime",
                config=Config(read_timeout=600, connect_timeout=600),
            )

        if "SESSION_ID" not in st.session_state:
            st.session_state["SESSION_ID"] = str(uuid.uuid1())

        self.agent_id = (
            Session()
            .client("ssm")
            .get_parameter(
                Name=f"/streamlitapp/{environmentName}/AGENT_ID", WithDecryption=False
            )["Parameter"]["Value"]
        )
        self.agent_alias_id = (
            Session()
            .client("ssm")
            .get_parameter(
                Name=f"/streamlitapp/{environmentName}/AGENT_ALIAS_ID",
                WithDecryption=False,
            )["Parameter"]["Value"]
        )
        if "INVOCATION_ID" not in st.session_state:
            st.session_state["INVOCATION_ID"] = None

    def new_session(self):
        """
        Resets the session.
        """
        if st.session_state["INVOCATION_ID"]:
            st.session_state["AGENT_RUNTIME_CLIENT"].invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self.agent_alias_id,
                sessionId=st.session_state["SESSION_ID"],
                endSession=True,
                sessionState={
                    "invocationId": st.session_state["INVOCATION_ID"],
                    "sessionAttributes": {"validate_counter": "0"},
                },
            )
            del st.session_state["INVOCATION_ID"]
        st.session_state["SESSION_ID"] = str(uuid.uuid1())
        del st.session_state["AGENT_RUNTIME_CLIENT"]

    def get_session_id(self):
        """
        Returns the session id.
        """
        return st.session_state["SESSION_ID"]

    def invoke_agent(self, text, trace, instruction):
        """
        Invokes the agent and returns the response text and trace information.

        Args:
            text (str): The input text.
            trace  (instanceof st.empty): Placeholder to stream the trace.
            instruction (str): The instruction to send to the agent. Can be one of ("validate", "generate", "update")

        Returns:
            tuple: The response text and trace information.
        """
        if instruction not in ("validate", "generate", "update"):
            raise ValueError("Instructions should be validate, generate, or update")

        if instruction == "validate":
            inputText = f"""
                    Validate the AWS CloudFormation template.
                    <thought>
                        To validate a CloudFormation template, I will follow these steps:
                            1. Invoke the validateCloudFormation function to validate the template.
                            2. If there are any errors, invoke the resolveCloudFormation function to resolve them and generate a new template.
                            3. Invoke the validateCloudFormation function to validate the new template.
                            4. Return control back to user even if there are errors. 
                    </thought>
                """
        elif instruction == "generate":
            inputText = f"""
            Create clouformation code of following explain <explain>{text}</explain>
            <thought>
                To generate a CloudFormation template for the given architecture explanation, I will follow these steps:
                    1. Invoke the generateCloudFormation function with the provided architecture explanation to get an initial CloudFormation template.
                    2. Invoke the reiterateCloudFormation function to optimize the template by incorporating AWS best practices.
                    3. Invoke the validateCloudFormation function to validate the optimized template.
                    4. If there are any errors, invoke the resolveCloudFormation function to resolve them and generate a new template.
                    5. Invoke the validateCloudFormation function to validate the new template.
                    6. Return control back to user even if there are errors. 
            </thought>
            """
        elif instruction == "update":
            inputText = f"""
            Update the AWS Cloudformation template based on following update instruction: <update>{text}</update>
            <thought>
                To update a CloudFormation template for the given update instruction, I will follow these steps:
                    1. Invoke the updateCloudFormation function with the provided architecture explanation to get an initial CloudFormation template.
                    2. Invoke the reiterateCloudFormation function to optimize the template by incorporating AWS best practices.
                    3. Invoke the validateCloudFormation function to validate the optimized template.
                    4. If there are any errors, invoke the resolveCloudFormation function to resolve them and generate a new template.
                    5. Invoke the validateCloudFormation function to validate the new template.
                    6. Return control back to user even if there are errors. 
            </thought>
            """

        response_text = str()
        trace_text = list()
        step = 0

        response = st.session_state["AGENT_RUNTIME_CLIENT"].invoke_agent(
            inputText=inputText,
            agentId=self.agent_id,
            agentAliasId=self.agent_alias_id,
            sessionId=st.session_state["SESSION_ID"],
            enableTrace=True,
            sessionState={
                "sessionAttributes": {"validate_counter": "0"},
            },
        )
        try:
            for event in response["completion"]:
                if (
                    "returnControl" in event
                    and "invocationId" in event["returnControl"]
                ):
                    st.session_state["INVOCATION_ID"] = response["completion"][
                        "returnControl"
                    ]["invocationId"]

                if "chunk" in event:

                    data = event["chunk"]["bytes"]
                    response_text = data.decode("utf8")

                elif "trace" in event:

                    trace_obj = event["trace"]["trace"]

                    if "orchestrationTrace" in trace_obj:

                        trace_dump = json.dumps(
                            trace_obj["orchestrationTrace"], indent=3
                        )

                        if "rationale" in trace_obj["orchestrationTrace"]:

                            trace_text.append(
                                {
                                    "heading": "Rationale",
                                    "category": "rationale",
                                    "content": trace_obj["orchestrationTrace"][
                                        "rationale"
                                    ]["text"],
                                }
                            )
                            if trace:
                                with trace:
                                    with st.expander(f"Rationale"):
                                        st.write(
                                            trace_obj["orchestrationTrace"][
                                                "rationale"
                                            ]["text"]
                                        )

                        elif (
                            "modelInvocationInput"
                            not in trace_obj["orchestrationTrace"]
                        ):

                            tools = json.loads(trace_dump)
                            if "invocationInput" in tools:
                                tool_used = tools["invocationInput"][
                                    "actionGroupInvocationInput"
                                ]["apiPath"]
                                trace_text.append(
                                    {
                                        "heading": f"Tool call {tool_used}",
                                        "category": "invocationInput",
                                        "content": trace_dump,
                                    }
                                )
                                if trace:
                                    with trace:
                                        with st.expander(f"Tool call {tool_used}"):
                                            st.code(trace_dump)

                            if "observation" in tools:
                                tool_used = trace_text[-1]["heading"].split()[-1]
                                trace_text.append(
                                    {
                                        "heading": f"Tool output {tool_used}",
                                        "category": "observation",
                                        "content": trace_dump,
                                    }
                                )
                                if trace:
                                    with trace:
                                        with st.expander(f"Tool output {tool_used}"):
                                            st.code(trace_dump)

                    elif "failureTrace" in trace_obj:
                        trace_text.append(
                            {
                                "heading": "Failure",
                                "category": "failureTrace",
                                "content": trace_dump,
                            }
                        )
                        if trace:
                            with trace:
                                with st.expander(f"Failure"):
                                    st.write(trace_dump)

        except Exception as e:
            trace_text += str(e)
            if trace:
                trace.markdown(str(e))
            raise Exception("unexpected event.", e)

        return response_text, trace_text
