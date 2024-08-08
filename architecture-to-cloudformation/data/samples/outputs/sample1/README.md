# Output [Sample1.jpg](/architecture-to-cloudformation/util/samples/sample1.jpg)
 
![sample1.jpg](/architecture-to-cloudformation/data/samples/sample1.jpg)

Uploading the above architecture diagram to the web application generates a step-by-step explanation of the Architecture diagram using Anthropic Claude 3 Sonnet vision capabilities. The step-by-step explanation is augmented with a few shot-learning examples to develop an initial AWS CloudFormation template. 


![artifact-1.png](/architecture-to-cloudformation/data/samples/outputs/sample1/artifact-1.png)

Let's analyze the step-by-step explanation. The generated response is divided into three parts:

1.	The context explains what the architecture diagram depicts.
2.	The architecture diagram's flow gives the order in which AWS services are invoked and their relationship with each other.
3.	We get a summary of the entire generated response.
In the following step-by-step explanation, we see a few highlighted errors.

![artifact-2.png](/architecture-to-cloudformation/data/samples/outputs/sample1/artifact-2.png)

Let's analyze the initial AWS CloudFormation template. 

> [!IMPORTANT]  
> The AWS CloudFormation template generated by the web application are intended for inspiration purposes and not for production-level applications. It is the responsibility of a developer to test and vet the AWS CloudFormation template according to security guidelines.

```
AWSTemplateFormatVersion: '2010-09-09'
Description: >
  This CloudFormation stack sets up a serverless data processing pipeline triggered by file uploads to an S3 bucket.
  It uses AWS Lambda to process the uploaded files, and Amazon SNS to send notifications upon successful processing.

Parameters:
  S3BucketName:
    Type: String
    Description: Name of the S3 bucket for file uploads
    AllowedPattern: ^[a-z0-9][a-z0-9-]*[a-z0-9]$
    MinLength: 1
    MaxLength: 63

  EmailAddress:
    Type: String
    Description: Email address to receive notifications
    AllowedPattern: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$

Resources:

  # S3 Bucket
  S3Bucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Ref S3BucketName
      NotificationConfiguration:
        LambdaConfigurations:
          - Event: 's3:ObjectCreated:*'
            Function: !GetAtt ProcessingLambda.Arn

  # SNS Topic
  SNSTopic:
    Type: AWS::SNS::Topic
    Properties:
      Subscription:
        - Endpoint: !Ref EmailAddress
          Protocol: email

  # Lambda Function
  ProcessingLambda:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: ProcessingLambda
      Runtime: python3.9
      Handler: index.lambda_handler
      Role: !GetAtt LambdaRole.Arn
      Code:
        ZipFile: |
          import boto3

          def lambda_handler(event, context):
              s3 = boto3.client('s3')
              sns = boto3.client('sns')

              # Process the uploaded file
              for record in event['Records']:
                  bucket_name = record['s3']['bucket']['name']
                  object_key = record['s3']['object']['key']

                  # Process the file data
                  # ...

              # Send notification upon successful processing
              sns.publish(
                  TopicArn=!Ref SNSTopic,
                  Message='File processing completed successfully',
                  Subject='Data Processing Notification'
              )

              return {
                  'statusCode': 200,
                  'body': 'File processing completed successfully'
              }

  # Lambda Role
  LambdaRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: 'sts:AssumeRole'
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      Policies:
        - PolicyName: S3Access
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - 's3:GetObject'
                Resource: !Join ['', ['arn:aws:s3:::', !Ref S3BucketName, '/*']]
        - PolicyName: SNSPublish
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - 'sns:Publish'
                Resource: !Ref SNSTopic

  # Lambda Permissions
  LambdaPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !GetAtt ProcessingLambda.Arn
      Action: 'lambda:InvokeFunction'
      Principal: s3.amazonaws.com
      SourceAccount: !Ref AWS::AccountId
      SourceArn: !Join ['', ['arn:aws:s3:::', !Ref S3BucketName]]

Outputs:

  S3BucketName:
    Description: Name of the S3 bucket for file uploads
    Value: !Ref S3Bucket
    Export:
      Name: !Sub '${AWS::StackName}-S3BucketName'

  LambdaFunctionArn:
    Description: ARN of the Lambda function
    Value: !GetAtt ProcessingLambda.Arn
    Export:
      Name: !Sub '${AWS::StackName}-LambdaFunctionArn'

  SNSTopicArn:
    Description: ARN of the SNS topic for notifications
    Value: !Ref SNSTopic
    Export:
      Name: !Sub '${AWS::StackName}-SNSTopicArn'
```

