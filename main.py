from kubeconfig import KubeConfig
from deployment import Deployment

def main():
    KubeConfig.load_kube_config()
    
    # find the deployment
    deployment = Deployment("cluster-autoscaler", "kube-system")
    # find the deployment object of cluster auto scaler
    cas_deployment = deployment.find_deployment()
    # scale cluster auto scaler deployment down to zero
    deployment.scale_to_zero(cas_deployment)

if __name__ == "__main__":
    main()
