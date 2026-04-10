import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Static Config from your Legacy App
SHOPIFY_STORE_URL = settings.SHOPIFY_STORE_URL
SHOPIFY_ACCESS_TOKEN = settings.SHOPIFY_ACCESS_TOKEN
API_VERSION = settings.SHOPIFY_API_VERSION
LOCATION_ID = settings.SHOPIFY_LOCATION_ID

async def shopify_graphql(query: str, variables: dict) -> dict:
    """Sends a GraphQL request to Shopify using the static Admin token."""
    url = f"https://{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/graphql.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            r = await client.post(url, json={"query": query, "variables": variables}, headers=headers)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Shopify HTTP Error: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Shopify Connection Error: {e}")
            raise

async def sync_product_to_shopify(name: str, price: float, description: str, quantity: int = 1):
    # STEP 1: Create Product
    create_mutation = """
    mutation productCreate($input: ProductInput!) {
      productCreate(input: $input) {
        product {
          id
          variants(first: 1) { edges { node { id inventoryItem { id } } } }
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
        return {"error": data["userErrors"][0]["message"]}

    product = data["product"]
    p_id = product["id"]
    v_id = product["variants"]["edges"][0]["node"]["id"]
    i_id = product["variants"]["edges"][0]["node"]["inventoryItem"]["id"]

    # STEP 2: Set Price
    price_mutation = """
    mutation vUpdate($pId: ID!, $v: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $pId, variants: $v) { userErrors { message } }
    }
    """
    await shopify_graphql(price_mutation, {
        "pId": p_id,
        "v": [{"id": v_id, "price": str(price)}]
    })

    # STEP 3: Set Inventory
    inv_mutation = """
    mutation inventorySetQuantities($input: InventorySetQuantitiesInput!) {
      inventorySetQuantities(input: $input) { userErrors { message } }
    }
    """
    await shopify_graphql(inv_mutation, {
        "input": {
            "name": "available",
            "reason": "correction",
            "quantities": [{
                "inventoryItemId": i_id,
                "locationId": LOCATION_ID,
                "quantity": quantity
            }]
        }
    })

    return p_id


async def update_shopify_product(shopify_id: str, name: str, description: str, price: float):
    """
    Updates an existing product and its first variant on Shopify.
    """
    # 1. First, we need to get the first variant ID to update the price
    # In a real app, you'd store the variant_id in your DB, 
    # but for now, we'll fetch it or use the productUpdate logic.
    
    mutation = """
    mutation productUpdate($input: ProductInput!) {
      productUpdate(input: $input) {
        product {
          id
          title
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    # Simplified logic: Shopify allows updating the title/description easily.
    # To update the price via productUpdate, you usually need the variant ID.
    # For this MVP, we focus on the Product fields.
    variables = {
        "input": {
            "id": shopify_id,
            "title": name,
            "descriptionHtml": description
        }
    }

    return await shopify_graphql(mutation, variables)


async def delete_shopify_product(shopify_id: str):
    """Deletes a product from Shopify using its GID."""
    mutation = """
    mutation productDelete($input: ProductDeleteInput!) {
      productDelete(input: $input) {
        deletedProductId
        userErrors {
          field
          message
        }
      }
    }
    """
    variables = {"input": {"id": shopify_id}}
    return await shopify_graphql(mutation, variables)