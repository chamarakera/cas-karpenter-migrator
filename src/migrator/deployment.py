import sys

from kubernetes import client
from loguru import logger


class Deployment:
    def __init__(self, deployment_name: str, namespace: str) -> None:
        self.deployment_name = deployment_name
        self.namespace = namespace

    def find_deployment(self) -> object:
        try:
            deployment = client.AppsV1Api().read_namespaced_deployment(
                name=self.deployment_name,
                namespace=self.namespace
            )
        except client.exceptions.ApiException as e:
            if e.status == 404:
                logger.error("deployment could not be found. please check"
                            " if deployment name or namespace names are correct.")
                sys.exit(1)

        return deployment

    def scale_to_zero(self, deployment):
        deployment.spec.replicas = 0

        try:
            patched_deployment = client.AppsV1Api().patch_namespaced_deployment(
                name=self.deployment_name,
                namespace=self.namespace,
                body=deployment
            )
        except client.exception.ApiException as e:
            if e.status == 404:
                logger.error("deployment could not be found. please check"
                            " if deployment name or namespace names are correct.")
                sys.exit(1)

        logger.info("patched number of deployment replicas to: "
                    "{patched_deployment.spec.replicas}")
