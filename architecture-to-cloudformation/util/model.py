import streamlit as st

from util.conversation_chain import ConvoChain, backoff_mechanism, invoke_model

import copy

class Model:
    def __init__(self, inference_params, modelId) -> None:
        self._chain = ConvoChain()
        self._inference_params = inference_params
        self._modelId = modelId

    def invoke_explain_model(self, image, image_type, data_placeholder):

        system_prompt, messages = self._chain.get_explain_messages(image, image_type)

        # print("###### Explain ######")
        # print(messages)
        # print("###### Explain ######")

        explain = backoff_mechanism(
            func=invoke_model,
            modelId=self._modelId,
            inference_params=self._inference_params,
            messages=messages,
            system_prompt=system_prompt,
            data_placeholder=data_placeholder,
        )

        if "explain" in st.session_state:
            del st.session_state["explain"]
        else:
            st.session_state["explain"] = explain

    def invoke_code_model(self, data_placeholder):

        if "explain" not in st.session_state:
            raise BaseException("explain not found")

        system_prompt, messages = self._chain.get_code_messages(
            st.session_state["explain"]
        )

        initial_cfn_code = backoff_mechanism(
            func=invoke_model,
            modelId=self._modelId,
            inference_params=self._inference_params,
            messages=messages,
            system_prompt=system_prompt,
            data_placeholder=data_placeholder,
        )

        if not self.check_memory():
            st.session_state["system_prompt"], st.session_state["messages"] = (
                self._chain.get_update_messages(
                    initial_cfn_code, st.session_state["explain"]
                )
            )

    def invoke_update_model(self, update_instructions, data_placeholder):

        # model = self._chain.get_llm()

        messages = copy.deepcopy(st.session_state["messages"])
        
        messages.append(
            {"role": "user", "content": [{"text": update_instructions + "\n\n" + "Do not return examples or explaination, only return the generated CloudFormation YAML template encapsulated between triple backticks (``` ```). Skip the preamble. Think step-by-step."}]}
        )
        st.session_state["messages"].append(
            {"role": "user", "content": [{"text": update_instructions}]}
        )

        # print("###### update ######")
        # print( st.session_state["memory"])
        # print("###### update ######")

        cfn_code = backoff_mechanism(
            func=invoke_model,
            modelId=self._modelId,
            inference_params=self._inference_params,
            messages=messages,
            system_prompt=st.session_state["system_prompt"],
            data_placeholder=data_placeholder,
        )

        st.session_state["messages"].append(
            {"role": "assistant", "content": [{"text": cfn_code}]}
        )

    def clear_memory(self):
        if self.check_memory():
            del st.session_state["messages"]
            del st.session_state["system_prompt"]

    def check_memory(self):
        if "messages" in st.session_state or "system_prompt" in st.session_state:
            return True
        else:
            return False

    def return_memory(self):
        return st.session_state["messages"][1:]

    def get_explain(self):
        if "explain" in st.session_state:
            return st.session_state["explain"]

        return False

    def clear_explain(self):
        if self.get_explain():
            del st.session_state["explain"]
