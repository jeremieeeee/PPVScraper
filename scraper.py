import time
from playwright.sync_api import sync_playwright

def run():
    found_links = set()
    target_url = "https://roxiestreams.info/"
    
    # Target path keywords to identify actual sports stream categories
    target_keywords = ["soccer", "mlb", "nba", "nfl", "nhl", "fighting", "motorsports", "wwe", "streams", "multiview"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()

        # Intercept hidden stream requests
        def intercept_response(response):
            url = response.url
            if ".m3u8" in url and url not in found_links:
                print(f"[FOUND M3U8] -> {url}")
                found_links.add(url)

        page.on("response", intercept_response)

        try:
            print(f"Navigating to homepage: {target_url}...")
            page.goto(target_url, wait_until="networkidle", timeout=60000)
            time.sleep(5)

            # --- TIER 1: FIND CATEGORY TABS ENTIRELY INSIDE ROXIESTREAMS.INFO ---
            all_anchors = page.locator("a").all()
            category_urls = set()

            for anchor in all_anchors:
                try:
                    href = anchor.get_attribute("href")
                    text = (anchor.text_content() or "").lower()
                    
                    if href:
                        # Ignore status/profile domains (.cc, guns.lol, etc.)
                        if any(bad_domain in href for bad_domain in [".cc", "guns.lol", "discord"]):
                            continue
                            
                        href_lower = href.lower()
                        # Verify it's a category matching our sports keywords
                        if any(k in href_lower or k in text for k in target_keywords):
                            if href.startswith("/"):
                                full_url = f"{target_url.rstrip('/')}{href}"
                            elif "roxiestreams.info" in href:
                                full_url = href
                            else:
                                continue # Skip unexpected external strings
                                
                            category_urls.add(full_url)
                except Exception:
                    continue

            sorted_categories = sorted(list(category_urls))
            print(f"Filtered status domains. Found {len(sorted_categories)} valid .info category tabs to inspect.")

            # --- TIER 2: VISIT EACH CATEGORY TAB TO HARVEST INTERNAL MATCH LINKS ---
            match_urls = set()
            for cat_path in sorted_categories:
                print(f"Opening category tab: {cat_path}")
                try:
                    page.goto(cat_path, wait_until="load", timeout=30000)
                    time.sleep(4)
                    
                    # Inside the category page, scan for specific stream container links (e.g., /mlb-streams-1)
                    sub_anchors = page.locator("a").all()
                    for sub_a in sub_anchors:
                        s_href = sub_a.get_attribute("href")
                        if s_href and not any(b in s_href for b in [".cc", "guns.lol"]):
                            # Look for links that point deeper into specific streams
                            if "stream" in s_href.lower() or "-" in s_href:
                                if s_href.startswith("/"):
                                    match_url = f"{target_url.rstrip('/')}{s_href}"
                                else:
                                    match_url = s_href
                                    
                                if "roxiestreams.info" in match_url:
                                    match_urls.add(match_url)
                except Exception as e:
                    print(f"Could not load sub-elements for {cat_path}: {e}")

            final_stream_targets = sorted(list(match_urls))
            print(f"Deep crawl extracted {len(final_stream_targets)} individual live stream links from tabs.")

            # --- TIER 3: LOAD FINAL STREAM PAGES TO TRIGGER VIDEO NETWORKING ---
            for idx, stream_target in enumerate(final_stream_targets[:25]):
                print(f"[{idx+1}/{len(final_stream_targets[:25])}] Triggering video player at: {stream_target}")
                try:
                    page.goto(stream_target, wait_until="load", timeout=30000)
                    time.sleep(8) # Wait for player handshake initialization
                    
                    # Click inside nested iframes/video targets to wake up streaming files
                    for frame in page.frames:
                        try:
                            play_button = frame.locator("video, .play-btn, #player, .jwplayer").first
                            if play_button and play_button.is_visible():
                                play_button.click(timeout=1500)
                                time.sleep(3)
                        except Exception:
                            continue
                except Exception as e:
                    print(f"Skipping stream page {stream_target}: {e}")

        except Exception as e:
            print(f"Scraper loop broken: {e}")
        finally:
            browser.close()

    # --- GENERATE OUTPUT ---
    if found_links:
        with open("playlist.m3u", "w") as f:
            f.write("#EXTM3U\n")
            for idx, link in enumerate(sorted(found_links), 1):
                stream_name = f"Roxie Stream {idx}"
                f.write(f'#EXTINF:-1 tvg-id="roxie_{idx}" tvg-name="{stream_name}" group-title="Live Sports",{stream_name}\n')
                f.write(f"{link}\n")
        print(f"Successfully generated playlist.m3u with {len(found_links)} source links.")
    else:
        print("Run complete. No active .m3u8 streaming links found.")

if __name__ == "__main__":
    run()
