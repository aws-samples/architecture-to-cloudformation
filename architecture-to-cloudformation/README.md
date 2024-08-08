# <center> Architecture to AWS CloudFormation code using Anthropic Claude 3 model family's vision capabilities on Amazon Bedrock </center> 

## Architecture

![architecture](/architecture-to-cloudformation/artifact/architecture.png)

0. Developer manually deploys [development.yaml](/architecture-to-cloudformation/development.yaml) stack to host Streamlit applicaiton on AWS Fargate. 
1. User uploads an architecture diagram on Streamlit app. This triggers Amazon Bedrock API to generate step-by-step explanation of the given architecture diagram.
2. Anthropic Claude 3 Sonnet model is invoked using step-by-step explanation and few shot learning examples to generate initial AWS CloudFormation code.
3. User provides update instruction, which is used to update the initial AWS CloudFormation code.

> [!NOTE]  
> Steps 1 and 2 are run only once when architecture diagram is uploaded. To trigger changes to the AWS CloudFormation code (step 3) provide update insturctions from StreamlitApp

## Prerequisite

An AWS Account, to deploy the infrastructure. You can find more instructions to create your 
account [here](https://aws.amazon.com/free).


> [!IMPORTANT]  
> To access a foundation model, the user must request access through the console. Follow the instructions documented [here](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html).

## Deploy VPC Infrastructure (Optional)

Optionally, you can deploy the Virtual Private Cloud (VPC) infrastructure using the provided [infrastructure.yaml](/infrastructure.yaml) file, or utilize the default VPC. The required infrastructure components, including Amazon CloudFront, an Application Load Balancer, and Amazon Elastic Container Service (ECS) on AWS Fargate instances, will be deployed within the chosen VPC environment. 

> [!Note]  
> Wait for `infrastructure.yaml` to be in CREATE_COMPLETE state before moving forward. Make sure to use the same region for both `infrastructure.yaml` and `development.yaml` stacks. 

|   Region   | infrastructure.yaml |
| ---------- | ----------------- |
| us-east-1  | [![launch-stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=ArchToCloudformationInfra&templateURL=https://ws-assets-prod-iad-r-iad-ed304a55c2ca1aee.s3.us-east-1.amazonaws.com/0a9f7588-a2c4-4484-b051-6658ce32605c/A2C/infrastructure.yaml)|
| us-west-2  | [![launch-stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?region=us-west-2#/stacks/new?stackName=ArchToCloudformationInfra&templateURL=https://ws-assets-prod-iad-r-pdx-f3b3f9f1a7d6a3d0.s3.us-west-2.amazonaws.com/0a9f7588-a2c4-4484-b051-6658ce32605c/A2C/infrastructure.yaml)|

You can leave the parameters with default values. `infrastructure.yaml` stack will take 3-5 minutes to complete deployment.

## Deploy Web Application

### Step :one: Deploy [development.yaml](/architecture-to-cloudformation/development.yaml).

|   Region   | development.yaml |
| ---------- | ----------------- |
| us-east-1  | [![launch-stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=ArchToCloudformation&templateURL=https://ws-assets-prod-iad-r-iad-ed304a55c2ca1aee.s3.us-east-1.amazonaws.com/0a9f7588-a2c4-4484-b051-6658ce32605c/A2C/base/development.yaml)|
| us-west-2  | [![launch-stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?region=us-west-2#/stacks/new?stackName=ArchToCloudformation&templateURL=https://ws-assets-prod-iad-r-pdx-f3b3f9f1a7d6a3d0.s3.us-west-2.amazonaws.com/0a9f7588-a2c4-4484-b051-6658ce32605c/A2C/base/development.yaml)|

Make sure to provide values for following parameters:
1. VPCId: VPC for provisioning required infrastructure. 
2. PublicSubnetAId: Public subnet A with route to internet gateway. Application Load Balancer will be provisioned in public subnet. 
3. PublicSubnetBId: Public subnet B with route to internet gateway. Application Load Balancer will be provisioned in public subnet. 
4. PrivateSubnetAId: Private subnet A with route to NAT gateway. ECS tasks will be provisioned in private subnet. 
5. PrivateSubnetBId: Private subnet B with route to NAT gateway. ECS tasks will be provisioned in private subnet. 
6. EnvironmentName: Unique name to distinguish application in the same AWS account (min length 1 and max length 4); you can try `dev`, `test` or `prod`.
7. ModelId: To specify the Amazon Bedrock model ID you want to use for inference. This flexibility allows you to choose the model that best suits your needs. By default, the template leverages the Anthropic Claude 3 Sonnet model, renowned for its exceptional performance. However, if you prefer to utilize a different model, you can seamlessly pass its Amazon Bedrock model ID as a parameter during deployment. It's essential to ensure that you have requested access to the desired model beforehand and that it possesses the necessary vision capabilities required for your specific use case.

### Step :three: Viewing the app

After the successful completion of `development.yaml`. Get the CloudFront URL from the `Outputs` tab of the stack. Paste it in the browser to view the web application.

## Clean Up
- Open the CloudFormation console.
- Select the stack `infrastructure.yaml` you created then click **Delete**. Wait for the stack to be deleted.
- Select the stack `development.yaml` you created then click **Delete**. Wait for the stack to be deleted.