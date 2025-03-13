# main.py
from datetime import datetime, timedelta, timezone
from truthbrush.api import Api
import json
import os
from dotenv import load_dotenv
from openai import OpenAI
import requests
import base64
import csv
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import math
import time

# Load environment variables (including OPENAI_API_KEY)
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
api = Api()

def classify_post(post):
    """
    For a given post, determine if it is tariffs related and extract:
      - tariffs_related: whether the post discusses tariffs/trade issues (true/false)
      - affected_country: which country is mentioned (if any)
      - affected_region: which region is mentioned (if any)
      - products: list of products mentioned (e.g., Champagne, wine, etc.)
      - published_time: the post's creation time (should match the provided created_at)
      - tariff_rate: any percentage or rate mentioned (if any)
      - classification: "threat" vs "official" (or "unknown")
      - media_analysis: a brief analysis of any media (or null if none)
      
    Returns the analysis as a JSON-parsed dictionary.
    """
    # Process media: for images, download and encode them as base64 data URLs.
    media_list = post.get("media", [])
    enhanced_media_text = ""
    for m in media_list:
        if m.get("type") == "image":
            try:
                resp = requests.get(m["url"])
                if resp.status_code == 200:
                    b64data = base64.b64encode(resp.content).decode("utf-8")
                    # Assume JPEG MIME type; adjust if needed.
                    mime = "image/jpeg"
                    data_url = f"data:{mime};base64,{b64data}"
                    enhanced_media_text += f"\nImage ({m.get('detail', 'low')}): {data_url}"
                else:
                    enhanced_media_text += f"\nImage URL: {m.get('url')}"
            except Exception:
                enhanced_media_text += f"\nImage URL: {m.get('url')} (failed to fetch image)"
        else:
            enhanced_media_text += f"\nNon-image media: {json.dumps(m)}"

    # Build a prompt text with post details.
    prompt_text = f"""
Analyze the following post and provide a JSON object with the following keys:
- "tariffs_related": true or false
- "affected_country": string or null
- "affected_region": string or null
- "products": a list of strings (empty list if none)
- "published_time": string (should match the post's created_at)
- "tariff_rate": string (e.g. "50%", or null if not mentioned)
- "classification": string ("threat" or "official" or "unknown")
- "media_analysis": string (a brief analysis of the media if present, or null)

Post details:
Published time: {post.get("created_at")}
Content: {post.get("content")}
Media URLs: {json.dumps(post.get("media"))}
{enhanced_media_text}
"""
    def do_request(text):
        return client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": (
                    "You are a tariff analysis assistant tasked with reviewing Donald Trump's posts on TruthSocial. "
                    "Your objective is to identify and analyze Trump's positions, announcements, or intended actions regarding tariffs. "
                    "Analyze both textual statements and visual content included in his posts. If Trump references news articles, "
                    "only consider them if he explicitly supports or announces something based on the article's content. "
                    "Ignore announcements or claims made solely by other individuals unless officially endorsed or mentioned explicitly by Trump himself."
                    "\n\nRespond strictly with JSON matching the provided schema."
                )},
                {"role": "user", "content": text}
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "tariff_analysis",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "tariffs_related": {"type": "boolean"},
                            "affected_country": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                            "affected_region": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                            "products": {"type": "array", "items": {"type": "string"}},
                            "published_time": {"type": "string"},
                            "tariff_rate": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                            "classification": {"type": "string"},
                            "media_analysis": {"anyOf": [{"type": "string"}, {"type": "null"}]}
                        },
                        "required": [
                            "tariffs_related",
                            "affected_country",
                            "affected_region",
                            "products",
                            "published_time",
                            "tariff_rate",
                            "classification",
                            "media_analysis"
                        ],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        )
    try:
        response = do_request(prompt_text)
        classification = json.loads(response.output_text)
    except Exception as e:
        # If error due to length, shorten the prompt and retry.
        if "too long" in str(e).lower():
            shortened = prompt_text[:int(len(prompt_text) * 0.9)]
            try:
                response = do_request(shortened)
                classification = json.loads(response.output_text)
            except Exception as e2:
                classification = {"error": str(e2)}
        else:
            classification = {"error": str(e)}
    return classification

def write_csv(filename, posts):
    fieldnames = [
        "created_at", "content", "media",
        "tariffs_related", "affected_country", "affected_region",
        "products", "published_time", "tariff_rate", "classification", "media_analysis"
    ]
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for post in posts:
            cls = post.get("classification", {})
            writer.writerow({
                "created_at": post.get("created_at", ""),
                "content": post.get("content", ""),
                "media": json.dumps(post.get("media", [])),
                "tariffs_related": cls.get("tariffs_related", ""),
                "affected_country": cls.get("affected_country", ""),
                "affected_region": cls.get("affected_region", ""),
                "products": ", ".join(cls.get("products", [])) if cls.get("products") else "",
                "published_time": cls.get("published_time", ""),
                "tariff_rate": cls.get("tariff_rate", ""),
                "classification": cls.get("classification", ""),
                "media_analysis": cls.get("media_analysis", "")
            })

def main():
    # Calculate the datetime for 90 days ago (UTC)
    created_after = datetime.now(timezone.utc) - timedelta(days=90)
    # Pull statuses for "realDonaldTrump" posted after the calculated time.
    posts = list(api.pull_statuses("realDonaldTrump", created_after=created_after))

    # Process posts concurrently with a maximum of 10 workers.
    def process_post(post):
        structured = {
            "created_at": post.get("created_at"),
            "content": post.get("content"),
            "media": [{"type": m.get("type"), "url": m.get("url")} for m in post.get("media_attachments", [])]
        }
        structured["classification"] = classify_post(structured)
        time.sleep(1)
        return structured

    with ThreadPoolExecutor(max_workers=10) as executor:
        structured_posts = list(tqdm(executor.map(process_post, posts), total=len(posts), desc="Processing posts"))

    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.getcwd(), "outputs")
    os.makedirs(output_dir, exist_ok=True)

    # Save all posts (Level 1)
    with open(os.path.join(output_dir, 'posts.json'), 'w') as file:
        json.dump(structured_posts, file, indent=2)
    write_csv(os.path.join(output_dir, 'posts.csv'), structured_posts)

    # Level 2: Tariff-related posts.
    tariff_posts = [post for post in structured_posts if post.get("classification", {}).get("tariffs_related") is True]
    with open(os.path.join(output_dir, 'tariff_posts.json'), 'w') as file:
        json.dump(tariff_posts, file, indent=2)
    write_csv(os.path.join(output_dir, 'tariff_posts.csv'), tariff_posts)

    # Level 3: Posts where an explicit tariff rate is specified (non-null and non-empty).
    official_tariff_posts = [post for post in structured_posts if post.get("classification", {}).get("tariff_rate") not in [None, ""]]
    with open(os.path.join(output_dir, 'official_tariff_posts.json'), 'w') as file:
        json.dump(official_tariff_posts, file, indent=2)
    write_csv(os.path.join(output_dir, 'official_tariff_posts.csv'), official_tariff_posts)

    # Also print the outputs
    print("All posts:")
    print(json.dumps(structured_posts, indent=2))
    print("Tariff-related posts:")
    print(json.dumps(tariff_posts, indent=2))
    print("Official tariff rate posts:")
    print(json.dumps(official_tariff_posts, indent=2))

if __name__ == "__main__":
    main()
