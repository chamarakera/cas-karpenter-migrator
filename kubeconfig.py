from kubernetes import config
from loguru import logger

import sys

class KubeConfig:
    def __init__(self) -> None:
        pass
    
    def load_kube_config():
        try:
            config.load_kube_config()
        except config.config_exception.ConfigException:
            logger.error("failed to load kubeconfig. please make sure "
                        "kubeconfig is setup prior to running this script")
            sys.exit(1)
