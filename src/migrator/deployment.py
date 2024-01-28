import sys

from typing import Type
from kubernetes import client
from loguru import logger


class Deployment:
    def __init__(self, deployment_name: str, namespace: str) -> None:
        self.deployment_name = deployment_name
        self.namespace = namespace
        self.apps_v1_api = client.AppsV1Api()

    def find_deployment(self) -> object:
        """Finds a deployment object when the name and the namespace
        of the deployment is given"""
        try:
            deployment = self.apps_v1_api.read_namespaced_deployment(
                name=self.deployment_name, namespace=self.namespace
            )
        except client.exceptions.ApiException as e:
            if e.status == 404:
                logger.error(
                    "Deployment could not be found. Please check"
                    " if deployment name or namespace names are correct."
                )
                sys.exit(1)

        return deployment

    def scale_to_zero(self, deployment: Type[client.V1Deployment]):
        """Scales the deployment replicas to 0"""
        deployment.spec.replicas = 0

        try:
            patched_deployment = self.apps_v1_api.patch_namespaced_deployment(
                name=self.deployment_name, namespace=self.namespace, body=deployment
            )
        except client.exception.ApiException as e:
            if e.status == 404:
                logger.error(
                    "Deployment could not be found. Please check"
                    " if deployment name or namespace names are correct."
                )
                sys.exit(1)

        logger.info(
            f"Patched number of deployment {patched_deployment.spec.name} "
            f"replicas to: {patched_deployment.spec.replicas}"
        )
