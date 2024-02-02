import unittest

from src.migrator.nodegroup import NodeGroup

TEST_DATA = [
    {
        "AvailabilityZone": "us-west-2a",
        "HealthStatus": "Healthy",
        "InstanceId": "i-xyz-1",
    },
    {
        "AvailabilityZone": "us-west-2a",
        "HealthStatus": "Healthy",
        "InstanceId": "i-xyz-2",
    },
    {
        "AvailabilityZone": "us-west-2b",
        "HealthStatus": "Healthy",
        "InstanceId": "i-xyz-3",
    },
]


class TestNodeGroup(unittest.TestCase):
    def test_select_instance_az_one(self):
        self.assertEqual(NodeGroup.select_instances(TEST_DATA)[0]["AvailabilityZone"], "us-west-2a")

    def test_select_instance_az_two(self):
        self.assertEqual(NodeGroup.select_instances(TEST_DATA)[1]["AvailabilityZone"], "us-west-2b")


if __name__ == "__main__":
    unittest.main()
