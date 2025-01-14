import boto3
from django.conf import settings
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import EventFile

@receiver(post_delete, sender=EventFile)
def delete_file_from_s3(sender, instance, **kwargs):
    """
    Deletes the file from S3 when an EventFile instance is deleted.
    """
    # Initialize the S3 client
    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    
    if instance.file:
        try:
            s3.delete_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=str(instance.file)  # Convert the file field to string for the key
            )
            print(f"Deleted {instance.file} from S3")
        except Exception as e:
            print(f"Error deleting file from S3: {e}")
