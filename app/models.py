import enum
import uuid
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# =====================================================================
# 1. ENUMERACIONES (Valores tipados y restringidos por base de datos)
# =====================================================================

class StorageLocation(str, enum.Enum):
    """Ubicaciones físicas de almacenamiento en el hogar."""
    HELADERA = "heladera"
    FREEZER = "freezer"
    ALACENA = "alacena"


class MediaType(str, enum.Enum):
    """Tipo de archivo multimedia adjunto a la receta."""
    IMAGE = "image"
    VIDEO = "video"


# =====================================================================
# 2. USUARIOS Y SISTEMA DE RECETARIOS (COLECCIONES)
# =====================================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relaciones ORM
    pantry_items: Mapped[List["UserPantry"]] = relationship(
        "UserPantry", back_populates="user", cascade="all, delete-orphan"
    )
    created_recipes: Mapped[List["Recipe"]] = relationship(
        "Recipe", back_populates="author"
    )
    recipe_books: Mapped[List["RecipeBook"]] = relationship(
        "RecipeBook", back_populates="user", cascade="all, delete-orphan"
    )


class RecipeBook(Base):
    """
    Colecciones o carpetas de recetas del usuario.
    is_system=True indica que es una carpeta protegida (ej: 'Favoritos') que la app no debe permitir borrar.
    """
    __tablename__ = "recipe_books"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relaciones
    user: Mapped["User"] = relationship("User", back_populates="recipe_books")
    recipes: Mapped[List["RecipeBookItem"]] = relationship(
        "RecipeBookItem", back_populates="book", cascade="all, delete-orphan"
    )

    # Evita que un mismo usuario cree dos carpetas con el mismo nombre
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_book_name"),
    )


class RecipeBookItem(Base):
    """
    Tabla de unión N:M entre RecipeBook y Recipe.
    Permite que una receta esté en varios libros a la vez sin duplicar datos.
    """
    __tablename__ = "recipe_book_items"

    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipe_books.id", ondelete="CASCADE"), primary_key=True
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    book: Mapped["RecipeBook"] = relationship("RecipeBook", back_populates="recipes")
    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="book_associations")


# =====================================================================
# 3. RECETAS, MULTIMEDIA E INGREDIENTES
# =====================================================================

class Ingredient(Base):
    """Catálogo maestro de alimentos e insumos."""
    __tablename__ = "ingredients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(
        String(150), unique=True, index=True, nullable=False
    )
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    default_unit: Mapped[str] = mapped_column(String(50), nullable=False)

    recipe_associations: Mapped[List["RecipeIngredient"]] = relationship(
        "RecipeIngredient", back_populates="ingredient"
    )
    pantry_batches: Mapped[List["UserPantry"]] = relationship(
        "UserPantry", back_populates="ingredient"
    )


class Recipe(Base):
    """Instrucciones y detalles generales de la preparación."""
    __tablename__ = "recipes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    prep_time_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    author: Mapped[Optional["User"]] = relationship("User", back_populates="created_recipes")
    ingredients: Mapped[List["RecipeIngredient"]] = relationship(
        "RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan"
    )
    book_associations: Mapped[List["RecipeBookItem"]] = relationship(
        "RecipeBookItem", back_populates="recipe", cascade="all, delete-orphan"
    )
    media: Mapped[List["RecipeMedia"]] = relationship(
        "RecipeMedia", back_populates="recipe", cascade="all, delete-orphan"
    )


class RecipeMedia(Base):
    """Fotos y videos asociados a una receta (Cloud URLs, orden de carrusel y portada)."""
    __tablename__ = "recipe_media"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    media_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType), default=MediaType.IMAGE, nullable=False
    )
    is_cover: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="media")


class RecipeIngredient(Base):
    """Asociación N:M entre recetas e ingredientes con sus cantidades requeridas."""
    __tablename__ = "recipe_ingredients"

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingredients.id", ondelete="RESTRICT"), primary_key=True
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="ingredients")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="recipe_associations")


# =====================================================================
# 4. INVENTARIO FÍSICO / DESPENSA (GESTIÓN POR LOTES)
# =====================================================================

class UserPantry(Base):
    """
    Lote físico individual de un alimento en la despensa del usuario.
    Permite el algoritmo FIFO, decaimiento post-apertura y control de caducidad.
    """
    __tablename__ = "user_pantry"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    location: Mapped[StorageLocation] = mapped_column(
        Enum(StorageLocation), default=StorageLocation.HELADERA, nullable=False
    )
    expiration_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_open: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="pantry_items")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="pantry_batches")

    # Índices de alto rendimiento para el algoritmo de sugerencia por vencimiento
    __table_args__ = (
        Index("idx_pantry_user_expiration", "user_id", "expiration_date"),
        Index("idx_pantry_user_ingredient", "user_id", "ingredient_id"),
    )