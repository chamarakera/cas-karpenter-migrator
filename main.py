from kubeconfig import KubeConfig
from deployment import Deployment
from reader import Reader

def main():
    KubeConfig.load_kube_config()
    
    # read config file
    config = Reader("config.yaml")

    # find the deployment
    deployment = Deployment(config.deployment, config.namespace)
    # find the deployment object of cluster auto scaler
    cas_deployment = deployment.find_deployment()
    # scale cluster auto scaler deployment down to zero
    deployment.scale_to_zero(cas_deployment)

if __name__ == "__main__":
    main()
