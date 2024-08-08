REITERATE_CLOUDFORMATION_PROMPT = """
Reiterate the CloudFormation template. Also make sure description consists "This template is not production ready and should only be used for inspiration".
<cloudformation>
    {{cloudformationTemplate}}
</cloudformation>

Do not return examples or explaination, only return the generated CloudFormation YAML template without ```yaml ```. Skip the preamble. Think step-by-step. 
"""