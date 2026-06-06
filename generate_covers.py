import base64
import json
import os
from pathlib import Path
from typing import Iterable

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

REPO = os.getenv("GITHUB_REPOSITORY", "lucasebert2004-1981/notion-company-covers")
BRANCH = os.getenv("GITHUB_REF_NAME", "main")
COMPANIES_FILE = Path(os.getenv("COMPANIES_FILE", "companies.json"))
COVERS_DIR = Path("covers")
NOTION_API_BASE = "https://api.notion.com/v1/pages"
NOTION_VERSION = os.getenv("NOTION_VERSION", "2022-06-28")
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
OPENAI_IMAGE_SIZE = os.getenv("OPENAI_IMAGE_SIZE", "1536x864")
RUN_STAGE = os.getenv("RUN_STAGE", "full").strip().lower()
ONLY_TICKERS = os.getenv("ONLY_TICKERS", "")
REQUEST_TIMEOUT = 60

PROMPT_TEMPLATE = (
    "Create a premium horizontal Notion cover image for {name} ({ticker}). "
    "Use a clean, polished, cinematic corporate-tech style, widescreen 16:9 composition, "
    "strong company branding, realistic or semi-realistic environment, subtle lighting, "
    "premium materials, and a sector-relevant scene. The {name} logo or clearly legible "
    "company name must be the hero element. Make the identity unmistakable but tasteful. "
    "Theme/context: {theme}. No extra captions, no watermarks, no busy infographic layout."
)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def load_companies() -> list[dict]:
    if not COMPANIES_FILE.exists():
        raise SystemExit(f"Missing required file: {COMPANIES_FILE}")
    with COMPANIES_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise SystemExit("companies.json must contain a top-level array")
    return data


def parse_only_tickers(raw: str) -> set[str]:
    return {item.strip().upper() for item in raw.split(",") if item.strip()}


def filter_companies(companies: Iterable[dict], only_tickers: set[str]) -> list[dict]:
    if not only_tickers:
        return list(companies)
    return [c for c in companies if c.get("ticker", "").upper() in only_tickers]


def build_prompt(company: dict) -> str:
    return PROMPT_TEMPLATE.format(
        name=company["name"],
        ticker=company["ticker"],
        theme=company.get("theme", "premium corporate technology environment"),
    )


def build_raw_url(ticker: str) -> str:
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/covers/{ticker}.png"


def generate_cover_image(client: OpenAI, company: dict, output_path: Path) -> None:
    prompt = build_prompt(company)
    print(f"[generate] {company['ticker']} - {company['name']}")
    result = client.images.generate(
        model=OPENAI_IMAGE_MODEL,
        prompt=prompt,
        size=OPENAI_IMAGE_SIZE,
        n=1,
    )

    image_data = None
    datum = result.data[0]
    if getattr(datum, "b64_json", None):
        image_data = base64.b64decode(datum.b64_json)
    elif getattr(datum, "url", None):
        response = requests.get(datum.url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        image_data = response.content
    else:
        raise RuntimeError("Image generation response did not include b64_json or url")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_data)
    print(f"[saved] {output_path} ({len(image_data):,} bytes)")


def verify_public_image(url: str) -> bool:
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        return response.status_code == 200 and bool(response.content)
    except requests.RequestException:
        return False


def update_notion_cover(page_id: str, image_url: str, notion_token: str) -> None:
    payload = {
        "cover": {
            "type": "external",
            "external": {
                "url": image_url,
            },
        }
    }
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }
    response = requests.patch(
        f"{NOTION_API_BASE}/{page_id}",
        headers=headers,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"Failed to update Notion cover for page {page_id}: "
            f"{response.status_code} {response.text}"
        )


def main() -> None:
    if RUN_STAGE not in {"full", "generate", "notion"}:
        raise SystemExit("RUN_STAGE must be one of: full, generate, notion")

    companies = filter_companies(load_companies(), parse_only_tickers(ONLY_TICKERS))
    if not companies:
        print("No companies matched the current filter.")
        return

    if RUN_STAGE in {"full", "generate"}:
        client = OpenAI(api_key=require_env("OPENAI_API_KEY"))
        for company in companies:
            ticker = company["ticker"].upper()
            output_path = COVERS_DIR / f"{ticker}.png"
            generate_cover_image(client, company, output_path)

    if RUN_STAGE in {"full", "notion"}:
        notion_token = require_env("NOTION_TOKEN")
        for company in companies:
            ticker = company["ticker"].upper()
            page_id = (company.get("page_id") or "").strip()
            image_url = build_raw_url(ticker)

            if not page_id:
                print(f"[skip] {ticker} has no page_id yet")
                continue

            if not verify_public_image(image_url):
                print(
                    f"[skip] {ticker} raw GitHub URL is not public yet: {image_url}. "
                    "Publish the image before updating Notion."
                )
                continue

            print(f"[notion] Updating cover for {ticker} -> {page_id}")
            update_notion_cover(page_id, image_url, notion_token)
            print(f"[done] Notion cover updated for {ticker}")


if __name__ == "__main__":
    main()
