import sys

import boto3
from loguru import logger


class NodeGroup:
    def __init__(self, node_group_name: str) -> None:
        self.node_group_name = node_group_name
        self.asg_client = boto3.client("autoscaling")
        self.ec2_client = boto3.client("ec2")

    def single_multi_az_node_group(self) -> list:
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

    def extract_instances(self, auto_scaling_group: object) -> list:
        if not auto_scaling_group["Instances"]:
            logger.error("No instances identified in the auto scaling group")
            sys.exist(1)

        return auto_scaling_group["Instances"]

    def extract_asg_name(self, auto_scaling_group: object) -> list:
        logger.info(f"ASG name of the node group: {auto_scaling_group['AutoScalingGroupName']}")

        return auto_scaling_group["AutoScalingGroupName"]

    @staticmethod
    def select_instances(node_group_instances: list) -> list:
        selected_instances = []

        if len(node_group_instances) < 2:
            logger.error("there must be more than 1 instances in the node group")
            sys.exit(1)
        else:
            count = 1
            for instance in node_group_instances:
                if count <= 2:
                    if (
                        selected_instances
                        and selected_instances[0]["AvailabilityZone"]
                        == instance["AvailabilityZone"]
                    ):
                        continue
                    selected_instances.append(instance)
                    count += 1

        if len(selected_instances) == 1:
            logger.error("the nodes must belong to at least two different AZs")
            sys.exit(1)

        logger.info(
            f"Instances selected to add scale-in protection: "
            f"{', '.join([instance['InstanceId'] for instance in selected_instances])}"
            f"{', '.join([instance['AvailabilityZone'] for instance in selected_instances])}"
        )

        return selected_instances

    def instances_without_protection(self, instance_in_asg: list, selected_instances: list) -> list:
        all_instances = [instance["InstanceId"] for instance in instance_in_asg]
        selected_instances = [instance["InstanceId"] for instance in selected_instances]
        instances_without_protection = [
            instance for instance in all_instances if instance not in selected_instances
        ]
        logger.info(
            "Instances without scale-in protection: " f"{', '.join(instances_without_protection)}"
        )

        return instances_without_protection

    def get_node_name(self, instance_ids: list, use_name_tag=False) -> list:
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
                            "status": "pending",
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
                            "status": "pending",
                        }
                    )

        return nodes
