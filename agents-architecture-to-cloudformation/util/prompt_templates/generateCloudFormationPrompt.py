GENERATE_CLOUDFORMATION_PROMPT = """
Create CLoudFormation code only for AWS Servies present in <explain></explain>
            
<explain>
{{architectureExplanation}}
</explain>

- Mimic the practices of example CloudFormation templates given between <example></example> XML tags.
- Use AWS CloudFormaton Pseudo parameters where necessary.
- Use structure of example templates.
- Add into description "This template is not production ready and should only be used for inspiration"

Do not return examples or explaination, only return the generated CloudFormation YAML template without ```yaml ```. Skip the preamble. Think step-by-step.
"""