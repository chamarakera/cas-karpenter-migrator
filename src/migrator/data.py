class Data:
    def __init__(self) -> None:
        pass

    def create_instance_status_info(self, instances, status):
        status_info = [
            {"instance_id": instance, "status": status} for instance in instances
        ]
        return status_info
