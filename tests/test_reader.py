import os
import unittest

from src.migrator.reader import Reader

TEST_CONFIG = os.path.join(os.path.dirname(__file__), "config.yaml")


class TestReader(unittest.TestCase):
    def setUp(self):
        self.config = Reader(TEST_CONFIG)

    def test_namespace(self):
        self.assertEqual(self.config.namespace(), "kube-system")

    def test_deployment(self):
        self.assertEqual(self.config.deployment(), "cluster-autoscaler")

    def test_node_groups(self):
        for node_group in self.config.node_group():
            self.assertEqual(node_group["name"], "eks-example-node-group")


if __name__ == "__main__":
    unittest.main()
