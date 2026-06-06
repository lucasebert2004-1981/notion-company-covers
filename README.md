# Notion company covers

Automated pipeline to generate premium company cover images, store them in this public GitHub repository, and update the corresponding Notion page covers.

## Setup

Add these repository secrets in GitHub:

- `OPENAI_API_KEY`
- `NOTION_TOKEN`

The Notion integration token must have permission to edit the target company pages.

## How to run

1. Open the **Actions** tab.
2. Choose **Generate Notion Covers**.
3. Click **Run workflow**.
4. Use `only_tickers` to test one or more tickers, for example:
   - `FROG`
   - `FROG,SNOW,PANW`
   - leave empty to generate all companies in `companies.json`.

The workflow will:

1. Generate a 16:9 cover image for each selected company.
2. Save it under `covers/TICKER.png`.
3. Commit the generated image back to the repo.
4. Update the Notion page cover using the GitHub raw URL.

## Configure companies

Edit `companies.json`. Each company can include:

- `ticker`
- `name`
- `notion_query`
- `page_id`
- `theme`

Only companies with a populated `page_id` will have Notion covers updated automatically.
