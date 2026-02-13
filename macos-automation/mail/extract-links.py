#!/usr/bin/env python3
"""Extract HTTP(S) link URLs from an email MIME source file.

Used by search-emails.sh to surface links that are lost when
Mail.app renders HTML emails as plain text.
"""
import email
import re
import sys


def extract_links(source_file: str) -> list[str]:
    with open(source_file) as f:
        msg = email.message_from_file(f)

    urls: list[str] = []
    seen: set[str] = set()
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True)
            if payload:
                charset = part.get_content_charset() or "utf-8"
                html = payload.decode(charset, errors="replace")
                for url in re.findall(r'href=["\']?(https?://[^"\'\s>]+)', html):
                    url = url.replace("&amp;", "&")
                    if url not in seen:
                        seen.add(url)
                        urls.append(url)
    return urls


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: extract-links.py <email-source-file>", file=sys.stderr)
        sys.exit(1)
    for link in extract_links(sys.argv[1]):
        print(link)
