import posixpath
import re

from pydantic import field_validator, model_validator

from api.schemas.base import Schema

HOSTNAME_RE = re.compile(r"^([a-z0-9]([a-z0-9-]*[a-z0-9])?\.)*[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
SUBDOMAIN_LABEL_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
FILENAME_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")
STATIC_SITES_PREFIX = "/var/statics/"


class SubdomainRoutingSettings(Schema):
    enabled: bool = True
    reserved_subdomains: list[str] = ["www", "api", "admin", "store", "mail", "ftp", "static"]
    base_domain: str = "local"  # base domain for generating server_name in static_sites
    map_file_name: str = "subdomain_store.map"
    static_redirects_file_name: str = "static_redirects.map"
    static_redirects: dict[str, str] = {}  # subdomain -> target URL
    static_sites_file_name: str = "static_sites.conf"
    static_sites: dict[str, str] = {}  # subdomain -> directory path

    @field_validator("base_domain")
    @classmethod
    def validate_base_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if not HOSTNAME_RE.match(v):
            raise ValueError(f"Invalid base_domain: must be a valid hostname, got '{v}'")
        return v

    @field_validator("map_file_name", "static_redirects_file_name", "static_sites_file_name")
    @classmethod
    def validate_file_names(cls, v: str) -> str:
        if not FILENAME_RE.match(v):
            raise ValueError(f"Invalid file name '{v}': must match [a-z0-9][a-z0-9_.-]* with no path separators")
        return v

    @model_validator(mode="after")
    def validate_static_sites(self) -> "SubdomainRoutingSettings":
        validated = {}
        for subdomain, path in self.static_sites.items():
            sub = subdomain.strip().lower()
            if not SUBDOMAIN_LABEL_RE.match(sub):
                raise ValueError(f"Invalid static_sites subdomain '{subdomain}': must be a valid subdomain label")
            if not path.startswith("/"):
                raise ValueError(f"Invalid static_sites path '{path}': must be an absolute path")
            normalised = posixpath.normpath(path)
            if not normalised.startswith(STATIC_SITES_PREFIX.rstrip("/")):
                raise ValueError(f"Invalid static_sites path '{path}': must be under {STATIC_SITES_PREFIX}")
            validated[sub] = normalised
        self.static_sites = validated
        return self

    @model_validator(mode="after")
    def validate_static_redirects(self) -> "SubdomainRoutingSettings":
        validated = {}
        for subdomain, url in self.static_redirects.items():
            sub = subdomain.strip().lower()
            if not SUBDOMAIN_LABEL_RE.match(sub):
                raise ValueError(f"Invalid static_redirects subdomain '{subdomain}': must be a valid subdomain label")
            if not (url.startswith("http://") or url.startswith("https://")):
                raise ValueError(f"Invalid static_redirects URL '{url}': must start with http:// or https://")
            if re.search(r"[\n\r;\s]", url):
                raise ValueError(f"Invalid static_redirects URL '{url}': must not contain newlines, semicolons, or whitespace")
            validated[sub] = url
        self.static_redirects = validated
        return self


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
