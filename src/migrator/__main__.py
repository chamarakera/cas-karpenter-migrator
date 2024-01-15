from deployment import Deployment
from kubeconfig import KubeConfig
from nodegroup import NodeGroup
from reader import Reader
from data import Data
from scaling_actions import ScalingActions


def main():
    KubeConfig.load_kube_config()

    # read config file
    config = Reader("config.yaml")

    # find the deployment
    deployment = Deployment(config.deployment(), config.namespace())
    # find the deployment object of cluster auto scaler
    cas_deployment = deployment.find_deployment()
    # scale cluster auto scaler deployment down to zero
    deployment.scale_to_zero(cas_deployment)

    # get ec2 instances from a single multi-AZ node group
    node_group = NodeGroup(config.node_group()[0]["name"])
    single_multi_az_ng = node_group.single_multi_az_node_group()
    instances = node_group.extract_instances(single_multi_az_ng)

    # extract asg name and select instances to add scale-in
    # protection from the single multi-AZ node group
    auto_scaling_group_name = node_group.extract_asg_name(single_multi_az_ng)
    selected_instances = node_group.select_instances(instances)

    # add scale-in protection
    scaling_actions = ScalingActions(auto_scaling_group_name)
    scaling_actions.set_scale_in_protection(selected_instances)

    # get instances without scale-in protection enabled
    print(
        Data().create_instance_status_info(
            node_group.instances_without_protection(instances, selected_instances),
            "pending",
        )
    )


if __name__ == "__main__":
    main()
