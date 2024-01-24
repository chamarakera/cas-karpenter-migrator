from kubernetes import client
from kubernetes.client.rest import ApiException
from loguru import logger
import time


class KubeActions:
    def __init__(self) -> None:
        self.v1_api = client.CoreV1Api()

    def corden(self, node_name: str):
        body = {
            "spec": {
                "unschedulable": True,
            },
        }
        self.v1_api.patch_node(node_name, body)

    def pod_is_evicatable(self, pod):
        if pod.metadata.annotations is not None and pod.metadata.annotations.get(
            "kubernetes.io/config.mirror"
        ):
            logger.info(
                f"Skipping mirror pod {pod.metadata.namespace}/{pod.metadata.name}"
            )
            return False
        if pod.metadata.owner_references is None:
            return True
        for ref in pod.metadata.owner_references:
            if (
                ref.controller is not None
                and ref.controller
                and ref.kind == "DaemonSet"
            ):
                logger.info(
                    f"Skipping DaemonSet {pod.metadata.namespace}/{pod.metadata.name}"
                )
                return False
        return True

    def get_evictable_pods(self, node_name):
        field_selector = "spec.nodeName=" + node_name
        pods = self.v1_api.list_pod_for_all_namespaces(
            watch=False, field_selector=field_selector
        )
        return [pod for pod in pods.items if self.pod_is_evicatable(pod)]

    def remove_all_pods(self, node_name, poll=5):
        pods = self.get_evictable_pods(node_name)

        logger.debug(f"Number of pods to delete: {str(len(pods))}")

    def evict_pods(self, pods):
        remaining = []
        for pod in pods:
            logger.info(
                f"Evicting pod {pod.metadata.name} in namespace {pod.metadata.namespace}"
            )
            body = {
                "apiVersion": "policy/v1beta1",
                "kind": "Eviction",
                "deleteOptions": {},
                "metadata": {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                },
            }
            try:
                self.v1_api.create_namespaced_pod_eviction(
                    pod.metadata.name, pod.metadata.namespace, body
                )
            except ApiException as e:
                if e.status == 429:
                    remaining.append(pod)
                    logger.waring(
                        f"Pod {pod.metadata.namespace}/{pod.metadata.name} could not be evicted due to distruption budget. Will retry."
                    )
                else:
                    logger.exception(
                        f"Unexpected error adding eviction for pod {pod.metadata.namespace}/{pod.metadata.name}"
                    )
            except:
                logger.exception(
                    f"Unexpected error adding evication for pod {pod.metadata.namespace}/{pod.metadata.name}"
                )
        return remaining

    def evict_until_completed(self, pods, poll):
        pending = pods
        while True:
            pending = self.evict_pods(pending)
            if (len(pending)) <= 0:
                return
            time.sleep(poll)

    def wait_until_empty(self, node_name, poll):
        logger.info("Waiting for evictions to complete")
        while True:
            pods = self.get_evictable_pods(node_name)
            if len(pods) <= 0:
                logger.info("All pods evicted successfully")
                return
            logger.debug(
                f"Still waiting for deletion of the following pods: {', '.join(map(lambda pod: pod.metadata.namespaace + "/" + pod.metadata.name, pods))}"
            )

    def get_pending_pods(self):
        pods = self.v1_api.list_pod_for_all_namespaces(watch=False)
        return [pod for pod in pods.items if pod.status.phase == "Pending"]

    def wait_until_pods_scheduled(self):
        while True:
            pods = self.get_pending_pods()
            if len(pods) <= 0:
                logger.info("All pods scheduled successfully")
                return
            logger.debug(
                f"Still waiting for the following pods to be scheduled: {', '.join(map(lambda pod: pod.metadata.namespaace + "/" + pod.metadata.name, pods))}"
            )
            time.sleep(5)
