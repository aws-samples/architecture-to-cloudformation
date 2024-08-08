import streamlit as st
from code_editor import code_editor

from argparse import ArgumentParser

from util.invoke import Bedrock, BedrockAgent, KnowledgeBase
from util.assets import download_button, read_image, download_cfn

parser = ArgumentParser()
parser.add_argument("--environmentName", type=str, default=None)
parser.add_argument("--GitURL", type=str, default=None)

args = parser.parse_args()

environmentName = args.environmentName
GitURL = args.GitURL

st.set_page_config(
    page_title="AWS",
    page_icon="👋",
    layout="wide",
)

st.sidebar.header("Inference Parameters for Vision")
Temperature = st.sidebar.slider(
    "Temperature", min_value=0.0, max_value=1.0, step=0.1, value=0.0
)
Top_P = st.sidebar.slider("Top P", min_value=0.0, max_value=1.0, step=0.001, value=1.0)
Top_K = st.sidebar.slider("Top K", min_value=0, max_value=500, step=1, value=250)

bedrock = Bedrock(
    inference_params={"temperature": Temperature, "top_p": Top_P, "top_k": Top_K}
)
agent = BedrockAgent(environmentName=environmentName)
knowledgebase = KnowledgeBase(environmentName=environmentName)

st.sidebar.subheader("Session ID")
st.sidebar.code(agent.get_session_id())


def upload_new_template(template, chat_history_index):
    knowledgebase.put_generated_cloudformation(
        sessionId=agent.get_session_id(), template=template
    )

    st.session_state["chat_history"][chat_history_index]["prompt"] = (
        "```yaml" + template
    )

    st.session_state["chat_history"][chat_history_index]["is_valid"] = None


warning = st.container()

st.title("Architecture to CloudFormation")

st.subheader(":grey[Amazon Bedrock Agents]")

heading_button_left, heading_button_center, heading_button_right = st.columns((1, 1, 8))

with heading_button_left:
    if st.button("Clear Session", type="primary"):
        if "chat_history" in st.session_state:
            del st.session_state["chat_history"]
        if "explain" in st.session_state:
            del st.session_state["explain"]
        if "uploaded_file" in st.session_state:
            del st.session_state["uploaded_file"]

        if "metadata_uri" in st.session_state:
            del st.session_state["metadata_uri"]

        if "user_edit_done" in st.session_state:
            del st.session_state["user_edit_done"]

        agent.new_session()
        knowledgebase.new_session()
        st.rerun()


with heading_button_center:
    if st.button("Validate"):
        if "chat_history" not in st.session_state:
            with warning:
                st.warning(
                    "Cannot validate, first upload architecture diagram and invoke agent!",
                    icon="⚠️",
                )
        else:
            st.session_state["chat_history"].append(
                {
                    "role": "human",
                    "prompt": "Validate the the most recently generated AWS CloudFormation template.",
                }
            )
            _, trace_text = agent.invoke_agent(
                text=st.session_state["explain"], trace=None, instruction="validate"
            )
            response_text = knowledgebase.get_generated_cloudformation(
                sessionId=agent.get_session_id()
            )

            is_valid = knowledgebase.get_generated_cloudformation(
                sessionId=agent.get_session_id(), key="is_valid"
            )

            st.session_state["chat_history"].append(
                {
                    "role": "assistant",
                    "prompt": "```yaml" + response_text,
                    "trace": trace_text,
                    "is_valid": is_valid,
                }
            )

with heading_button_right:
    st.link_button("_Github_ :sunglasses:", GitURL)

disable_file_uploader = False


def change_availability(disable_file_uploader):
    disable_file_uploader = True


st.session_state["uploaded_file"] = st.file_uploader(
    "Upload an Architecture diagram to generate AWS CloudFormation code",
    type=["jpeg", "png"],
    disabled="uploaded_file" in st.session_state
    and st.session_state["uploaded_file"] is not None,
)

# file is uploaded
if st.session_state["uploaded_file"] is not None:
    image_col, explain_col = st.columns((5, 5))

    with image_col:
        st.image(st.session_state["uploaded_file"].getvalue())

    with explain_col:
        explain_placeholder = st.empty()

    if "explain" not in st.session_state:
        st.session_state["explain"] = bedrock.invoke_explain_model(
            st.session_state["uploaded_file"],
            st.session_state["uploaded_file"].type.replace("image/", ""),
            explain_placeholder,
        )
        st.rerun()
    else:
        if "user_edit_done" not in st.session_state:
            with explain_placeholder:
                st.session_state["explain"] = st.text_area(
                    label="Step-by-step explain",
                    value=st.session_state["explain"],
                    height=500,
                    key="step-by-step-explain-edited",
                )
            if st.button("InvokeAgent", type="primary"):
                st.session_state["user_edit_done"] = True
                st.rerun()
        else:
            with explain_placeholder:
                st.text_area(
                    label="Step-by-step explain",
                    value=st.session_state["explain"],
                    height=500,
                    key="step-by-step-explain-edited",
                    disabled=True,
                )


