# cas-karpenter-migrator
Tool for automating the migration from Kubernetes Cluster AutoScaler to Karpenter

```sh
$ poetry install
$ poetry run python src/migrator
```

Assumptions
- You have single multi-AZ node group
- You are using self-managed nodes

further Support:
- Multiple single-AZ node groups 
