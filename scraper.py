import time
import re
from playwright.sync_api import sync_playwright

def run():
    found_links = set()
    target_url = "https://roxiestreams.info/"
    target_keywords = ["soccer", "mlb", "nba", "nfl", "nhl", "fighting", "motorsports", "wwe", "streams", "multiview"]

    # Regular expression to extract any URLs ending in .m3u8 from raw text/html
    m3u8_regex = re.compile(r'(https?://[^\s"\',\?<>#]+\.m3u8[^\s"\',<>]*)', re.IGNORECASE)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()

        # Strategy 1: Catch .m3u8 links passing through network requests or responses
        def check_url(url):
            if ".m3u8" in url and url not in found_links:
                print(f"[FOUND VIA NETWORK] -> {url}")
                found_links.add(url)

        page.on("request", lambda request: check_url(request.url))
        page.on("response", lambda response: check_url(response.url))

        try:
            print(f"Navigating to homepage: {target_url}...")
            page.goto(target_url, wait_until="networkidle", timeout=60000)
            time.sleep(5)

            # --- TIER 1: FIND CATEGORY TABS ---
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
            print(f"Found {len(sorted_categories)} category tabs to scan.")

            # --- TIER 2: VISIT TABS TO HARVEST MATCH LINKS ---
            match_urls = set()
            for cat_path in sorted_categories:
                try:
                    page.goto(cat_path, wait_until="load", timeout=30000)
                    time.sleep(3)
                    sub_anchors = page.locator("a").all()
                    for sub_a in sub_anchors:
                        s_href = sub_a.get_attribute("href")
                        if s_href and not any(b in s_href for b in [".cc", "guns.lol"]):
                            if "stream" in s_href.lower() or "-" in s_href:
                                match_url = f"{target_url.rstrip('/')}{s_href}" if s_href.startswith("/") else s_href
                                if "roxiestreams.info" in match_url:
                                    match_urls.add(match_url)
                except Exception:
                    continue

            final_stream_targets = sorted(list(match_urls))
            print(f"Deep crawl extracted {len(final_stream_targets)} individual stream paths.")

            # --- TIER 3: LOAD FINAL STREAM PAGES & SCRAPE SOURCE CODE ---
            for idx, stream_target in enumerate(final_stream_targets[:25]):
                print(f"[{idx+1}/{len(final_stream_targets[:25])}] Scanning player source code at: {stream_target}")
                try:
                    page.goto(stream_target, wait_until="load", timeout=30000)
                    time.sleep(6) # Wait for page elements/scripts to populate completely

                    # Strategy 2: Extract hardcoded .m3u8 links directly from the main page frame HTML
                    main_html = page.content()
                    for match in m3u8_regex.findall(main_html):
                        clean_url = match.replace('\\', '') # Clean any escaped JS slashes
                        if clean_url not in found_links:
                            print(f"[FOUND IN MAIN HTML SOURCE] -> {clean_url}")
                            found_links.add(clean_url)

                    # Strategy 3: Scan inside every embedded iframe source code text
                    for frame in page.frames:
                        try:
                            frame_html = frame.content()
                            for match in m3u8_regex.findall(frame_html):
                                clean_url = match.replace('\\', '')
                                if clean_url not in found_links:
                                    print(f"[FOUND IN IFRAME HTML SOURCE] -> {clean_url}")
                                    found_links.add(clean_url)
                            
                            # Backup click event to try and force dynamic initialization
                            play_button = frame.locator("video, .play-btn, #player, .jwplayer").first
                            if play_button and play_button.is_visible():
                                play_button.click(timeout=1000)
                        except Exception:
                            continue

                    time.sleep(2) # Brief pause for any network calls forced by backup clicks
                except Exception as e:
                    print(f"Skipping stream target {stream_target}: {e}")

        except Exception as e:
            print(f"Scraper runtime failure: {e}")
        finally:
            browser.close()

    # --- GENERATE OUTPUT PLAYLIST ---
    if found_links:
        with open("playlist.m3u", "w") as f:
            f.write("#EXTM3U\n")
            for idx, link in enumerate(sorted(found_links), 1):
                stream_name = f"Roxie Stream {idx}"
                f.write(f'#EXTINF:-1 tvg-id="roxie_{idx}" tvg-name="{stream_name}" group-title="Live Sports",{stream_name}\n')
                f.write(f"{link}\n")
        print(f"Successfully generated playlist.m3u with {len(found_links)} stream configurations.")
    else:
        print("Run finished. 0 streaming playlist links captured.")

if __name__ == "__main__":
    run()
