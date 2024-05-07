from src.conversation_chain import ConvoChain, backoff_mechanism, invoke_model
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage


class Model:
    def __init__(self, inference_params) -> None:
        self._chain = ConvoChain(inference_params=inference_params)

    def invoke_explain_model(self, image, image_type, data_placeholder):

        explain_model = self._chain.get_llm()

        messages = self._chain.get_explain_messages(image, image_type)

        # print("###### Explain ######")
        # print(messages)
        # print("###### Explain ######")
        
        explain = backoff_mechanism(
            func=invoke_model,
            model=explain_model,
            messages=messages,
            data_placeholder=data_placeholder,
        )

        if "explain" in st.session_state:
            del st.session_state["explain"]
        else:
            st.session_state["explain"] = explain

    def invoke_code_model(self, image, image_type, data_placeholder):

        if "explain" not in st.session_state:
            raise BaseException("explain not found")

        model = self._chain.get_llm()

        messages = self._chain.get_code_messages(st.session_state["explain"])
        
        # print("###### code ######")
        # print(messages)
        # print("###### code ######")
        
        initial_cfn_code = backoff_mechanism(
            func=invoke_model,
            model=model,
            messages=messages,
            data_placeholder=data_placeholder,
        )

        if not self.check_memory():
            st.session_state["memory"] = self._chain.get_update_messages(
                initial_cfn_code, st.session_state["explain"]
            )

    def invoke_update_model(self, update_instructions, data_placeholder):

        model = self._chain.get_llm()

        st.session_state["memory"].append(
            HumanMessage([{"type": "text", "text": update_instructions}])
        )
        
        # print("###### update ######")
        # print( st.session_state["memory"])
        # print("###### update ######")

        cfn_code = backoff_mechanism(
            func=invoke_model,
            model=model,
            messages=st.session_state["memory"],
            data_placeholder=data_placeholder,
        )

        st.session_state["memory"].append(
            AIMessage([{"type": "text", "text": cfn_code}])
        )

    def clear_memory(self):
        if self.check_memory():
            del st.session_state["memory"]

    def check_memory(self):
        if "memory" in st.session_state:
            return True
        else:
            return False

    def return_memory(self):
        return st.session_state["memory"][2:]

    def get_explain(self):
        if "explain" in st.session_state:
            return st.session_state["explain"]

        return False

    def clear_explain(self):
        if self.get_explain():
            del st.session_state["explain"]