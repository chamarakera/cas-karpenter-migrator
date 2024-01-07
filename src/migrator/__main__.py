from pprint import pprint

from deployment import Deployment
from kubeconfig import KubeConfig
from nodegroup import NodeGroup
from reader import Reader


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

    # select two ec2 instances from a single multi-AZ node group to retain
    node_group = NodeGroup(config.node_group()[0]['name'])
    single_multi_az_ng = node_group.single_multi_az_node_group()
    pprint(node_group.select_instances(single_multi_az_ng))


if __name__ == "__main__":
    main()
