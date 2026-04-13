import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Static Config from Settings
SHOPIFY_STORE_URL = settings.SHOPIFY_STORE_URL
SHOPIFY_ACCESS_TOKEN = settings.SHOPIFY_ACCESS_TOKEN
API_VERSION = settings.SHOPIFY_API_VERSION
LOCATION_ID = settings.SHOPIFY_LOCATION_ID

async def shopify_graphql(query: str, variables: dict = None) -> dict:
    """Sends a GraphQL request to Shopify using the Admin token."""
    url = f"https://{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/graphql.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            r = await client.post(url, json={"query": query, "variables": variables or {}}, headers=headers)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Shopify HTTP Error: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Shopify Connection Error: {e}")
            raise

async def sync_product_to_shopify(name: str, price: float, description: str, quantity: int = 1):
    """
    Creates a product and initializes price and inventory.
    Returns a dict with all Shopify GIDs.
    """
    # STEP 1: Create Product
    create_mutation = """
    mutation productCreate($input: ProductInput!) {
      productCreate(input: $input) {
        product {
          id
          variants(first: 1) { 
            edges { 
              node { 
                id 
                inventoryItem { id } 
              } 
            } 
          }
        }
        userErrors { field message }
      }
    }
    """
    res = await shopify_graphql(create_mutation, {
        "input": {"title": name, "descriptionHtml": description, "status": "ACTIVE"}
    })
    
    data = res.get("data", {}).get("productCreate", {})
    if data.get("userErrors"):
        logger.error(f"Shopify productCreate Error: {data['userErrors']}")
        return {"error": data["userErrors"][0]["message"]}

    product = data["product"]
    p_id = product["id"]
    variant_node = product["variants"]["edges"][0]["node"]
    v_id = variant_node["id"]
    i_id = variant_node["inventoryItem"]["id"]

    # STEP 2: Set Price
    price_mutation = """
    mutation vUpdate($pId: ID!, $v: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $pId, variants: $v) { 
        userErrors { message } 
      }
    }
    """
    await shopify_graphql(price_mutation, {
        "pId": p_id,
        "v": [{"id": v_id, "price": str(price)}]
    })

    # STEP 3: Set Inventory Level
    await update_shopify_inventory(i_id, LOCATION_ID, quantity)

    return {
        "shopify_id": p_id,
        "shopify_variant_id": v_id,
        "shopify_inventory_item_id": i_id
    }

async def update_shopify_product(shopify_id: str, name: str, description: str):
    """Updates basic product details on Shopify."""
    mutation = """
    mutation productUpdate($input: ProductInput!) {
      productUpdate(input: $input) {
        product { id title }
        userErrors { field message }
      }
    }
    """
    variables = {
        "input": {
            "id": shopify_id,
            "title": name,
            "descriptionHtml": description
        }
    }
    return await shopify_graphql(mutation, variables)

async def update_shopify_inventory(inventory_item_id: str, location_id: str, quantity: int):
    """Updates the 'available' stock level for a product."""
    mutation = """
    mutation inventorySet($input: InventorySetQuantitiesInput!) {
      inventorySetQuantities(input: $input) {
        inventoryLevels {
          quantities { name quantity }
        }
        userErrors { field message }
      }
    }
    """
    variables = {
        "input": {
            "name": "available",
            "reason": "correction",
            "quantities": [{
                "inventoryItemId": inventory_item_id,
                "locationId": location_id,
                "quantity": quantity
            }]
        }
    }
    return await shopify_graphql(mutation, variables)

async def delete_shopify_product(shopify_id: str):
    """Deletes a product from Shopify using its GID."""
    mutation = """
    mutation productDelete($input: ProductDeleteInput!) {
      productDelete(input: $input) {
        deletedProductId
        userErrors { field message }
      }
    }
    """
    variables = {"input": {"id": shopify_id}}
    return await shopify_graphql(mutation, variables)

async def update_shopify_product_image(shopify_id: str, image_url: str):
    """Uploads an image from a public URL to Shopify's CDN."""
    mutation = """
    mutation productCreateMedia($media: [CreateMediaInput!]!, $productId: ID!) {
      productCreateMedia(media: $media, productId: $productId) {
        media { id status }
        userErrors { field message }
      }
    }
    """
    variables = {
        "productId": shopify_id,
        "media": [{
            "alt": "Product Image",
            "mediaContentType": "IMAGE",
            "originalSource": image_url
        }]
    }
    return await shopify_graphql(mutation, variables)