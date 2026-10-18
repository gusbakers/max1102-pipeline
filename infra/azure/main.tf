terraform {
  required_version = ">= 1.5, < 2.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}
provider "azurerm" {
  features {}
  resource_provider_registrations = "none"
}
variable "location" {
  description = "Exact location returned by az group show. No guessed region."
  type        = string
}
variable "resource_group_name" {
  type    = string
  default = "rg-max-week2-api"
}
variable "service_plan_name" {
  type    = string
  default = "plan-max-week2-free"
}
variable "web_app_name" {
  type    = string
  default = "maxweek2-gusbakers-972358cb"
}
variable "plan_sku" {
  type    = string
  default = "F1"
  validation {
    condition     = var.plan_sku == "F1"
    error_message = "This lab configuration permits only the existing F1 plan."
  }
}
resource "azurerm_resource_group" "api" {
  name     = var.resource_group_name
  location = var.location
  lifecycle {
    prevent_destroy = true
  }
}
resource "azurerm_service_plan" "api" {
  name                = var.service_plan_name
  location            = var.location
  resource_group_name = azurerm_resource_group.api.name
  os_type             = "Linux"
  sku_name            = var.plan_sku
  lifecycle {
    prevent_destroy = true
  }
}
resource "azurerm_linux_web_app" "api" {
  name                = var.web_app_name
  location            = var.location
  resource_group_name = azurerm_resource_group.api.name
  service_plan_id     = azurerm_service_plan.api.id
  https_only          = true
  site_config {
    always_on        = false
    app_command_line = "python -m uvicorn main:app --host 0.0.0.0 --port 8000 --no-access-log"
    application_stack {
      python_version = "3.12"
    }
  }
  lifecycle {
    prevent_destroy = true
    # Credentials and Oryx settings are maintained by the existing app/CD configuration.
    ignore_changes = [app_settings]
  }
}
output "api_url" {
  value = "https://${azurerm_linux_web_app.api.default_hostname}"
}
