from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import engine, Base, get_db
from backend import models, schemas

# Create tables in luxline automatically if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Test endpoint
@app.get("/")
def home():
    return {"message": "Luxline API is running!"}

@app.get("/db-test")
def test_db(db: Session = Depends(get_db)):
    result = db.execute("SELECT 1").fetchone()
    return {"database_status": "Connected", "result": result[0]}

# Category endpoints
@app.post("/categories/", response_model=schemas.CategoryResponse)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    new_category = models.Category(name=category.name, description=category.description)
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category

@app.get("/categories/", response_model=list[schemas.CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).all()

# Product endpoints
@app.post("/products/", response_model=schemas.ProductResponse)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    new_product = models.Product(
        category_id=product.category_id,
        seller_id=product.seller_id,
        company_id=product.company_id,
        name=product.name,
        price=product.price,
        description=product.description
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product

@app.get("/products/", response_model=list[schemas.ProductResponse])
def get_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()

# User endpoints
@app.post("/users/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    new_user = models.User(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        password=user.password,
        contact_number=user.contact_number,
        address_line_1=user.address_line_1,
        address_line_2=user.address_line_2,
        address_line_3=user.address_line_3
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/users/", response_model=list[schemas.UserResponse])
def get_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()
