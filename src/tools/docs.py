"""Feishu/Lark document and drive tools."""

import logging

from lark_oapi.api.docx.v1 import (
    CreateDocumentRequest,
    CreateDocumentRequestBody,
    RawContentDocumentRequest,
)
from lark_oapi.api.drive.v1 import (
    CreateFolderFileRequest,
    CreateFolderFileRequestBody,
    DeleteFileRequest,
    ListFileRequest,
    MoveFileRequest,
    MoveFileRequestBody,
)

from src.lark_client import get_client
from src.logging_utils import content_hash, redact_content
from src.harness.result import api_error, internal_error, param_error, tool_ok
from src.tools.registry import register_tool

log = logging.getLogger("lark_agent.tools.docs")


@register_tool(
    name="search_docs",
    description="Search Feishu documents by keyword. Returns matching document list.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword"},
        },
        "required": ["query"],
    },
    risk_level="read",
)
async def search_docs(query: str) -> dict:
    log.info("Searching docs: %s hash=%s", redact_content(query), content_hash(query))

    try:
        client = get_client()
        req = ListFileRequest.builder().folder_token("").page_size(20).build()
        resp = await client.drive.v1.file.alist(req)

        if not resp.success():
            log.error("Doc list API failed: code=%s msg=%s", resp.code, resp.msg)
            return api_error(f"{resp.msg} (code={resp.code})")

        docs = []
        if resp.data and resp.data.files:
            for f in resp.data.files:
                name = f.name or ""
                if query and query.lower() not in name.lower():
                    continue
                docs.append({
                    "token": f.token,
                    "name": name,
                    "type": f.type,
                    "url": f.url or "",
                    "modified_time": f.modified_time or "",
                })

        return tool_ok({"docs": docs, "count": len(docs)})

    except Exception as e:
        log.exception("search_docs failed")
        return internal_error(str(e))


@register_tool(
    name="read_doc",
    description="Read the full content of a Feishu document.",
    parameters={
        "type": "object",
        "properties": {
            "document_id": {"type": "string", "description": "Document ID"},
        },
        "required": ["document_id"],
    },
    risk_level="read",
)
async def read_doc(document_id: str) -> dict:
    log.info("Reading doc: %s", document_id)

    try:
        client = get_client()
        req = RawContentDocumentRequest.builder().document_id(document_id).build()
        resp = await client.docx.v1.document.araw_content(req)

        if not resp.success():
            log.error("Read doc failed: code=%s msg=%s", resp.code, resp.msg)
            return api_error(f"{resp.msg} (code={resp.code})")

        content = resp.data.content if resp.data else ""
        return tool_ok({"content": content, "document_id": document_id})

    except Exception as e:
        log.exception("read_doc failed")
        return internal_error(str(e))


@register_tool(
    name="create_doc",
    description="Create a new Feishu document.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Document title"},
            "content": {"type": "string", "description": "Document content (plain text)"},
        },
        "required": ["title"],
    },
    risk_level="write",
)
async def create_doc(title: str, content: str = "") -> dict:
    log.info("Creating doc: %s hash=%s", redact_content(title), content_hash(title))

    try:
        client = get_client()
        body = CreateDocumentRequestBody.builder().title(title).build()
        req = CreateDocumentRequest.builder().request_body(body).build()
        resp = await client.docx.v1.document.acreate(req)

        if not resp.success():
            log.error("Create doc failed: code=%s msg=%s", resp.code, resp.msg)
            return api_error(f"{resp.msg} (code={resp.code})")

        doc = resp.data.document if resp.data else None
        doc_id = doc.document_id if doc else None

        return tool_ok({
            "success": True,
            "document_id": doc_id,
            "title": title,
        })

    except Exception as e:
        log.exception("create_doc failed")
        return internal_error(str(e))


@register_tool(
    name="delete_doc",
    description="Delete a Feishu document or drive file. Requires explicit user confirmation.",
    parameters={
        "type": "object",
        "properties": {
            "file_token": {"type": "string", "description": "File token to delete"},
            "file_type": {"type": "string", "description": "File type (docx, doc, sheet, etc.), default docx"},
        },
        "required": ["file_token"],
    },
    risk_level="destructive",
)
async def delete_doc(file_token: str, file_type: str = "docx") -> dict:
    log.info("Deleting doc: token_hash=%s type=%s", content_hash(file_token), file_type)

    try:
        client = get_client()
        req = DeleteFileRequest.builder().file_token(file_token).type(file_type).build()
        resp = await client.drive.v1.file.adelete(req)

        if not resp.success():
            log.error("Delete doc failed: code=%s msg=%s", resp.code, resp.msg)
            return api_error(f"{resp.msg} (code={resp.code})")

        return tool_ok({"success": True, "file_token": file_token, "file_type": file_type})

    except Exception as e:
        log.exception("delete_doc failed")
        return internal_error(str(e))


@register_tool(
    name="move_file",
    description="Move a Feishu drive file to a target folder.",
    parameters={
        "type": "object",
        "properties": {
            "file_token": {"type": "string", "description": "File token to move"},
            "target_folder_token": {"type": "string", "description": "Target folder token"},
            "file_type": {"type": "string", "description": "File type (docx, doc, sheet, etc.), default docx"},
        },
        "required": ["file_token", "target_folder_token"],
    },
    risk_level="write",
)
async def move_file(file_token: str, target_folder_token: str, file_type: str = "docx") -> dict:
    log.info("Moving file: token_hash=%s target_hash=%s type=%s",
             content_hash(file_token), content_hash(target_folder_token), file_type)

    try:
        client = get_client()
        body = MoveFileRequestBody.builder().folder_token(target_folder_token).type(file_type).build()
        req = MoveFileRequest.builder().file_token(file_token).request_body(body).build()
        resp = await client.drive.v1.file.amove(req)

        if not resp.success():
            log.error("Move file failed: code=%s msg=%s", resp.code, resp.msg)
            return api_error(f"{resp.msg} (code={resp.code})")

        return tool_ok({"success": True, "file_token": file_token, "target_folder": target_folder_token})

    except Exception as e:
        log.exception("move_file failed")
        return internal_error(str(e))


@register_tool(
    name="create_folder",
    description="Create a folder in Feishu drive under a specified parent folder.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Folder name"},
            "parent_folder_token": {"type": "string", "description": "Parent folder token (required)"},
        },
        "required": ["name", "parent_folder_token"],
    },
    risk_level="write",
)
async def create_folder(name: str, parent_folder_token: str) -> dict:
    if not parent_folder_token:
        return param_error("parent_folder_token is required to create a folder.")

    log.info("Creating folder: %s parent_hash=%s", redact_content(name), content_hash(parent_folder_token))

    try:
        client = get_client()
        body = (
            CreateFolderFileRequestBody.builder()
            .name(name)
            .folder_token(parent_folder_token)
            .build()
        )
        req = CreateFolderFileRequest.builder().request_body(body).build()
        resp = await client.drive.v1.file.acreate_folder(req)

        if not resp.success():
            log.error("Create folder failed: code=%s msg=%s", resp.code, resp.msg)
            return api_error(f"{resp.msg} (code={resp.code})")

        return tool_ok({
            "success": True,
            "token": resp.data.token if resp.data else None,
            "name": name,
            "url": resp.data.url if resp.data else "",
        })

    except Exception as e:
        log.exception("create_folder failed")
        return internal_error(str(e))
