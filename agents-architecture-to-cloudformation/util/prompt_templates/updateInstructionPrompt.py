UPDATE_CLOUDFORMATION_PROMPT = """
I need your assistance in updating AWS CloudFormation template. Please review the following:

<cloudformation>
{{cloudformationTemplate}}
</cloudformation>

<update>
{{updateInstruction}}
</update>
        
Also make sure description consists "This template is not production ready and should only be used for inspiration".

Once you have completed the updates, you will output only the revised CloudFormation YAML template without ```yaml ```. Skip the preamble.Think step-by-step. 
"""