CODE_PROMPT ="""
Create CLoudFormation code only for AWS Servies present in <explain></explain>

<explain>
{{ explain }}
</explain>

Mimic the practices of example CloudFormation templates.

- Use AWS CloudFormaton Pseudo parameters where necessary.
- Add into description "This template is not production ready and should only be used for inspiration"
Do not return examples or explaination, only return the generated CloudFormation YAML template encapsulated between triple backticks (``` ```). Skip the preamble. Think step-by-step.
"""