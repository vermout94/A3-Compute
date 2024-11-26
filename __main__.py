"""An Azure RM Python Pulumi program"""

import pulumi
from pulumi import asset, Config, FileArchive
from pulumi_azure_native import storage, web, resources
from pulumi_azure_native.web import AzureStorageType

# Variables
resource_group_name = "clco-demo-rg"
app_name = "clco-demo-app"
storage_account_name = "clcodemostorage"
config = Config("azure-native")
location = config.get("location") or "WestEurope"

# Create an Azure Resource Group
resource_group = resources.ResourceGroup(resource_group_name, location=location)

# Create a storage account
storage_account = storage.StorageAccount(
    storage_account_name,
    resource_group_name=resource_group.name,
    sku=storage.SkuArgs(name=storage.SkuName.STANDARD_LRS),
    kind=storage.Kind.STORAGE_V2,
    location=location,
    allow_blob_public_access=True,
)


# Get storage account keys
keys = pulumi.Output.all(resource_group.name, storage_account.name).apply(
    lambda args: storage.list_storage_account_keys(resource_group_name=args[0], account_name=args[1])
)
storage_key = keys.apply(lambda key_list: key_list.keys[0].value)


# Create a Blob Container for the application ZIP file
blob_container = storage.BlobContainer(
    "app-container",
    account_name=storage_account.name,
    resource_group_name=resource_group.name,
    public_access=storage.PublicAccess.BLOB,
)


# Use FileArchive to package the application directory
app_directory = "./app"  # Path to your app files
zip_file_asset = FileArchive(app_directory)

# Upload the zip file to Azure Storage
app_blob = storage.Blob(
    "app-blob",
    blob_name="clco-demo.zip",
    resource_group_name=resource_group.name,
    account_name=storage_account.name,
    container_name=blob_container.name,
    source=zip_file_asset,
    type=storage.BlobType.BLOCK,
    content_type="application/zip",
)


# Create a file share for the database
file_share = storage.FileShare(
    "database-share",
    account_name=storage_account.name,
    resource_group_name=resource_group.name,
)


# Create the web app
app_service_plan = web.AppServicePlan(
    "app-service-plan",
    resource_group_name=resource_group.name,
    location=location,
    sku=web.SkuDescriptionArgs(
        name="S1",  # Free tier
        tier="Standard",
    ),
    reserved=True,
)


# Create the Web App
app = web.WebApp(
    app_name,
    resource_group_name=resource_group.name,
    location=location,
    server_farm_id=app_service_plan.id,
    site_config=web.SiteConfigArgs(
        linux_fx_version="PYTHON|3.9",  # Specify Python runtime
        app_command_line='pip install -r /home/site/wwwroot/requirements.txt && FLASK_APP=app.py python -m flask run --host=0.0.0.0 --port=8000',  # Startup command
        app_settings=[
            # Reference the Blob Container URL for the ZIP deployment
            web.NameValuePairArgs(
                name="WEBSITE_RUN_FROM_PACKAGE",
                value=pulumi.Output.concat(
                    "https://", storage_account.name, ".blob.core.windows.net/", blob_container.name, "/clco-demo.zip"
                )
            ),
            # Set the environment variable for the database path
            web.NameValuePairArgs(name="DATABASE_PATH", value="/mnt/datastore/database.db"),
        ],
    ),
    https_only=True,
)



# Export the Web App endpoint
pulumi.export("app_url", app.default_host_name)
pulumi.export("database_mount_path", "/mnt/datastore")
