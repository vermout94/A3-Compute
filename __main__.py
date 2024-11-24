"""An Azure RM Python Pulumi program"""

import pulumi
from pulumi_azure_native import storage, resources, web
from pulumi import FileAsset

#Configuration
config = pulumi.Config()
location = config.get("location") or "WestEurope"
app_name = config.require("app_name")

storage_config = pulumi.Config("storage")
account_name = storage_config.require("accountName")
sku = storage_config.require("sku")
kind = storage_config.require("kind")

# Create an Azure Resource Group
resource_group = resources.ResourceGroup("resource_group")

# Create an Azure resource (Storage Account)
storage_account = storage.StorageAccount(
    account_name,
    resource_group_name=resource_group.name,
    sku=storage.SkuArgs(name=sku),
    kind=storage.Kind(kind),
    location=resource_group.location,
    allow_blob_public_access=True,
)

# Create a Blob Container
container = storage.BlobContainer(
    "container",
    resource_group_name=resource_group.name,
    account_name=storage_account.name,
    container_name="app",
    public_access=storage.PublicAccess.BLOB,
)

# Upload the pre-zipped application as a Blob
blob = storage.Blob(
    "appzip",
    resource_group_name=resource_group.name,
    account_name=storage_account.name,
    container_name=container.name,
    blob_name="clco-demo.zip",
    type=storage.BlobType.BLOCK,
    source=FileAsset("./clco-demo.zip"),  # Reference the pre-zipped file
)

# Create an App Service Plan
app_service_plan = web.AppServicePlan(
    "appserviceplan",
    resource_group_name=resource_group.name,
    kind="Linux",
    reserved=True,
    sku=web.SkuDescriptionArgs(
        tier="Free",
        name="F1",
    ),
    location=resource_group.location,
)

# Deploy the Web App
app = web.WebApp(
    app_name,
    resource_group_name=resource_group.name,
    server_farm_id=app_service_plan.id,
    site_config=web.SiteConfigArgs(
        linux_fx_version="PYTHON|3.9",
        app_settings=[
            {"name": "WEBSITE_RUN_FROM_PACKAGE", "value": blob.url},
            {"name": "FLASK_ENV", "value": "production"},  # Add environment variables
            {"name": "FLASK_APP", "value": "app.py"},
            {"name": "AZURE_STORAGE_ACCOUNT_NAME", "value": account_name},
            {"name": "AZURE_STORAGE_ACCOUNT_KEY", "value": pulumi.Output.secret(
                storage_account.primary_endpoints.blob
            )},
            {"name": "DATABASE_URL", "value": "sqlite:///database.db"},
        ]
    ),
    location=resource_group.location,
)

# Export the Web App URL
pulumi.export("app_url", pulumi.Output.concat("https://", app.default_host_name))

# Export the resource group name
pulumi.export("resource_group_name", resource_group.name)

# Export the app name
pulumi.export("app_name", app.name)

# Export the Blob URL for debugging
pulumi.export("blob_url", blob.url)





