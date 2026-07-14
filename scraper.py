import time
from playwright.sync_api import sync_playwright

def run():
    playlist_entries = []
    target_url = "https://roxiestreams.info/"
    target_keywords = ["soccer", "mlb", "nba", "nfl", "nhl", "fighting", "motorsports", "wwe", "streams", "multiview", "aew"]

    # Your explicit mapping dictionary matching page paths directly to the underlying CDN channels
    stream_map = {
        "mlb-streams-1": [
            "https://tedesco.uniteesports.com/mlb.m3u8",
            "https://tedesco.formaturamaxi.com.br/mlb.m3u8"
        ],
        "nba-streams-1": [
            "https://tedesco.uniteesports.com/nba.m3u8"
        ],
        "nba-streams-2": [
            "https://tedesco.formaturamaxi.com.br/nba2.m3u8"
        ],
        "wwe-streams": [
            "https://admin2.formaturamaxi.com.br/wwe.m3u8"
        ],
        "aew": [
            "https://tedesco.formaturamaxi.com.br/aew.m3u8"
        ],
        # Predictive patterns for remaining categories based on your template configurations
        "soccer-streams-1": ["https://tedesco.uniteesports.com/soccer.m3u8"],
        "soccer-streams-2": ["https://tedesco.formaturamaxi.com.br/soccer2.m3u8"],
        "nfl-streams-1": ["https://tedesco.uniteesports.com/nfl.m3u8"],
        "nhl-streams-1": ["https://tedesco.uniteesports.com/nhl.m3u8"],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            print(f"Navigating to homepage index: {target_url}...")
            page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)

            # Gather category navigation links present on the root domain
            all_anchors = page.locator("a").all()
            category_urls = set()

            for anchor in all_anchors:
                try:
                    href = anchor.get_attribute("href")
                    text = (anchor.text_content() or "").lower()
                    if href:
                        if any(bad in href for bad in [".cc", "guns.lol", "discord"]):
                            continue
                        if any(k in href.lower() or k in text for k in target_keywords):
                            full_url = f"{target_url.rstrip('/')}{href}" if href.startswith("/") else href
                            if "roxiestreams.info" in full_url:
                                category_urls.add(full_url)
                except Exception:
                    continue

            sorted_categories = sorted(list(category_urls))
            print(f"Discovered {len(sorted_categories)} valid tabs to search.")

            # Scan tabs for active references
            active_paths = set()
            for cat_path in sorted_categories:
                try:
                    print(f"Inspecting active items on tab: {cat_path}")
                    page.goto(cat_path, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(2)
                    
                    sub_anchors = page.locator("a").all()
                    for sub_a in sub_anchors:
                        s_href = sub_a.get_attribute("href")
                        if s_href and not any(b in s_href for b in [".cc", "guns.lol"]):
                            if any(k in s_href.lower() for k in target_keywords) or s_href.startswith("/"):
                                # Strip leading slashes and domain roots clean to get exact string tokens
                                path_only = s_href.split("roxiestreams.info/")[-1].strip("/")
                                if path_only and len(path_only) > 1:
                                    active_paths.add(path_only)
                except Exception:
                    continue

            print(f"Verified active paths running on site layout right now: {list(active_paths)}")

            # Match discovered paths with your hardcoded CDN endpoints
            stream_count = 1
            for current_path in sorted(list(active_paths)):
                # Exact key lookup (e.g., mlb-streams-1)
                if current_path in stream_map:
                    for m3u8_endpoint in stream_map[current_path]:
                        display_name = current_path.replace("-", " ").title()
                        playlist_entries.append({
                            "name": f"{display_name} Link {stream_count}",
                            "url": m3u8_endpoint,
                            "id": f"roxie_{stream_count}"
                        })
                        stream_count += 1
                else:
                    # Fuzzy match fallback logic to catch variations
                    for static_key, endpoints in stream_map.items():
                        if static_key in current_path:
                            for m3u8_endpoint in endpoints:
                                display_name = current_path.replace("-", " ").title()
                                playlist_entries.append({
                                    "name": f"{display_name}",
                                    "url": m3u8_endpoint,
                                    "id": f"roxie_{stream_count}"
                                })
                                stream_count += 1
                            break

        except Exception as e:
            print(f"Execution handling error: {e}")
        finally:
            browser.close()

    # Generate the M3U output
    if playlist_entries:
        with open("playlist.m3u", "w") as f:
            f.write("#EXTM3U\n")
            for entry in playlist_entries:
                f.write(f'#EXTINF:-1 tvg-id="{entry["id"]}" tvg-name="{entry["name"]}" group-title="Live Sports",{entry["name"]}\n')
                f.write(f"{entry['url']}\n")
        print(f"Successfully compiled playlist.m3u with {len(playlist_entries)} mapped items.")
    else:
        print("No matches detected on the site layout corresponding to your streaming list configurations.")

if __name__ == "__main__":
    run()
