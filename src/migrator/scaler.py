import sys
import time

import boto3
from loguru import logger


class Scaler:
    def __init__(self, auto_scaling_group: str) -> None:
        self.client = boto3.client("autoscaling")
        self.auto_scaling_group = auto_scaling_group

    def set_scale_in_protection(self, instances: list, enable_protection: bool) -> None:
        """Set scale-in protection to a a list
        of instances in and Auto Scaling Group"""
        instance_ids = [instance["InstanceId"] for instance in instances]
        response = self.client.set_instance_protection(
            InstanceIds=instance_ids,
            AutoScalingGroupName=self.auto_scaling_group,
            ProtectedFromScaleIn=enable_protection,
        )
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            logger.info(f"scale-in protection added to: {', '.join(instance_ids)}")
        else:
            logger.error(f"scale-in protection could not be added to: {', '.join(instance_ids)}")
            sys.exit(0)

    def resize_scaling_group(self, size: int) -> None:
        logger.info(f"Resizing scaling group {self.auto_scaling_group} to {size}")
        try:
            _ = self.client.update_auto_scaling_group(
                AutoScalingGroupName=self.auto_scaling_group,
                MinSize=size,
                MaxSize=size,
                DesiredCapacity=size,
            )
        except (
            self.client.exception.ResourceContentionFault,
            self.client.exception.ServiceLinkedRoleFailure,
            self.client.exception.ScalingActivityInProgressFault,
        ) as e:
            logger.error(e)
            sys.exist(1)
        else:
            logger.info("Successfully scaled scaling group " f"{self.auto_scaling_group} to {size}")

    def remove_scale_in_protection(self, instances: list, size: str) -> None:
        while True:
            asg = self.client.describe_auto_scaling_groups(
                AutoScalingGroupNames=[
                    self.auto_scaling_group,
                ],
            )
            if len(asg["AutoScalingGroups"][0]["Instances"]) == size:
                self.set_scale_in_protection(instances, False)
            logger.info(
                "Waiting for the ASG to scale to size: "
                f"{size}. Current size: "
                f"{len(asg['AutoScalingGroups'][0]['Instances'])}"
            )
            time.sleep(10)
