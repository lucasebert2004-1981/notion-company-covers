import base64
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests
from openai import OpenAI

REPO = os.environ.get("GITHUB_REPOSITORY", "lucasebert2004-1981/notion-company-covers")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
COVERS_DIR = Path("covers")
COMPANIES_FILE = Path(os.environ.get("COMPANIES_FILE", "companies.json"))
MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")
IMAGE_SIZE = os.environ.get("OPENAI_IMAGE_SIZE", "1536x864")
NOTION_VERSION = os.environ.get("NOTION_VERSION", "2022-06-28")

STYLE_REFERENCE = """
Create a premium horizontal Notion cover image in the same family as the reference covers: clean, polished, cinematic corporate-tech art, widescreen composition, strong company branding, realistic or semi-realistic environment, subtle lighting, premium materials, and a modern workspace or sector-relevant scene. The logo/company name must be prominent and legible. Avoid clutter, watermarks, captions, or infographic layouts.
""".strip()


def load_companies() -> List[Dict[str, Any]]:
    with COMPANIES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def selected_companies(companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    only = os.environ.get("ONLY_TICKERS", "").strip()
    if not only:
        return companies
    wanted = {x.strip().upper() for x in only.split(",") if x.strip()}
    return [c for c in companies if c.get("ticker", "").upper() in wanted]


def prompt_for(company: Dict[str, Any]) -> str:
    ticker = company["ticker"]
    name = company["name"]
    theme = company.get("theme", "premium corporate technology environment")
    return f"""
{STYLE_REFERENCE}

Company: {name} ({ticker})
Theme/context: {theme}

Design requirements:
- Use a 16:9 horizontal composition suitable for a Notion page cover.
- Put the {name} brand/logo or clearly legible text \"{name}\" as the hero element.
- Make the identity unmistakable but keep the overall image tasteful and premium.
- The scene should visually relate to the company's business and sector.
- Use brand-appropriate colors and cinematic lighting.
- No extra captions, no fake UI labels except tasteful sector-relevant interface details, no watermark.
""".strip()


def generate_image(client: OpenAI, company: Dict[str, Any]) -> bytes:
    result = client.images.generate(
        model=MODEL,
        prompt=prompt_for(company),
        size=IMAGE_SIZE,
        n=1,
    )
    image_b64 = result.data[0].b64_json
    if not image_b64:
        raise RuntimeError(f"No image data returned for {company['ticker']}")
    return base64.b64decode(image_b64)


def notion_headers() -> Dict[str, str]:
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise RuntimeError("NOTION_TOKEN is not set")
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def update_notion_cover(page_id: str, image_url: str) -> None:
    if not page_id:
        return
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {"cover": {"type": "external", "external": {"url": image_url}}}
    resp = requests.patch(url, headers=notion_headers(), json=payload, timeout=30)
    if resp.status_code >= 300:
        raise RuntimeError(f"Notion update failed for {page_id}: {resp.status_code} {resp.text}")


def raw_url(ticker: str) -> str:
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/covers/{ticker}.png"


def main() -> None:
    COVERS_DIR.mkdir(exist_ok=True)
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    companies = selected_companies(load_companies())
    if not companies:
        raise RuntimeError("No companies selected")

    for company in companies:
        ticker = company["ticker"].upper()
        out = COVERS_DIR / f"{ticker}.png"
        print(f"Generating {ticker} - {company['name']}...")
        data = generate_image(client, company)
        out.write_bytes(data)
        print(f"Wrote {out} ({len(data):,} bytes)")
        if company.get("page_id"):
            url = raw_url(ticker)
            print(f"Updating Notion cover for {ticker}: {url}")
            update_notion_cover(company["page_id"], url)
        time.sleep(1)


if __name__ == "__main__":
    main()
