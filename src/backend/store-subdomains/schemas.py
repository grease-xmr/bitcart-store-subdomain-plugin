import re

from pydantic import field_validator

from api.schemas.base import Schema


class SubdomainRoutingSettings(Schema):
    enabled: bool = True
    reserved_subdomains: list[str] = ["www", "api", "admin", "store", "mail", "ftp", "static"]
    map_file_name: str = "subdomain_store.map"


class SlugInput(Schema):
    slug: str

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        v = v.lower().strip()
        if not (3 <= len(v) <= 63):
            raise ValueError("Slug must be 3-63 characters")
        if not re.match(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$", v):
            raise ValueError("Invalid slug format: must start and end with alphanumeric, may contain hyphens")
        if "--" in v:
            raise ValueError("Invalid slug format: consecutive hyphens not allowed")
        return v


class SlugOutput(Schema):
    slug: str | None
    store_id: str
