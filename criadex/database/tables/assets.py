"""

This file is part of Criadex.

Criadex is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Criadex is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Criadex. If not, see <https://www.gnu.org/licenses/>.

@package    Criadex
@author     Isaac Kogan
@copyright  2024 onwards York University (https://yorku.ca/)
@repository https://github.com/YorkUITInnovation/Criadex
@license    https://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later

"""
import base64
import uuid
from datetime import datetime
from typing import Optional, Tuple, List

from criadex.database.schemas import Table, TableModel
from criadex.index.schemas import RawAsset


class AssetsModel(TableModel):
    """
    A document in the index group

    """

    id: int
    uuid: str
    document_id: int
    group_id: int
    mimetype: str
    data: bytes
    created: datetime

    def to_base64(self) -> str:
        data = self.data
        data_b64 = base64.b64encode(data)
        return data_b64.decode('utf-8')


class Assets(Table):
    """
    Represents a document asset (i.e. image) in the database

    """

    async def insert(
            self,
            group_id: int,
            document_id: int,
            asset: RawAsset
    ) -> str:
        """
        Insert an asset reference into the database

        :param group_id: the index group's primary key
        :param document_id: the document's primary key
        :param asset: Raw asset data
        :return: None

        """

        data_binary = base64.b64decode(asset.data_base64)
        new_uuid = uuid.UUID(asset.uuid)

        async with self.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO Assets (`group_id`, `document_id`, `data`, `mimetype`, `uuid`) VALUES (%s, %s, %s, %s, %s)",
                (group_id, document_id, data_binary, asset.data_mimetype, new_uuid.bytes)
            )

        return str(new_uuid)

    async def delete(
            self,
            document_id: int,
            asset_uuid: str
    ) -> None:
        """
        Delete a document reference from the database

        :param document_id: the document's primary key
        :param asset_uuid: the asset's uuid4
        :return: None
        """

        return await self.delete_many(document_id, asset_uuid)

    async def delete_many(self, document_id: int, *asset_uuids: str) -> None:
        """
        Delete a document reference from the database

        :param document_id: the document's primary key
        :param asset_uuids: The names of the documents to delete
        :return: None
        """

        placeholders: str = ', '.join(['%s'] * len(asset_uuids))

        async with self.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM Assets "
                f"WHERE `document_id`=%s AND `name` IN ({placeholders})",
                (document_id, *[uuid.UUID(asset_uuid).bytes for asset_uuid in asset_uuids])
            )

    async def delete_all_document_assets(self, document_id: int) -> None:
        """
        Delete all document assets

        :param document_id: The doc id
        :return: None

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM Assets "
                "WHERE `document_id`=%s",
                (document_id,)
            )

    async def delete_all_group_assets(self, group_id: int) -> None:
        """
        Delete all group assets

        :param group_id: The group id
        :return: None

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM Assets "
                "WHERE `group_id`=%s",
                (group_id,)
            )

    async def retrieve(self, document_id: int, asset_uuid: str) -> Optional[AssetsModel]:
        """
        Retrieve a document reference from the databased

        :param document_id: the document's primary key
        :param asset_uuid: The name of the document

        :return: Full model of the document

        """

        asset_uuid_bytes = uuid.UUID(asset_uuid).bytes

        async with self.cursor() as cursor:
            await cursor.execute(
                f"SELECT {AssetsModel.to_query_str()} "
                "FROM Assets "
                "WHERE `document_id`=%s AND `uuid`=%s",
                (document_id, asset_uuid_bytes)
            )

            return AssetsModel.from_results(
                await cursor.fetchone()
            )

    async def list(self, document_id: int) -> List[AssetsModel]:
        """
        List the asset references belonging to a given document
        :return: List of document assets

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                f"SELECT {AssetsModel.to_query_str()} "
                "FROM Assets "
                "WHERE `document_id`=%s",
                (document_id,)
            )

            results: Optional[Tuple[tuple]] = await cursor.fetchall()

        return list(
            AssetsModel.from_results(result)
            for result in results
            if result is not None
        ) if results is not None else list()

    async def exists(self, document_id: int, asset_uuid: str) -> bool:
        """
        Check if a given reference to an index document exists

        :param document_id: the document's primary key
        :param asset_uuid: The name of the document
        :return: Whether the document reference exists

        """

        return bool(await self.retrieve(document_id=document_id, asset_uuid=asset_uuid))
