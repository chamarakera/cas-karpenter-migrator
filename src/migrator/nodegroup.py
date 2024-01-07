import sys

import boto3
from loguru import logger


class NodeGroup:
    def __init__(self, node_group_name: str) -> None:
        self.node_group_name = node_group_name
        self.client = boto3.client('autoscaling')

    def single_multi_az_node_group(self) -> list:
        node_group = self.client.describe_auto_scaling_groups(
            Filters=[
                {
                    'Name': 'tag:Name',
                    'Values': [
                        self.node_group_name
                    ]
                }
            ]
        )

        if not node_group['AutoScalingGroups'][0]['Instances']:
            logger.error("no node groups were identified. "
                         "please check if tags are correct")
        return node_group['AutoScalingGroups'][0]['Instances']

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
                    if selected_instances and selected_instances[0]["AvailabilityZone"] == instance["AvailabilityZone"]:
                        continue
                    selected_instances.append(instance)
                    count += 1

        if len(selected_instances) == 1:
            logger.error("the nodes must belong to at least two different AZs")
            sys.exit(1)

        return selected_instances
