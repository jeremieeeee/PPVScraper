import time
from playwright.sync_api import sync_playwright

def run():
    found_links = set()
    target_url = "https://roxiestreams.info/"

    with sync_playwright() as p:
        # Launch browser emulating standard desktop environment
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Network Interceptor to capture streaming traffic
        def intercept_response(response):
            url = response.url
            if ".m3u8" in url and url not in found_links:
                print(f"[FOUND M3U8] -> {url}")
                found_links.add(url)

        page.on("response", intercept_response)

        try:
            print(f"Navigating to homepage: {target_url}...")
            page.goto(target_url, wait_until="networkidle", timeout=60000)
            time.sleep(4)

            # --- TIER 1: COLLECT MAIN CATEGORY TABS ---
            category_links = page.locator("a").all()
            category_urls = []
            
            for link in category_links:
                href = link.get_attribute("href")
                if href and href.startswith("/") and href != "/":
                    full_url = f"{target_url.rstrip('/')}{href}"
                    # Skip external pages or profile links like guns.lol
                    if "guns.lol" not in full_url and full_url not in category_urls:
                        category_urls.append(full_url)

            print(f"Found {len(category_urls)} category tabs to scan.")

            # --- TIER 2: VISIT TABS AND SCRAPE STREAMING MATCHES ---
            match_urls = []
            for cat_url in category_urls[:10]: # Scans top 10 categories to avoid runtime limits
                print(f"Scanning category page for events: {cat_url}")
                try:
                    page.goto(cat_url, wait_until="load", timeout=30000)
                    time.sleep(3)
                    
                    # Look inside the tab page for specific stream target elements
                    sub_links = page.locator("a").all()
                    for s_link in sub_links:
                        s_href = s_link.get_attribute("href")
                        if s_href and ("-stream" in s_href or "stream-" in s_href or "streams" in s_href):
                            f_url = s_href if s_href.startswith("http") else f"{target_url.rstrip('/')}{s_href}"
                            if f_url not in match_urls:
                                match_urls.append(f_url)
                except Exception as e:
                    print(f"Failed to extract matches from {cat_url}: {e}")

            print(f"Deep crawl successfully discovered {len(match_urls)} individual match/stream windows.")

            # --- TIER 3: INSPECT FINAL STREAM PAGES ---
            for idx, stream_url in enumerate(match_urls[:25]): # Process up to 25 live events per hour
                print(f"[{idx+1}/{len(match_urls[:25])}] Triggering stream inside: {stream_url}")
                try:
                    page.goto(stream_url, wait_until="load", timeout=30000)
                    time.sleep(8) # Gives the player handshake enough time to fire off network calls
                    
                    # Interact with nested iframes if they exist to force video element activation
                    iframes = page.frames
                    for frame in iframes:
                        try:
                            play_btn = frame.locator("video, .play-btn, #player, .jwplayer").first
                            if play_btn.is_visible():
                                play_btn.click(timeout=2000)
                                time.sleep(4)
                        except Exception:
                            continue
                            
                except Exception as e:
                    print(f"Skipping match URL {stream_url} due to an error: {e}")
                    continue

        except Exception as e:
            print(f"Main execution encountered an error: {e}")
        finally:
            browser.close()

    # --- GENERATE M3U PLAYLIST ---
    if found_links:
        with open("playlist.m3u", "w") as f:
            f.write("#EXTM3U\n")
            for idx, link in enumerate(sorted(found_links), 1):
                stream_name = f"Roxie Stream {idx}"
                f.write(f'#EXTINF:-1 tvg-id="roxie_{idx}" tvg-name="{stream_name}" group-title="Live Sports",{stream_name}\n')
                f.write(f"{link}\n")
        print(f"Successfully generated playlist.m3u with {len(found_links)} channels.")
    else:
        print("No active .m3u8 streaming endpoints captured.")

if __name__ == "__main__":
    run()
