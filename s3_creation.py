#create s3 bucket
import boto3

REGION = "us-east-2"
s3 = boto3.client('s3', region_name=REGION)
bucket_name = 'yovel-s3-bucket'  
try:  
      s3.create_bucket(Bucket=bucket_name)
      print(f'Bucket {bucket_name} created successfully.')
except Exception as e:
      print(f'Error creating bucket: {e}')

# import boto3
# from botocore.exceptions import ClientError

# def create_my_bucket(bucket_name: str, region: str = "us-east-1"):
#     # יצירת אובייקט לקוח של S3
#     s3_client = boto3.client("s3", region_name=region)

#     try:
#         # יצירת ה-Bucket
#         # שים לב: באזור us-east-1 לא צריך לציין LocationConstraint
#         if region == "us-east-1":
#             s3_client.create_bucket(Bucket=bucket_name)
#         else:
#             location = {'LocationConstraint': region}
#             s3_client.create_bucket(
#                 Bucket=bucket_name,
#                 CreateBucketConfiguration=location
#             )
        
#         print(f"Bucket '{bucket_name}' created successfully.")

#     except ClientError as e:
#         print(f"Error: {e.response['Error']['Message']}")

# if __name__ == "__main__":
#     # בחר שם ייחודי מאוד!
#     my_unique_bucket_name = "adi-meller-test-bucket-2026-05-28"
#     create_my_bucket(my_unique_bucket_name)
