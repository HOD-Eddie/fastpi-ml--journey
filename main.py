# I just learned that, specific routes must be defined before dynamic ones, else, 
# unusual matching will be done leading 422 errors

from fastapi import FastAPI, HTTPException, Path

new_inst = FastAPI()


items = [
    {"item_id":1, "name": "Jorgers", "description": "Cotton jogger", "price": 332},
    {"item_id":2, "name": "Loafers", "description": "designer", "price": 590},
    {"item_id":3, "name": "Jacket", "description": "Balenciaga", "price": 999}
]


# REST endpoints use methods such as
# 1. GEt - to read or retrieve data
# 2. POST - to create new data
# 3. PUT -  to update existing data
# 4. DELETE - to erase existing data.

# fetching all items, endpoint to retrieve all items
@new_inst.get("/items")
async def index():
    return items



# Routing endpoints can work with parameters. There are 2 categories.
# 1. Path Parameters - a parameter is passed into the endpoint url, and then into the functions
# 2. Query Parameters - a parameter is passed into the function, but may not appear in the 
#                       endpoint url

# Example use-case for Query
# fetching a specific item by its name, given the name as a path parameter (this is new route, using a query parameter)
@new_inst.get("/items/by-name")
async def get_item_by_name(name: str):
    for item in items:
        if item["name"] == name:
            return item
    return {"error": "Item not found"}

# Example use-case for Path
# fetching a specific item by its ID, given the item_id as a path parameter
@new_inst.get("/items/{item_id}")
async def get_item(item_id: int = Path(..., description="The ID of the item to retrieve")):
    for item in items:
        if item["item_id"] == item_id:
            return item
    return {"error": "Item not found"}

# Path parameter are more dynamic which means query endpoints must be defined first, before
# Path ones, just uas done above.

#creating a new item, given the item_id, name, description, and price as path parameters
@new_inst.post("/items")
async def create_item(item_id: int, name: str, description: str, price: float):
    for item in items:
        if item["item_id"] == item_id:
            raise HTTPException(status_code=400, detail="Item already exists")
    items.append({"item_id": item_id, "name": name, "description": description, "price": price})
    return {"message": f"{item_id} created successfully"}



# updating route, endpoint to update an item by its ID
@new_inst.put("/items/{item_id}")
async def update_item(item_id: int, name: str, description: str, price: float):
    for item in items:
        if item["item_id"] == item_id:
            if name is not None:
                item["name"] = name
            if description is not None:
                item["description"] = description
            if price is not None:
                item["price"] = price
            return {"message": f"{item_id} updated successfully"}
    raise HTTPException(status_code=404, detail="Item not found")


# deleting route, endpoint to delete an item by its ID
@new_inst.delete("/items/{item_id}")
async def delete_item(item_id: int):
    for item in items:
        if item["item_id"] == item_id:
            items.remove(item)
            return {"message": f"{item_id} deleted successfully"}
    raise HTTPException(status_code=404, detail="Item not found")
 

# items = [
#     {"item_id": 1,
#      "name": "Eddie",
#      "description": "male"}
# ]
# app = FastAPI()

# @app.get("/items/{item_id}")
# async def get_by_item_id(item_id: int):
#     for item in items:
#         if item["item_id"] == item_id:
#             return item
#     return {"Error": "item not found"} 

# @app.post("/items")
# async def add_item(item_id: int, name: str, description: str):
#     for item in items:
#         if item["item_id"] ==  item_id:
#             return {"Error": f"{item_id} already exists"}
#     items.append({"item_id": item_id, "name": name, "description": description})
#     return {"item added successfully"}