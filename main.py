import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Order, OrderItem

app = FastAPI(title="HNG PACKAGING SOLUTION API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "HNG PACKAGING SOLUTION backend is running"}

# Helper to convert ObjectId to string

def serialize_doc(doc):
    if not doc:
        return doc
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc

# Seed some sample products if collection empty
@app.post("/seed")
def seed_products():
    try:
        count = db["product"].count_documents({}) if db else 0
        if count > 0:
            return {"message": "Products already seeded", "count": count}
        sample = [
            {
                "title": "Corrugated Boxes - Small",
                "description": "Durable small corrugated boxes for light shipments.",
                "price": 12.99,
                "category": "Boxes",
                "image": "https://images.unsplash.com/photo-1585166276991-9a6f4018f3a0",
                "in_stock": True,
            },
            {
                "title": "Bubble Wrap Roll",
                "description": "High-quality bubble wrap for fragile items.",
                "price": 19.5,
                "category": "Protective",
                "image": "https://images.unsplash.com/photo-1585386959984-a4155223168f",
                "in_stock": True,
            },
            {
                "title": "Packing Tape - Heavy Duty",
                "description": "Strong adhesive packing tape for secure sealing.",
                "price": 4.75,
                "category": "Tape",
                "image": "https://images.unsplash.com/photo-1516637090014-cb1ab0d08fc7",
                "in_stock": True,
            },
        ]
        for p in sample:
            create_document("product", p)
        return {"message": "Seeded sample products", "count": len(sample)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Products endpoints
@app.get("/products")
def list_products(category: Optional[str] = None):
    try:
        query = {"category": category} if category else {}
        docs = get_documents("product", query)
        return [serialize_doc(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/products")
def create_product(product: Product):
    try:
        new_id = create_document("product", product)
        return {"id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Orders endpoint
class CreateOrderRequest(Order):
    pass

@app.post("/orders")
def create_order(order: CreateOrderRequest):
    try:
        # Compute total
        total = 0.0
        for item in order.items:
            prod = db["product"].find_one({"_id": ObjectId(item.product_id)}) if db else None
            if not prod:
                raise HTTPException(status_code=404, detail=f"Product not found: {item.product_id}")
            total += float(prod.get("price", 0)) * item.quantity
        order_dict = order.model_dump()
        order_dict["total_amount"] = round(total, 2)
        new_id = create_document("order", order_dict)
        return {"id": new_id, "total": order_dict["total_amount"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
