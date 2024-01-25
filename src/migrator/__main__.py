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

    deployment = Deployment(config.deployment(), config.namespace())
    # Find the deployment object of cluster auto scaler
    # Scale cluster auto scaler deployment down to zero
    deployment.scale_to_zero(deployment.find_deployment())

    # Get EC2 instances in the node group (single multi-AZ ng)
    node_group = NodeGroup(config.node_group()[0]["name"])
    instances = node_group.extract_instances(node_group.single_multi_az_node_group())

    # Extract asg name from the node group
    auto_scaling_group_name = node_group.extract_asg_name(node_group.single_multi_az_node_group())

    # Select two instances that does not belong to the same AZ
    # to add scale-in protection from the single multi-AZ node group
    selected_instances = node_group.select_instances(instances)

    # Add scale-in protection
    ScalingActions(auto_scaling_group_name).set_scale_in_protection(selected_instances)

    # Generate dictionary of instance without protection these
    # instance would eventually cordened, drained and terminated
    nodes_to_retire = node_group.get_node_name(
        node_group.instances_without_protection(instances, selected_instances)
    )

    # Perform different actions to corden and evict pods from nodes
    kube_actions = KubeActions()
    kube_actions.corden(nodes_to_retire[0]["node_name"])
    kube_actions.remove_all_pods(nodes_to_retire[0]["node_name"])
    kube_actions.wait_until_pods_scheduled()


if __name__ == "__main__":
    main()
