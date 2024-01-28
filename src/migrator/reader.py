import yaml


class Reader:
    def __init__(self, config: str) -> None:
        self.config = config

    def read_config(self) -> object:
        """Reads yaml config file and returns a dictionary"""
        with open(self.config, encoding="utf8") as file:
            return yaml.safe_load(file)

    def namespace(self) -> str:
        """returns kubernetes namespace provided in the config"""
        return self.read_config()["namespace"]

    def deployment(self) -> str:
        """returns deployment name provided in the config"""
        return self.read_config()["deployment"]

    def node_group(self) -> list:
        """returns node groups provided in the config"""
        return self.read_config()["nodeGroups"]
