import sys

import boto3
from loguru import logger


class ScalingActions:
    def __init__(self, auto_scaling_group) -> None:
        self.client = boto3.client("autoscaling")
        self.auto_scaling_group = auto_scaling_group

    def set_scale_in_protection(self, instances) -> None:
        instance_ids = [instance["InstanceId"] for instance in instances]
        response = self.client.set_instance_protection(
            InstanceIds=instance_ids,
            AutoScalingGroupName=self.auto_scaling_group,
            ProtectedFromScaleIn=True,
        )
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            logger.info(f"scale-in protection added to: {instance_ids}")
        else:
            logger.error(f"scale-in protection could not be added to: {instance_ids}")
            sys.exit(0)
