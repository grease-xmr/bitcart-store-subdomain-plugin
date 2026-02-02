import os
import tempfile
from typing import cast

from dishka import FromDishka
from fastapi import APIRouter, FastAPI, HTTPException, Security

from api import models, utils
from api.constants import AuthScopes
from api.db import AsyncSession
from api.plugins import BasePlugin, DIRoute, get_plugin_logger
from api.services.crud.stores import StoreService
from api.settings import Settings

from .schemas import SlugInput, SlugOutput, SubdomainRoutingSettings

logger = get_plugin_logger(__name__)


SLUG_METADATA_KEY = "store-subdomains:slug"


class Plugin(BasePlugin):
    name = "store-subdomains"

    def setup_app(self, app: FastAPI) -> None:
        router = APIRouter(route_class=DIRoute, prefix="/stores", tags=["stores"])

        @router.patch("/{store_id}/slug", response_model=SlugOutput)
        async def set_slug(
            store_id: str,
            slug_input: SlugInput,
            session: FromDishka[AsyncSession],
            settings: FromDishka[Settings],
            store_service: FromDishka[StoreService],
            user: models.User = Security(utils.authorization.auth_dependency, scopes=[AuthScopes.STORE_MANAGEMENT]),
        ) -> SlugOutput:
            store = await store_service.get(store_id, user)
            slug = slug_input.slug

            plugin_settings = await self._get_settings()

            if slug in plugin_settings.reserved_subdomains:
                raise HTTPException(400, f"Slug '{slug}' is reserved")

            existing_store = await self._find_store_by_slug(session, slug)
            if existing_store and existing_store.id != store_id:
                raise HTTPException(400, f"Slug '{slug}' is already in use")

            store.meta[SLUG_METADATA_KEY] = slug
            await session.flush()

            await self._regenerate_map_file(session, settings)

            return SlugOutput(slug=slug, store_id=store.id)

        @router.delete("/{store_id}/slug", response_model=SlugOutput)
        async def delete_slug(
            store_id: str,
            session: FromDishka[AsyncSession],
            settings: FromDishka[Settings],
            store_service: FromDishka[StoreService],
            user: models.User = Security(utils.authorization.auth_dependency, scopes=[AuthScopes.STORE_MANAGEMENT]),
        ) -> SlugOutput:
            store = await store_service.get(store_id, user)

            if SLUG_METADATA_KEY in store.meta:
                del store.meta[SLUG_METADATA_KEY]
                await session.flush()

            await self._regenerate_map_file(session, settings)

            return SlugOutput(slug=None, store_id=store.id)

        @router.get("/by-slug/{slug}", response_model=SlugOutput)
        async def get_store_by_slug(
            slug: str,
            session: FromDishka[AsyncSession],
        ) -> SlugOutput:
            store = await self._find_store_by_slug(session, slug)
            if not store:
                raise HTTPException(404, f"No store found with slug '{slug}'")

            return SlugOutput(slug=slug, store_id=store.id)

        app.include_router(router)

    async def startup(self) -> None:
        logger.info("store-subdomains plugin starting")

        self.register_settings(SubdomainRoutingSettings)

        self.context.register_hook("db_create_store", self._on_store_change)
        self.context.register_hook("db_modify_store", self._on_store_modify)
        self.context.register_hook("db_delete_store", self._on_store_change)

        settings = await self.container.get(Settings)
        async with self.container() as request_container:
            session = await request_container.get(AsyncSession)
            await self._regenerate_map_file(session, settings)

        logger.info("store-subdomains plugin started successfully")

    async def shutdown(self) -> None:
        logger.info("store-subdomains plugin shutting down")

    async def worker_setup(self) -> None:
        pass

    async def _on_store_change(self, store: models.Store) -> None:
        settings = await self.container.get(Settings)
        async with self.container() as request_container:
            session = await request_container.get(AsyncSession)
            await self._regenerate_map_file(session, settings)

    async def _on_store_modify(self, store: models.Store, old_store: models.Store) -> None:
        old_slug = old_store.meta.get(SLUG_METADATA_KEY)
        new_slug = store.meta.get(SLUG_METADATA_KEY)

        if old_slug != new_slug:
            settings = await self.container.get(Settings)
            async with self.container() as request_container:
                session = await request_container.get(AsyncSession)
                await self._regenerate_map_file(session, settings)

    async def _find_store_by_slug(self, session: AsyncSession, slug: str) -> models.Store | None:
        from sqlalchemy import select

        stmt = select(models.Store).where(models.Store.meta[SLUG_METADATA_KEY].astext == slug)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_all_slugs(self, session: AsyncSession) -> list[tuple[str, str]]:
        from sqlalchemy import select

        stmt = select(models.Store.id, models.Store.meta[SLUG_METADATA_KEY].astext).where(
            models.Store.meta[SLUG_METADATA_KEY].astext.isnot(None), models.Store.meta[SLUG_METADATA_KEY].astext != ""
        )
        result = await session.execute(stmt)
        return [(row[0], row[1]) for row in result.fetchall() if row[1]]

    async def _get_settings(self) -> SubdomainRoutingSettings:
        plugin_settings = await self.get_plugin_settings()
        if plugin_settings is None:
            return SubdomainRoutingSettings()
        return cast(SubdomainRoutingSettings, plugin_settings)

    async def _regenerate_map_file(self, session: AsyncSession, settings: Settings) -> None:
        plugin_settings = await self._get_settings()

        if not plugin_settings.enabled:
            logger.debug("store-subdomains is disabled, skipping map file regeneration")
            return

        data_dir = self.data_dir()
        map_file_path = os.path.join(data_dir, plugin_settings.map_file_name)

        slugs = await self._get_all_slugs(session)

        lines = [f"{slug} {store_id};" for store_id, slug in slugs]
        content = "\n".join(lines) + ("\n" if lines else "")

        self._atomic_write(map_file_path, content)

        logger.info(f"Regenerated subdomain map file with {len(slugs)} entries")

    def _atomic_write(self, path: str, content: str) -> None:
        dir_name = os.path.dirname(path)
        try:
            fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix=".tmp_")
            try:
                os.write(fd, content.encode("utf-8"))
                os.fsync(fd)
            finally:
                os.close(fd)

            os.replace(tmp_path, path)
        except Exception:
            if "tmp_path" in locals():
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            raise
