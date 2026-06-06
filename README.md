# Notion Company Cover Pipeline

Pipeline para gerar capas premium de empresas, publicar as imagens no GitHub e atualizar automaticamente as capas das paginas correspondentes no Notion.

## Repositorio alvo

- Repo: `lucasebert2004-1981/notion-company-covers`
- Caminho das capas: `covers/TICKER.png`
- URL publica final: `https://raw.githubusercontent.com/lucasebert2004-1981/notion-company-covers/main/covers/TICKER.png`

## Arquivos principais

- `companies.json`
- `generate_covers.py`
- `requirements.txt`
- `.github/workflows/generate-covers.yml`
- `README.md`

## companies.json

Formato esperado:

```json
[
  {
    "ticker": "FROG",
    "name": "JFrog",
    "page_id": "372ab10f-bd8b-81f4-a2cf-e44a1c3910a0",
    "theme": "enterprise DevOps, software supply chain, artifact management, cloud-native delivery, green brand palette"
  }
]
```

Se `page_id` estiver em branco, a empresa continua elegivel para geracao da imagem, mas a atualizacao da cover no Notion e pulada.

## Segredos necessarios no GitHub

Configure estes secrets no repositorio:

- `OPENAI_API_KEY`
- `NOTION_TOKEN`

A integracao do Notion precisa ter permissao para editar as paginas alvo.

## Como rodar pelo GitHub Actions

1. Abra a aba **Actions**.
2. Escolha **Generate Notion Covers**.
3. Clique em **Run workflow**.
4. Use `only_tickers` para filtrar tickers, por exemplo `FROG` ou `FROG,SNOW,PANW`.

O workflow roda na ordem segura:

1. gera a imagem em `covers/TICKER.png`
2. faz commit e push da imagem no GitHub
3. verifica se a URL raw publica esta acessivel
4. atualiza a cover da pagina no Notion somente depois da publicacao

## Execucao local

Instale dependencias:

```bash
pip install -r requirements.txt
```

Gerar imagens:

```bash
RUN_STAGE=generate ONLY_TICKERS=FROG python generate_covers.py
```

Atualizar Notion depois que as imagens ja estiverem publicadas:

```bash
RUN_STAGE=notion ONLY_TICKERS=FROG python generate_covers.py
```

## Variaveis suportadas

- `OPENAI_API_KEY`
- `NOTION_TOKEN`
- `ONLY_TICKERS` - exemplo: `FROG,SNOW,PANW`
- `RUN_STAGE` - `generate`, `notion` ou `full`
- `OPENAI_IMAGE_MODEL` - padrao: `gpt-image-1`
- `OPENAI_IMAGE_SIZE` - padrao: `1536x864`

## Prompt-base

```text
Create a premium horizontal Notion cover image for {name} ({ticker}). Use a clean, polished, cinematic corporate-tech style, widescreen 16:9 composition, strong company branding, realistic or semi-realistic environment, subtle lighting, premium materials, and a sector-relevant scene. The {name} logo or clearly legible company name must be the hero element. Make the identity unmistakable but tasteful. Theme/context: {theme}. No extra captions, no watermarks, no busy infographic layout.
```

## Observacoes

- O script falha com erro claro se faltar um segredo necessario para o estagio em execucao.
- A atualizacao do Notion acontece apenas quando `page_id` estiver preenchido.
- Se a URL raw ainda nao estiver publica, a atualizacao do Notion e pulada naquele momento.
