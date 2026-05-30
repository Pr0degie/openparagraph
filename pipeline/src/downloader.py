"""Download and extract XML from individual GII law xml.zip files."""
from __future__ import annotations

import io
import logging
import zipfile

import requests

log = logging.getLogger(__name__)

HEADERS = {"User-Agent": "openparagraph/1.0 (research; github.com/openparagraph)"}
TIMEOUT = 60


def fetch_law_xml(zip_url: str, slug: str, session: requests.Session) -> bytes | None:
    """Download xml.zip and return the first XML file's bytes.

    Returns None on network errors, bad zips, or missing XML inside the archive.
    Caller is responsible for writing to disk and for parse errors.
    """
    try:
        r = session.get(zip_url, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.RequestException as exc:
        log.warning("download failed %s: %s", slug, exc)
        return None

    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            xml_names = [n for n in zf.namelist() if n.endswith(".xml")]
            if not xml_names:
                log.warning("no XML in zip for %s", slug)
                return None
            return zf.read(xml_names[0])
    except zipfile.BadZipFile as exc:
        log.warning("bad zip for %s: %s", slug, exc)
        return None
