resource "docker_network" "nexus" {
  name = "nexus-terraform-network"
}
output "network_name" {
  value = docker_network.nexus.name
}
