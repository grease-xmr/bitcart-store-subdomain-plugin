import re

from pydantic import field_validator

from api.schemas.base import Schema


class SubdomainRoutingSettings(Schema):
    enabled: bool = True
    reserved_subdomains: list[str] = ["www", "api", "admin", "store", "mail", "ftp", "static"]
    base_domain: str = "local"  # base domain for generating server_name in static_sites
    map_file_name: str = "subdomain_store.map"
    static_redirects_file_name: str = "static_redirects.map"
    static_redirects: dict[str, str] = {}  # subdomain -> target URL
    static_sites_file_name: str = "static_sites.conf"
    static_sites: dict[str, str] = {}  # subdomain -> directory path


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
