import sys
import time

from kubernetes import client
from kubernetes.client.rest import ApiException
from loguru import logger

INTERVAL = 5


class Kuber:
    def __init__(self, action_timeout=5) -> None:
        self.core_v1_api = client.CoreV1Api()
        self.action_timeout = action_timeout

    def corden(self, node_name: str):
        body = {
            "spec": {
                "unschedulable": True,
            },
        }
        self.core_v1_api.patch_node(node_name, body)

    def pod_is_evicatable(self, pod):
        if pod.metadata.annotations is not None and pod.metadata.annotations.get(
            "kubernetes.io/config.mirror"
        ):
            logger.info(f"Skipping mirror pod {pod.metadata.namespace}/{pod.metadata.name}")
            return False
        if pod.metadata.owner_references is None:
            return True
        for ref in pod.metadata.owner_references:
            if ref.controller is not None and ref.controller and ref.kind == "DaemonSet":
                logger.info(f"Skipping DaemonSet {pod.metadata.namespace}/{pod.metadata.name}")
                return False
        return True

    def get_evictable_pods(self, node_name):
        """Removes all pods from the specified node"""
        field_selector = "spec.nodeName=" + node_name
        pods = self.core_v1_api.list_pod_for_all_namespaces(
            watch=False, field_selector=field_selector
        )
        return [pod for pod in pods.items if self.pod_is_evicatable(pod)]

    def drain(self, node_name):
        logger.info(f"Start draining node: {node_name}")

        pods = self.get_evictable_pods(node_name)

        logger.debug(f"Number of pods to delete: {str(len(pods))}")

        self.evict_until_completed(pods)
        self.wait_until_empty(node_name)

    def evict_pods(self, pods):
        remaining = []
        for pod in pods:
            logger.info(f"Evicting pod {pod.metadata.name} in namespace {pod.metadata.namespace}")
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
                self.core_v1_api.create_namespaced_pod_eviction(
                    pod.metadata.name, pod.metadata.namespace, body
                )
            except ApiException as e:
                if e.status == 429:
                    remaining.append(pod)
                    logger.waring(
                        f"Pod {pod.metadata.namespace}/{pod.metadata.name} "
                        "could not be evicted due to disruption budget. Will retry."
                    )
                else:
                    logger.exception(
                        "Unexpected error when evicting "
                        f"{pod.metadata.namespace}/{pod.metadata.name}"
                    )
            except:
                logger.exception(
                    "Unexpected error when evicting" f"{pod.metadata.namespace}/{pod.metadata.name}"
                )
        return remaining

    def evict_until_completed(self, pods):
        pending = pods
        while True:
            pending = self.evict_pods(pending)
            if (len(pending)) <= 0:
                return
            time.sleep(INTERVAL)

    def wait_until_empty(self, node_name):
        timeout = self.timeout(self.action_timeout)
        logger.info("Waiting for evictions to complete")
        while True:
            pods = self.get_evictable_pods(node_name)
            if len(pods) <= 0:
                logger.info("All pods evicted successfully")
                return
            if time.time() > timeout:
                logger.error(
                    "All pods were not be evicted during the specified time. Hence aborting..."
                )
            logger.debug(
                "Still waiting for deletion of the following pods: "
                f"{', '.join(map(lambda pod: pod.metadata.namespaace + '/' + pod.metadata.name, pods))}"
            )
            time.sleep(INTERVAL)

    def get_pending_pods(self):
        pods = self.core_v1_api.list_pod_for_all_namespaces(watch=False)
        return [pod for pod in pods.items if pod.status.phase == "Pending"]

    def wait_until_pods_scheduled(self):
        timeout = self.timeout(self.action_timeout)
        while True:
            pods = self.get_pending_pods()
            if len(pods) <= 0:
                logger.info("All pods scheduled successfully")
                return
            if time.time() > timeout:
                logger.error(
                    "All pods were not scheduled during the specified time. Hence aborting..."
                )
            logger.debug(
                f"Still waiting for the pods to be scheduled: "
                f"{', '.join(map(lambda pod: pod.metadata.namespaace + '/' + pod.metadata.name, pods))}"
            )
            time.sleep(INTERVAL)

    def timeout(self, minutes):
        timeout = time.time() + 60 * minutes
        return timeout

    def detect_no_schedule_tolerations(self):
        pods = self.core_v1_api.list_pod_for_all_namespaces().items()

        no_schedule_pods = [
            pod.metadata.name
            for pod in pods
            if pod.spec.tolerations is not None
            for toleration in pod.spec.tolerations
            if toleration.effect == "NoSchedule" and toleration.operator == "Exists"
            for ref in pod.metadata.owner_references
            if ref.controller is not None and ref.controller and ref.kind != "DaemonSet"
        ]

        if len(no_schedule_pods) > 0:
            logger.error(
                "Pods have been found having 'NoSchedule' tolerations. "
                f"This is preventing node draining: {(', ').join(no_schedule_pods)}"
            )
            sys.exit(1)

    def extract_karpenter_instance_ids(self, namespace="karpenter"):
        try:
            pods = self.core_v1_api.list_namespaced_pod(
                namespace=namespace, label_selector="app.kubernetes.io/name=karpenter"
            ).items
        except client.exceptions.ApiException as e:
            logger.error(e)
            sys.exit(1)

        instance_ids = [self.extract_instance_id_from_node(pod.spec.node_name) for pod in pods]
        logger.info(f"Instances that have Karpenter running: {(', ').join(instance_ids)}")
        return instance_ids

    def extract_instance_id_from_node(self, node_name: str) -> str:
        try:
            instance_id = self.core_v1_api.read_node(node_name).spec.provider_id.split("/")[-1]
        except client.exceptions.ApiException as e:
            logger.error(e)
            sys.exit(1)
        return instance_id