After analyzing the AWS CloudFormation template, we see that the Lambda code refers to Amazon SNS Topic using !Ref SNSTopic, which is not valid. Moreover, we would also like to add additional functionality to the template. First, we want to filter the Amazon S3 notification configuration to invoke AWS lambda only when *.csv files are uploaded. Second, we want to add metadata to the AWS CloudFormation template. To do this we will use the chat interface to give following update instruction to the web application. 

Make the following updates:

```
1.	Use environment variables for AWS Lambda to access SNS Topic ARN.
2.	Add filter to S3 notification configuration to only invoke AWS lambda when *.csv files are uploaded 
3.	Add metadata to CloudFormation template
```

![artifact-3.png](/architecture-to-cloudformation/data/samples/outputs/sample1/artifact-3.png)

The updated AWS CloudFormation template is given below:

> [!IMPORTANT]  
> The AWS CloudFormation template generated by the web application are intended for inspiration purposes and not for production-level applications. It is the responsibility of a developer to test and vet the AWS CloudFormation template according to security guidelines.

```
AWSTemplateFormatVersion: '2010-09-09'
Description: >
  This CloudFormation stack sets up a serverless data processing pipeline triggered by file uploads to an S3 bucket.
  It uses AWS Lambda to process the uploaded files, and Amazon SNS to send notifications upon successful processing.

Metadata:
  'AWS::CloudFormation::Interface':
    ParameterGroups:
      - Label:
          default: 'S3 Bucket Configuration'
        Parameters:
          - S3BucketName
      - Label:
          default: 'Notification Configuration'
        Parameters:
          - EmailAddress

Parameters:
  S3BucketName:
    Type: String
    Description: Name of the S3 bucket for file uploads
    AllowedPattern: ^[a-z0-9][a-z0-9-]*[a-z0-9]$
    MinLength: 1
    MaxLength: 63

  EmailAddress:
    Type: String
    Description: Email address to receive notifications
    AllowedPattern: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$

Resources:

  # S3 Bucket
  S3Bucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Ref S3BucketName
      NotificationConfiguration:
        LambdaConfigurations:
          - Event: 's3:ObjectCreated:*'
            Function: !GetAtt ProcessingLambda.Arn
            Filter:
              S3Key:
                Rules:
                  - Name: suffix
                    Value: .csv

  # SNS Topic
  SNSTopic:
    Type: AWS::SNS::Topic
    Properties:
      Subscription:
        - Endpoint: !Ref EmailAddress
          Protocol: email

  # Lambda Function
  ProcessingLambda:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: ProcessingLambda
      Runtime: python3.9
      Handler: index.lambda_handler
      Role: !GetAtt LambdaRole.Arn
      Environment:
        Variables:
          SNS_TOPIC_ARN: !Ref SNSTopic
      Code:
        ZipFile: |
          import boto3
          import os

          def lambda_handler(event, context):
              s3 = boto3.client('s3')
              sns = boto3.client('sns')
              sns_topic_arn = os.environ['SNS_TOPIC_ARN']

              # Process the uploaded file
              for record in event['Records']:
                  bucket_name = record['s3']['bucket']['name']
                  object_key = record['s3']['object']['key']

                  # Process the file data
                  # ...

              # Send notification upon successful processing
              sns.publish(
                  TopicArn=sns_topic_arn,
                  Message='File processing completed successfully',
                  Subject='Data Processing Notification'
              )

              return {
                  'statusCode': 200,
                  'body': 'File processing completed successfully'
              }

  # Lambda Role
  LambdaRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: 'sts:AssumeRole'
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      Policies:
        - PolicyName: S3Access
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - 's3:GetObject'
                Resource: !Join ['', ['arn:aws:s3:::', !Ref S3BucketName, '/*']]
        - PolicyName: SNSPublish
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - 'sns:Publish'
                Resource: !Ref SNSTopic

  # Lambda Permissions
  LambdaPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !GetAtt ProcessingLambda.Arn
      Action: 'lambda:InvokeFunction'
      Principal: s3.amazonaws.com
      SourceAccount: !Ref AWS::AccountId
      SourceArn: !Join ['', ['arn:aws:s3:::', !Ref S3BucketName]]

Outputs:

  S3BucketName:
    Description: Name of the S3 bucket for file uploads
    Value: !Ref S3Bucket
    Export:
      Name: !Sub '${AWS::StackName}-S3BucketName'

  LambdaFunctionArn:
    Description: ARN of the Lambda function
    Value: !GetAtt ProcessingLambda.Arn
    Export:
      Name: !Sub '${AWS::StackName}-LambdaFunctionArn'

  SNSTopicArn:
    Description: ARN of the SNS topic for notifications
    Value: !Ref SNSTopic
    Export:
      Name: !Sub '${AWS::StackName}-SNSTopicArn'
```