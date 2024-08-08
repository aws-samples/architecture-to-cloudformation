from boto3.session import Session


def read_image(s3_path):
    s3 = Session().client("s3")

    # Split the path by the '/' character
    parts = s3_path.replace("s3://", "")
    parts = parts.split("/")
    # The bucket name is the second part (index 1)
    bucket_name = parts[0]

    # The key name is the remaining parts joined back together
    key_name = "/".join(parts[1:])

    try:
        response = s3.get_object(Bucket=bucket_name, Key=key_name)
        image_data = response["Body"].read()
    except Exception as e:
        print(f"Error downloading image: {e}")
        image_data = None
    return image_data


def download_cfn(s3_path):
    s3 = Session().client("s3")

    # Split the path by the '/' character
    parts = s3_path.replace("s3://", "")
    parts = parts.split("/")
    # The bucket name is the second part (index 1)
    bucket_name = parts[0]

    # The key name is the remaining parts joined back together
    key_name = "/".join(parts[1:])

    try:
        response = s3.get_object(Bucket=bucket_name, Key=key_name)
        cfn_data = response["Body"].read()
    except Exception as e:
        print(f"Error downloading image: {e}")
        cfn_data = None
    return cfn_data
