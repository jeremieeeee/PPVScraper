import time
from playwright.sync_api import sync_playwright

def run():
    found_links = set()
    target_url = "https://roxiestreams.info/"

    with sync_playwright() as p:
        # Launch browser with options to bypass basic bot blockers
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Network Interceptor: Every time the browser makes a request, look for .m3u8
        def intercept_response(response):
            url = response.url
            if ".m3u8" in url and url not in found_links:
                print(f"[FOUND M3U8] -> {url}")
                found_links.add(url)

        page.on("response", intercept_response)

        try:
            print(f"Navigating to {target_url}...")
            page.goto(target_url, wait_until="networkidle", timeout=60000)
            time.sleep(5)  # Let any immediate streams load

            # --- ADVANCED TAB/WINDOW CRAWLER ---
            # 1. Gather all main stream links/tabs present on the homepage
            # Adjust the selector below (e.g., 'a', '.btn', '.tab') based on the site's layout
            links = page.locator("a").all()
            hrefs = []
            
            for link in links:
                href = link.get_attribute("href")
                # Filter out external links or irrelevant links if necessary
                if href and ("stream" in href or href.startswith("/")) and href != "/":
                    # Form absolute URLs if they are relative paths
                    full_url = href if href.startswith("http") else f"{target_url.rstrip('/')}{href}"
                    if full_url not in hrefs:
                        hrefs.append(full_url)

            print(f"Discovered {len(hrefs)} prospective stream paths/tabs to check.")

            # 2. Cycle through each tab/window systematically
            for idx, stream_url in enumerate(hrefs[:20]): # Limited to top 20 to prevent runner timeouts
                print(f"[{idx+1}/{len(hrefs)}] Inspecting: {stream_url}")
                try:
                    # Navigate directly or click elements that open frames
                    page.goto(stream_url, wait_until="load", timeout=30000)
                    time.sleep(8) # Gives players time to perform handshakes and load playlists
                    
                    # If streams sit inside an iframe, let's trigger them
                    iframes = page.frames
                    for frame in iframes:
                        # Sometimes clicking the play button inside the frame triggers the .m3u8 load
                        try:
                            play_btn = frame.locator("video, .play-btn, #player").first
                            if play_btn.is_visible():
                                play_btn.click(timeout=2000)
                                time.sleep(3)
                        except Exception:
                            continue
                            
                except Exception as e:
                    print(f"Skipping {stream_url} due to error: {e}")
                    continue

        except Exception as e:
            print(f"Main execution encountered an error: {e}")
        finally:
            browser.close()

    # Save results to file
    if found_links:
        with open("live_streams.txt", "w") as f:
            for link in sorted(found_links):
                f.write(f"{link}\n")
        print(f"Successfully saved {len(found_links)} links.")
    else:
        print("No .m3u8 links intercepted during this run.")

if __name__ == "__main__":
    run()
