import sys
import time

import boto3
from kubernetes import client
from loguru import logger


class NodeGroup:
    def __init__(self, node_group_name: str) -> None:
        self.node_group_name = node_group_name
        self.asg_client = boto3.client("autoscaling")
        self.ec2_client = boto3.client("ec2")
        self.core_v1_api = client.CoreV1Api()

    def auto_scaling_group(self) -> list:
        node_group = self.asg_client.describe_auto_scaling_groups(
            Filters=[
                {
                    "Name": "tag:Name",
                    "Values": [
                        self.node_group_name,
                    ],
                },
            ]
        )
        if not node_group["AutoScalingGroups"]:
            logger.error("No node groups were identified. Please check if tags are correct")
        return node_group["AutoScalingGroups"]

    def extract_nodes(self) -> list:
        if not self.auto_scaling_group()["Instances"]:
            logger.error("No instances identified in the auto scaling group")
            sys.exist(1)

        return self.auto_scaling_group()["Instances"]

    def nodes_without_protection(self, instance_in_asg: list, selected_instances: list) -> list:
        all_instances = [instance["InstanceId"] for instance in instance_in_asg]
        nodes_without_protection = [
            instance for instance in all_instances if instance not in selected_instances
        ]
        logger.info(
            "Instances without scale-in protection: " f"{', '.join(nodes_without_protection)}"
        )
        return nodes_without_protection

    def get_node_name(self, instance_ids: list, use_name_tag=False) -> list:
        """Returns Kubernetes Node name based on lit of EC2 Instance IDs.
        It will return the 'Name' tag of the instance or the Private DNS
        name of the instance"""
        nodes = []
        if use_name_tag:
            response = self.ec2_client.describe_tags(
                Filters=[
                    {
                        "Name": "resource_id",
                        "Values": instance_ids,
                    },
                ]
            )
            for tag in response["Tags"]:
                if tag["Key"] == "Name":
                    nodes.append(
                        {
                            "instance_id": tag["ResourceId"],
                            "node_name": tag["Value"],
                        }
                    )
        else:
            response = self.ec2_client.describe_instances(
                InstanceIds=instance_ids,
            )
            for reservation in response["Reservations"]:
                for instances in reservation["Instances"]:
                    nodes.append(
                        {
                            "instance_id": instances["InstanceId"],
                            "node_name": instances["PrivateDnsName"],
                        }
                    )
        return nodes

    def set_scale_in_protection(self, instances: list, enable_protection: bool) -> None:
        """Set scale-in protection to a a list
        of instances in and Auto Scaling Group"""
        instance_ids = [instance["InstanceId"] for instance in instances]
        response = self.asg_client.set_instance_protection(
            InstanceIds=instance_ids,
            AutoScalingGroupName=self.auto_scaling_group()["AutoScalingGroupName"],
            ProtectedFromScaleIn=enable_protection,
        )
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            logger.info(f"scale-in protection added to: {', '.join(instance_ids)}")
        else:
            logger.error(f"scale-in protection could not be added to: {', '.join(instance_ids)}")
            sys.exit(0)

    def resize_scaling_group(self, size=2) -> None:
        asg_name = self.auto_scaling_group()["AutoScalingGroupName"]
        logger.info(f"Resizing scaling group {asg_name} to {size}")
        try:
            _ = self.asg_client.update_auto_scaling_group(
                AutoScalingGroupName=asg_name,
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
            logger.info("Successfully scaled scaling group " f"{asg_name} to {size}")

    def remove_scale_in_protection(self, instances: list, size=2) -> None:
        while True:
            asg_instance_size = len(self.auto_scaling_group()["Instances"])
            if asg_instance_size == size:
                self.set_scale_in_protection(instances, False)
                return
            logger.info(
                "Waiting for the ASG to scale to size: "
                f"{size}. Current size: "
                f"{asg_instance_size}"
            )
            time.sleep(10)
