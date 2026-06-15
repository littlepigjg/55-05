import os
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Callable
from bs4 import BeautifulSoup


class ContentExtractor:
    EPUB_CONTAINER_NS = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
    EPUB_OPF_NS = {
        "opf": "http://www.idpf.org/2007/opf",
        "dc": "http://purl.org/dc/elements/1.1/",
    }
    CHUNK_SIZE = 1024 * 1024

    def __init__(self):
        self._html_re = re.compile(r"<[^>]+>")
        self._whitespace_re = re.compile(r"\s+")

    def extract(self, file_path: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> str:
        ext = Path(file_path).suffix.lower()
        if ext == ".epub":
            return self._extract_epub(file_path, progress_callback)
        elif ext == ".pdf":
            return self._extract_pdf(file_path, progress_callback)
        elif ext == ".mobi":
            return self._extract_mobi(file_path, progress_callback)
        return ""

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = self._html_re.sub(" ", text)
        text = self._whitespace_re.sub(" ", text)
        return text.strip()

    def _extract_epub(self, file_path: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> str:
        content_parts = []
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                opf_path = self._find_opf_path(zf)
                if not opf_path:
                    return ""

                opf_dir = str(Path(opf_path).parent)
                manifest_items = self._get_manifest_items(zf, opf_path)

                total = len(manifest_items)
                for i, item_path in enumerate(manifest_items):
                    if progress_callback:
                        progress_callback(i + 1, total)

                    try:
                        full_path = item_path if opf_dir == "." else f"{opf_dir}/{item_path}"
                        if full_path not in zf.namelist():
                            continue

                        with zf.open(full_path) as f:
                            chunk = f.read(self.CHUNK_SIZE)
                            while chunk:
                                try:
                                    text = chunk.decode("utf-8", errors="ignore")
                                    soup = BeautifulSoup(text, "html.parser")
                                    for script in soup(["script", "style"]):
                                        script.decompose()
                                    content_parts.append(soup.get_text(" ", strip=True))
                                except Exception:
                                    pass
                                chunk = f.read(self.CHUNK_SIZE)
                    except Exception:
                        continue

        except Exception:
            pass

        return self._clean_text(" ".join(content_parts))

    def _find_opf_path(self, zf: zipfile.ZipFile) -> Optional[str]:
        try:
            container = zf.read("META-INF/container.xml").decode("utf-8", errors="ignore")
            root = ET.fromstring(container)
            rootfile = root.find(".//c:rootfile", self.EPUB_CONTAINER_NS)
            if rootfile is not None:
                return rootfile.get("full-path")
        except Exception:
            pass
        return None

    def _get_manifest_items(self, zf: zipfile.ZipFile, opf_path: str) -> list:
        items = []
        try:
            opf_content = zf.read(opf_path).decode("utf-8", errors="ignore")
            root = ET.fromstring(opf_content)

            spine = root.find(".//{http://www.idpf.org/2007/opf}spine")
            manifest = root.find(".//{http://www.idpf.org/2007/opf}manifest")

            if spine is not None and manifest is not None:
                id_to_href = {}
                for item in manifest.findall(".//{http://www.idpf.org/2007/opf}item"):
                    item_id = item.get("id", "")
                    href = item.get("href", "")
                    media_type = item.get("media-type", "")
                    if media_type.startswith("application/xhtml+xml") or media_type == "text/html":
                        id_to_href[item_id] = href

                for itemref in spine.findall(".//{http://www.idpf.org/2007/opf}itemref"):
                    idref = itemref.get("idref", "")
                    if idref in id_to_href:
                        items.append(id_to_href[idref])
        except Exception:
            pass
        return items

    def _extract_pdf(self, file_path: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> str:
        content_parts = []
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(file_path)
            total_pages = len(reader.pages)

            for page_num in range(total_pages):
                if progress_callback:
                    progress_callback(page_num + 1, total_pages)

                try:
                    page = reader.pages[page_num]
                    text = page.extract_text() or ""
                    content_parts.append(text)
                except Exception:
                    continue

        except ImportError:
            return ""
        except Exception:
            pass

        return self._clean_text(" ".join(content_parts))

    def _extract_mobi(self, file_path: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> str:
        content_parts = []
        try:
            file_size = os.path.getsize(file_path)
            with open(file_path, "rb") as f:
                header = f.read(132)
                if len(header) < 132:
                    return ""

                mobi_start = int.from_bytes(header[60:64], "big")
                f.seek(mobi_start)
                mobi_header = f.read(200)
                if len(mobi_header) < 24:
                    return ""

                encoding = int.from_bytes(mobi_header[12:16], "big")
                codec = "utf-8" if encoding == 65001 else "cp1252"

                text_start = int.from_bytes(mobi_header[24:28], "big") + mobi_start
                text_len = int.from_bytes(mobi_header[28:32], "big")

                f.seek(text_start)
                total_chunks = (text_len + self.CHUNK_SIZE - 1) // self.CHUNK_SIZE
                remaining = text_len

                for chunk_num in range(total_chunks):
                    if progress_callback:
                        progress_callback(chunk_num + 1, total_chunks)

                    chunk_size = min(self.CHUNK_SIZE, remaining)
                    chunk = f.read(chunk_size)
                    remaining -= chunk_size

                    try:
                        text = chunk.decode(codec, errors="ignore")
                        content_parts.append(text)
                    except Exception:
                        try:
                            text = chunk.decode("utf-8", errors="ignore")
                            content_parts.append(text)
                        except Exception:
                            pass

        except Exception:
            pass

        return self._clean_text(" ".join(content_parts))
