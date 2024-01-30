from deployment import Deployment
from kubeconfig import KubeConfig
from nodegroup import NodeGroup
from reader import Reader
from kube_actions import KubeActions
from scaling_actions import ScalingActions


def main():
    KubeConfig.load_kube_config()

    # Read config file
    config = Reader("config.yaml")

    # Checks if there are Pods with "NoSchedule" tolerations
    # before starting the migration tasks
    KubeActions().check_no_schedule_tolerations()

    # Find the deployment object of cluster auto scaler
    # Scale cluster auto scaler deployment down to zero
    Deployment(config.deployment(), config.namespace()).scale_to_zero()

    # Get EC2 instances in the node group (single multi-AZ ng)
    node_group = NodeGroup(config.node_group()[0]["name"])
    instances = node_group.extract_instances(node_group.single_multi_az_node_group())

    # Extract asg name from the node group
    auto_scaling_group_name = node_group.extract_asg_name(node_group.single_multi_az_node_group())

    # Select two instances that does not belong to the same AZ
    # to add scale-in protection from the single multi-AZ node group
    select_two_instances = node_group.select_instances(instances)

    # Add scale-in protection
    scaling_actions = ScalingActions(auto_scaling_group_name)
    scaling_actions.set_scale_in_protection(select_two_instances, True)

    # Generate dictionary of instance without protection these
    # instance would eventually cordened, drained and terminated
    nodes_to_retire = node_group.get_node_name(
        node_group.instances_without_protection(instances, select_two_instances)
    )

    # Perform various actions to Corden and evict pods from nodes
    for node in nodes_to_retire:
        KubeActions().corden(node["node_name"])
        KubeActions().drain(node["node_name"])
        KubeActions().wait_until_pods_scheduled()

    # Scaling down the ASG/Node Group
    # Since, our scope is a single multi-AZ NG we will
    # keep minimum of 2 instances in the NG as suggested in
    # https://karpenter.sh/docs/getting-started/migrating-from-cas/#remove-cas
    single_multi_az_ng_size = 2
    scaling_actions.resize_scaling_group(single_multi_az_ng_size)
    scaling_actions.set_scale_in_protection(select_two_instances, False)


if __name__ == "__main__":
    main()
