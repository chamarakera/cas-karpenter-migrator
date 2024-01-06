import yaml

class Reader:
    def __init__(self, config: str) -> None:
        self.config = config
        
    def read_config(self) -> object:
        with open(self.config, 'r', encoding="utf8") as file:
            return yaml.safe_load(file)
        
    def namespace(self) -> str:
        return self.read_config()["namespace"]
    
    def deployment(self) -> str:
        return self.read_config()["deployment"]
    
    def node_group(self) -> list:
        return self.read_config()["nodeGroup"]
