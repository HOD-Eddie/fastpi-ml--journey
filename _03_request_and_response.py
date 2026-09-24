# Today, I'm gonna cover how to handle data bodies in my routes.
# when client device / user sends info to the server, the data is passed as 
# a request body. 
# When the server sends info back to the user, it is passed as a response body.
# a client can pass data of varioius formats such as text, images etx.
from fastapi import FastAPI, HTTPException, status

from _03_schemas import Product, ResponseBody, Supplier, UpdateProduct

# This in-memory store acts like a lightweight database while we practice API
# contracts. It makes request/response flows easy to reason about without adding
# persistence or a database layer yet.
FAKE_PRODUCTS_DB: list[Product] = [
    Product(
        pid=1,
        name="Ergonomic Mouse",
        description="Wireless mouse with silent clicks.",
        price=45.99,
        supplier=Supplier(sid=1, sname="LogiTech Distributors", email="example@gmail.com")
    ),
    Product(
        pid=2,
        name="UltraWide Monitor",
        description=None, # Testing optional fields
        price=349.50,
        supplier=Supplier(sid=2, sname="ScreenCorp Inc")
    ),
    Product(
        pid=3,
        name="Anker USB-C Cable",
        description="Braided 6ft fast-charging cable.",
        price=12.99,
        supplier=Supplier(sid=3, sname="Anker Logistics", email=None)
    )
]


inst = FastAPI()
@inst.get("/products/", response_model=list[ResponseBody])
def get_products():
    return FAKE_PRODUCTS_DB

@inst.get("/products/{pid}", response_model=ResponseBody)
def get_by_id(pid: int):
    for product in FAKE_PRODUCTS_DB:
        if product.pid == pid:
            return product
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {pid} does not exist")

@inst.post("/products/", response_model=ResponseBody)
def create_product(prod: Product):
    # Duplicate prevention is a classic API rule: we reject conflicts early instead
    # of creating two records that share the same primary key.
    for product in FAKE_PRODUCTS_DB:
        if product.pid == prod.pid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product already exists")

    FAKE_PRODUCTS_DB.append(prod)
    return prod


@inst.put("/products/{pid}", response_model=UpdateProduct)
def update_product_details(pid: int, uprod: UpdateProduct):
    # The update contract is partial: only fields that are supplied in the payload
    # should overwrite the stored record. This keeps the endpoint flexible without
    # requiring the client to resend the entire object.
    for product in FAKE_PRODUCTS_DB:
        if product.pid == pid:
            if uprod.name is not None:
                product.name = uprod.name
            if uprod.description is not None:
                product.description = uprod.description
            if uprod.price is not None:
                product.price = uprod.price
            if uprod.supplier is not None:
                if uprod.supplier.sid is not None:
                    product.supplier.sid = uprod.supplier.sid
                if uprod.supplier.sname is not None:
                    product.supplier.sname = uprod.supplier.sname
                if uprod.supplier.email is not None:
                    product.supplier.email = uprod.supplier.email

            return product
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {pid} doest not exist")


@inst.delete("/products/{pid}")
def delete_product(pid: int):
    for product in FAKE_PRODUCTS_DB:
        if product.pid == pid:
            FAKE_PRODUCTS_DB.remove(product)
            return {"Success": f"Product {pid} removed"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prodduct {pid} does not exist")