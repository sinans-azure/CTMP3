# =============================================================================
# Database Module — Main Configuration
# =============================================================================
# Provisions Azure Database for PostgreSQL Flexible Server inside a private VNet,
# stores credentials in Key Vault, and configures private DNS resolution.
# =============================================================================

resource "random_password" "pg_admin_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "azurerm_private_dns_zone" "pg" {
  name                = "${var.prefix}-pg-dns.postgres.database.azure.com"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "pg" {
  name                  = "${var.prefix}-pg-dns-link"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.pg.name
  virtual_network_id    = var.vnet_id
  registration_enabled  = false
  tags                  = var.tags
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                          = "${var.prefix}-pg-server"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  version                       = "14"
  delegated_subnet_id           = var.pg_subnet_id
  private_dns_zone_id           = azurerm_private_dns_zone.pg.id
  administrator_login          = var.admin_username
  administrator_password       = random_password.pg_admin_password.result

  storage_mb = 32768
  sku_name   = var.sku_name

  public_network_access_enabled = false

  backup_retention_days        = 7
  geo_redundant_backup_enabled = false
  auto_grow_enabled            = true

  tags = var.tags

  lifecycle {
    ignore_changes = [
      zone,
    ]
  }

  depends_on = [
    azurerm_private_dns_zone_virtual_network_link.pg
  ]
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = var.db_name
  server_id = azurerm_postgresql_flexible_server.main.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

resource "azurerm_key_vault_secret" "pg_password" {
  name         = "pg-admin-password"
  value        = random_password.pg_admin_password.result
  key_vault_id = var.key_vault_id
}

resource "azurerm_key_vault_secret" "pg_conn_str" {
  name         = "pg-connection-string"
  value        = "postgresql://${var.admin_username}:${random_password.pg_admin_password.result}@${azurerm_postgresql_flexible_server.main.fqdn}/${var.db_name}"
  key_vault_id = var.key_vault_id
}
