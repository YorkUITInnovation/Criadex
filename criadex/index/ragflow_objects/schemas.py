"""
This file is part of Criadex.

Criadex is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Criadex is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Criadex. If not, see <https://www.gnu.org/licenses/>.

@package    Criadex
@author     kiarash b
@copyright  2025 onwards York University (https://yorku.ca/)
@repository https://github.com/YorkUITInnovation/Criadex
@license    https://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
"""
from typing import List, Dict, Any, Optional

from typing import Dict, Any, Optional, List, Union
import asyncio

FILE_NAME_META_STR = "file_name"
FILE_CREATED_AT_META_STR = "created_at"
FILE_GROUP_META_STR = "group_name"
FILE_GROUP_ID_META_STR = "group_id"

TOKEN_COUNT_METADATA_KEY = "token_count"

class RagflowTransformComponent:
    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        self.name = name
        self.params = params or {}

class RagflowBaseNode:
    def __init__(self, id_: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        self.id_ = id_
        self.text = text
        self.metadata = metadata or {}

class RagflowTextNode(RagflowBaseNode):
    pass

class RagflowIndexNode(RagflowBaseNode):
    def __init__(self, id_: str, text: str, index_id: str, metadata: Optional[Dict[str, Any]] = None):
        super().__init__(id_, text, metadata)
        self.index_id = index_id

class RagflowNodeWithScore:
    def __init__(self, node: RagflowBaseNode, score: float, metadata: Optional[Dict[str, Any]] = None):
        self.node = node
        self.score = score
        self.metadata = metadata or {}

class RagflowNodeRelationship:
    SOURCE = "source"

class RagflowReranker:
    def __init__(self, model_name: str = "default", params: Optional[Dict[str, Any]] = None):
        self.model_name = model_name
        self.params = params or {}

class RagflowDocument:
    def __init__(self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        self.doc_id = doc_id
        self.text = text
        self.metadata = metadata or {}

    def add_metadata(self, file_name=None, created_at=None, group_name=None, group_id=None):
        if file_name:
            self.metadata[FILE_NAME_META_STR] = file_name
        if created_at:
            self.metadata[FILE_CREATED_AT_META_STR] = created_at
        if group_name:
            self.metadata[FILE_GROUP_META_STR] = group_name
        if group_id:
            self.metadata[FILE_GROUP_ID_META_STR] = group_id
        return self

class RagflowQuery:
    def __init__(self, query_text: str, filters: Optional[Dict[str, Any]] = None):
        self.query_text = query_text
        self.filters = filters or {}

    def add_filter(self, filter_dict: Dict[str, Any]):
        # Merge with existing filters
        for k, v in filter_dict.items():
            if k in self.filters and isinstance(self.filters[k], list):
                self.filters[k].extend(v if isinstance(v, list) else [v])
            else:
                self.filters[k] = v
        return self

    async def afilter(self, filter_dict: Dict[str, Any]):
        # Async filter addition
        self.add_filter(filter_dict)
        return self
