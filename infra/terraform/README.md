# Terraform local infrastructure demo
This starter uses the Docker provider and creates a local Docker network. It does not provision AWS or any public cloud resources.
Run from this directory after Docker Desktop is running:
```bash
terraform init
terraform plan
terraform apply
```
Destroy the network with `terraform destroy`.
