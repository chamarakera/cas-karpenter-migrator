from deployment import Deployment
from kubeconfig import KubeConfig
from kuber import Kuber
from nodegroup import NodeGroup
from reader import Reader


def main():
    KubeConfig.load_kube_config()

    # Read config file
    config = Reader("config.yaml")

    # Checks for Pods with "NoSchedule" tolerations
    # prior to starting any migration asks
    Kuber().detect_no_schedule_tolerations()

    # Find the deployment object of cluster auto scaler and scale it down too 0
    Deployment(config.deployment(), config.namespace()).scale_to_zero()

    # Loop over node groups
    for ng in config.node_groups():
        node_group = NodeGroup(ng["name"])
        # Extract nodes from the node group
        nodes = node_group.extract_instances(node_group.single_multi_az_node_group())

        # Select nodes where Karpenter pods are running
        # in order to add enable scale-in protection on them
        karpenter_nodes = Kuber().extract_karpenter_instance_ids(namespace="infra")

        # Add scale-in protection
        node_group.set_scale_in_protection(karpenter_nodes, True)

        # Create a dict of nodes without scale-in protection. These
        # nodes would be eventually cordened, drained and terminated
        nodes_to_retire = node_group.get_node_name(
            node_group.instances_without_protection(nodes, karpenter_nodes)
        )

        # Perform various actions to corden and evict pods from nodes.
        # In order to retire them from the node group, Karpenter will
        # create new nodes to schedule workloads from retired nodes.
        for node in nodes_to_retire:
            Kuber().corden(node["node_name"])
            Kuber().drain(node["node_name"])
            Kuber().wait_until_pods_scheduled()

        # Scaling down the ASG/Node Group
        # Since, our scope is a single multi-AZ NG we will
        # keep minimum of 2 instances in the NG as suggested in
        # https://karpenter.sh/docs/getting-started/migrating-from-cas/#remove-cas
        node_group.resize_scaling_group()

        # Finally remove scale-in protection added in previous step
        node_group.set_scale_in_protection(karpenter_nodes, False)


if __name__ == "__main__":
    main()
