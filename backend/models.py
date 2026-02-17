from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from backend.database import Base

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String)
    
    # Relationships - one category can have many products and sellers
    products = relationship("Product", back_populates="category")
    sellers = relationship("Seller", back_populates="category")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    contact_number = Column(String)
    address_line_1 = Column(String, nullable=False)
    address_line_2 = Column(String, nullable=False)
    address_line_3 = Column(String, nullable=False)

class Seller(Base):
    __tablename__ = "sellers"
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    contact_number = Column(String)
    address_line_1 = Column(String, nullable=False)
    address_line_2 = Column(String, nullable=False)
    address_line_3 = Column(String, nullable=False)
    
    # Relationships - one seller has one category, one seller can have many products
    category = relationship("Category", back_populates="sellers")
    products = relationship("Product", back_populates="seller")

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    contact_number = Column(String)
    address_line_1 = Column(String, nullable=False)
    address_line_2 = Column(String, nullable=False)
    address_line_3 = Column(String, nullable=False)
    
    # Relationship - one company can have many products
    products = relationship("Product", back_populates="company")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    seller_id = Column(Integer, ForeignKey('sellers.id'), nullable=False)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    description = Column(String, nullable=True)
    
    # Relationships - link to category, seller, and company
    category = relationship("Category", back_populates="products")
    seller = relationship("Seller", back_populates="products")
    company = relationship("Company", back_populates="products")