if "user_edit_done" in st.session_state and "explain" in st.session_state:
    if "chat_history" in st.session_state:

        for index, chat in enumerate(st.session_state["chat_history"]):
            with st.chat_message(chat["role"]):
                if chat["role"] == "assistant":
                    # col1, col2 = st.columns((7, 3))
                    # with col2:
                    if chat["is_valid"]:
                        st.success("CloudFormation template is valid!")
                    elif chat["is_valid"] is False:
                        st.error("CloudFormation template is not valid!")
                    else:
                        st.warning(
                            "Unable to determine if CloudFormation template is valid or not!"
                        )
                    for trace in chat["trace"]:
                        with st.expander(trace["heading"]):
                            if (
                                "rationale" in trace["category"]
                                or "failureTrace" in trace["category"]
                            ):
                                st.write(trace["content"])
                            else:
                                st.code(trace["content"])

                    if index == len(st.session_state["chat_history"]) - 1:

                        # with col1:
                        custom_btns = [
                            {
                                "name": "Copy",
                                "feather": "Copy",
                                "hasText": True,
                                "alwaysOn": True,
                                "commands": [
                                    "copyAll",
                                    [
                                        "infoMessage",
                                        {
                                            "text": "Copied to clipboard!",
                                            "timeout": 2500,
                                            "classToggle": "show",
                                        },
                                    ],
                                ],
                                "style": {"top": "0.46rem", "right": "0.4rem"},
                            },
                            {
                                "name": "Submit",
                                "feather": "Play",
                                "primary": True,
                                "hasText": True,
                                "showWithIcon": True,
                                "commands": ["submit"],
                                "style": {"bottom": "0.44rem", "right": "0.4rem"},
                            },
                        ]

                        response_dict = code_editor(
                            chat["prompt"].replace("```yaml", ""),
                            # focus=True,
                            theme="dark",
                            buttons=custom_btns,
                            key=index,
                            options={"wrap": False},
                        )

                        if (
                            response_dict["type"] == "submit"
                            and len(response_dict["text"]) != 0
                        ):
                            upload_new_template(
                                template=response_dict["text"],
                                chat_history_index=index,
                            )
                    else:
                        # with col1:
                        custom_btns = [
                            {
                                "name": "Copy",
                                "feather": "Copy",
                                "hasText": True,
                                "alwaysOn": True,
                                "commands": [
                                    "copyAll",
                                    [
                                        "infoMessage",
                                        {
                                            "text": "Copied to clipboard!",
                                            "timeout": 2500,
                                            "classToggle": "show",
                                        },
                                    ],
                                ],
                                # "style": {"top": "0.46rem", "right": "0.4rem"},
                            }
                        ]

                        response_dict = code_editor(
                            chat["prompt"].replace("```yaml", ""),
                            # focus=True,
                            theme="light",
                            buttons=custom_btns,
                            key=index,
                            options={"wrap": False},
                        )

                        # col1.markdown(chat["prompt"], unsafe_allow_html=True)

                else:
                    st.markdown(chat["prompt"])

    if "chat_history" not in st.session_state or not st.session_state["chat_history"]:

        st.session_state["chat_history"] = list()

        with st.chat_message("assistant"):
            # col1, col2 = st.columns((5, 5))
            col2 = st.container()

            _, trace_text = agent.invoke_agent(
                text=st.session_state["explain"], trace=col2, instruction="generate"
            )
            response_text = knowledgebase.get_generated_cloudformation(
                sessionId=agent.get_session_id()
            )

            is_valid = knowledgebase.get_generated_cloudformation(
                sessionId=agent.get_session_id(), key="is_valid"
            )

            st.session_state["chat_history"].append(
                {
                    "role": "assistant",
                    "prompt": "```yaml" + response_text,
                    "trace": trace_text,
                    "is_valid": is_valid,
                }
            )
            st.rerun()
    if "chat_history" in st.session_state:
        if prompt := st.chat_input("Give the bot update instructions..."):
            st.session_state["chat_history"].append({"role": "human", "prompt": prompt})

            with st.chat_message("human"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                # col1, col2 = st.columns((5, 5))
                col2 = st.container()

                _, trace_text = agent.invoke_agent(
                    text=prompt, trace=col2, instruction="update"
                )
                response_text = knowledgebase.get_generated_cloudformation(
                    sessionId=agent.get_session_id()
                )

                is_valid = knowledgebase.get_generated_cloudformation(
                    sessionId=agent.get_session_id(), key="is_valid"
                )

                st.session_state["chat_history"].append(
                    {
                        "role": "assistant",
                        "prompt": "```yaml" + response_text,
                        "trace": trace_text,
                        "is_valid": is_valid,
                    }
                )

                st.rerun()

    st.session_state["metadata_uri"] = knowledgebase.retrieve_metadata(
        query=st.session_state["explain"], sessionId=agent.get_session_id()
    )
    with st.sidebar:
        st.header("Knowledge Base")
        for uri in st.session_state["metadata_uri"]:
            with st.container(border=True):
                st.image(read_image(uri["architecture_image"]), width=300)
                download_button_str = download_button(
                    button_text="Download",
                    object_to_download=download_cfn(uri["cfn_stack"]),
                    download_filename="data.yaml",
                )
                st.markdown(download_button_str, unsafe_allow_html=True)
