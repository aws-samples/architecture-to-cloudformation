import streamlit as st
import base64
import src

st.set_page_config(
    page_title="AWS",
    page_icon="👋",
    layout="wide",
)

st.header("Architecture to CloudFormation")

# Using object notation

st.sidebar.header("Inference Parameters")
Temperature = st.sidebar.slider(
    "Temperature", min_value=0.0, max_value=1.0, step=0.1, value=0.0
)
Top_P = st.sidebar.slider("Top P", min_value=0.0, max_value=1.0, step=0.001, value=1.0)
Top_K = st.sidebar.slider("Top K", min_value=0, max_value=500, step=1, value=250)

bedrock = src.Model({"temperature": Temperature, "top_p": Top_P, "top_k": Top_K})

if st.button("Clear", type="secondary"):
    uploaded_file = None
    bedrock.clear_memory()
    bedrock.clear_explain()
    st.rerun()

uploaded_file = st.file_uploader(
    "Upload an Architecture diagram to generate AWS CloudFormation code",
    type=["jpeg", "png"],
    disabled= bool(bedrock.get_explain())
)

if uploaded_file is not None:

    image, explain = st.columns((5, 5))

    with image:
        st.image(uploaded_file.getvalue())

    with explain:

        if bedrock.get_explain():
            st.write(bedrock.get_explain())
        else:
            explain_placeholder = st.empty()
            bedrock.invoke_explain_model(
                uploaded_file, uploaded_file.type, explain_placeholder
            )

    if bedrock.check_memory():
        role = "assistant"
        for chat in bedrock.return_memory():
            content = chat.to_json()["kwargs"]["content"]
            with st.chat_message(role):
                st.markdown(content[0]["text"])

            role = "human" if role == "assistant" else "assistant"

    if not bedrock.check_memory():
        with st.chat_message("assistant"):
            code_placeholder = st.empty()

            bedrock.invoke_code_model(
                uploaded_file, uploaded_file.type, code_placeholder
            )

    if prompt := st.chat_input(
        "Give the bot instructions to update stack...",
    ):
        with st.chat_message("human"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if bedrock.check_memory():
                update_placeholder = st.empty()
                bedrock.invoke_update_model(prompt, update_placeholder)
