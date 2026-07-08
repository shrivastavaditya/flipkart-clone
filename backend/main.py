import csv
import os
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Flipkart Clone API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CART_FILE = os.path.join(os.path.dirname(__file__), "..", "postgres", "cart.csv")
ORDERS_FILE = os.path.join(os.path.dirname(__file__), "..", "postgres", "orders.csv")

PRODUCTS = [
    {"id": "p1", "name": "Apple iPhone 15 Pro", "price": 120000, "category": "Electronics"},
    {"id": "p2", "name": "Samsung Galaxy S24 Ultra", "price": 115000, "category": "Electronics"},
    {"id": "p3", "name": "Sony WH-1000XM5 Headphones", "price": 28000, "category": "Accessories"},
    {"id": "p4", "name": "Nike Air Max Sneakers", "price": 8500, "category": "Fashion"},
    {"id": "p5", "name": "Levi's 501 Original Jeans", "price": 3200, "category": "Fashion"},
]

class CartItem(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int = Field(ge=1)

def init_db():
    if not os.path.exists(CART_FILE):
        os.makedirs(os.path.dirname(CART_FILE), exist_ok=True)
        with open(CART_FILE, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["id", "product_id", "name", "price", "quantity", "created_at"])

def read_cart() -> list[dict]:
    init_db()
    with open(CART_FILE, "r", encoding="utf-8") as file:
        return list(csv.DictReader(file))

def write_cart(rows: list[dict]):
    with open(CART_FILE, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["id", "product_id", "name", "price", "quantity", "created_at"])
        writer.writeheader()
        writer.writerows(rows)

def init_orders_db():
    if not os.path.exists(ORDERS_FILE):
        os.makedirs(os.path.dirname(ORDERS_FILE), exist_ok=True)
        with open(ORDERS_FILE, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["order_id", "total_amount", "created_at"])


CATEGORIES_FILE = os.path.join(os.path.dirname(__file__), "..", "postgres", "categories.csv")

def init_categories_db():
    if not os.path.exists(CATEGORIES_FILE):
        os.makedirs(os.path.dirname(CATEGORIES_FILE), exist_ok=True)
        with open(CATEGORIES_FILE, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["id", "name"])
            writer.writerows([["c1", "Electronics"], ["c2", "Accessories"], ["c3", "Fashion"], ["c4", "Home"]])

@app.get("/api/navigation/categories")
def get_categories():
    init_categories_db()
    with open(CATEGORIES_FILE, "r", encoding="utf-8") as file:
        return list(csv.DictReader(file))

@app.get("/products")
def get_products(q: str = ""):
    if not q:
        return PRODUCTS
    return [p for p in PRODUCTS if q.lower() in p["name"].lower() or q.lower() in p["category"].lower()]

@app.get("/cart")
def get_cart():
    return read_cart()

@app.post("/cart")
def add_to_cart(item: CartItem):
    cart = read_cart()
    for row in cart:
        if row["product_id"] == item.product_id:
            row["quantity"] = str(int(row["quantity"]) + item.quantity)
            write_cart(cart)
            return {"message": "Cart item quantity updated", "item": row}
    
    new_row = {
        "id": f"cart-{os.urandom(4).hex()}",
        "product_id": item.product_id,
        "name": item.name,
        "price": str(item.price),
        "quantity": str(item.quantity),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    cart.append(new_row)
    write_cart(cart)
    return {"message": "Item added to cart", "item": new_row}

@app.post("/checkout")
def checkout():
    cart = read_cart()
    if not cart:
        raise HTTPException(status_code=400, detail="Shopping cart is empty.")
    
    total = sum(float(row["price"]) * int(row["quantity"]) for row in cart)
    
    init_orders_db()
    order_id = f"ord-{os.urandom(4).hex()}"
    with open(ORDERS_FILE, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([order_id, total, datetime.now(timezone.utc).isoformat()])
        
    write_cart([])  # Empty the cart
    return {"message": "Checkout completed successfully!", "order_id": order_id, "total_amount": total, "order_status": "placed"}

from fastapi.responses import PlainTextResponse

@app.get("/invoice/{order_id}", response_class=PlainTextResponse)
def get_invoice(order_id: str):
    init_orders_db()
    with open(ORDERS_FILE, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        order = next((row for row in reader if row["order_id"] == order_id), None)
        
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    invoice_text = (
        "====================================\n"
        "          FLIPKART CLONE\n"
        "====================================\n"
        "             INVOICE\n"
        "------------------------------------\n"
        f"Order ID: {order['order_id']}\n"
        f"Date:     {order['created_at']}\n"
        "------------------------------------\n"
        f"Total Amount Paid: ${order['total_amount']}\n"
        "====================================\n"
        "   Thank you for shopping with us!\n"
        "====================================\n"
    )
    
    return PlainTextResponse(
        content=invoice_text,
        headers={"Content-Disposition": f"attachment; filename=invoice_{order_id}.txt"}
    )
