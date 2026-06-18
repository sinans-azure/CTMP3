# =============================================================================
# Jumpbox Module — Variables
# =============================================================================

variable "resource_group_name" {
  description = "Name of the resource group."
  type        = string
}

variable "location" {
  description = "Azure region."
  type        = string
}

variable "prefix" {
  description = "Naming prefix."
  type        = string
}

variable "tags" {
  description = "Tags applied to all resources."
  type        = map(string)
  default     = {}
}

variable "subnet_id" {
  description = "Subnet ID of the jumpbox subnet."
  type        = string
}

variable "admin_username" {
  description = "Admin username for the VM."
  type        = string
  default     = "portaladmin"
}


