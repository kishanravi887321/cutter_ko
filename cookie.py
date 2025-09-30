# export_youtube_cookies.py
"""
Playwright script to log into Google (YouTube), wait for manual 2FA if needed,
and export cookies in Netscape cookies.txt format usable by yt-dlp.
Usage:
    python export_youtube_cookies.py your-email@example.com your-password cookies.txt headed
If you supply "headed" as the 4th arg, the browser window will be visible so you can complete 2FA.
If you prefer security, run without password and sign-in manually when the browser opens:
    python export_youtube_cookies.py --manual cookies.txt headed
"""

import sys
import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

def save_netscape_cookiefile(cookies, out_path: Path):
    lines = [
        "# Netscape HTTP Cookie File",
        "# Exported by Playwright",
        ""
    ]
    for c in cookies:
        # Convert cookie data to netscape fields
        domain = c.get("domain", "")
        # Netscape uses TRUE/FALSE for include_subdomains
        include_subdomains = "TRUE" if c.get("hostOnly") is False else "FALSE"
        path = c.get("path", "/")
        secure = "TRUE" if c.get("secure") else "FALSE"
        # expiry: if 'expires' not present or 0, set -1
        expires = str(int(c.get("expires", -1))) if c.get("expires") is not None else "-1"
        name = c.get("name", "")
        value = c.get("value", "")
        lines.append("\t".join([domain, include_subdomains, path, secure, expires, name, value]))
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[+] Saved cookies to {out_path}")

def run(email=None, password=None, out_file="cookies.txt", headed=True):
    out_path = Path(out_file).resolve()
    with sync_playwright() as p:
        # Pick chromium for best compatibility
        browser = p.chromium.launch(headless=not headed, args=["--no-sandbox"])
        context = browser.new_context()
        page = context.new_page()

        print("[*] Opening Google sign-in page for YouTube...")
        page.goto("https://accounts.google.com/signin/v2/identifier?service=youtube", timeout=60000)

        if email and password:
            # Fill email
            try:
                page.fill('input[type="email"]', email, timeout=15000)
                page.click('button:has-text("Next")')
                page.wait_for_timeout(1500)
            except Exception as e:
                print("[!] Could not auto-fill email. You may need to fill manually in the opened browser.")
            # Fill password
            try:
                page.fill('input[type="password"]', password, timeout=15000)
                page.click('button:has-text("Next")')
            except Exception as e:
                print("[!] Could not auto-fill password. You may need to fill manually in the opened browser.")
        else:
            print("[*] No credentials provided; please sign in manually in opened browser window.")

        # Wait for account UI on YouTube. This may need manual 2FA completion.
        print("[*] Waiting for YouTube page to load / for you to complete sign-in (2FA if required).")
        # We'll wait up to 2 minutes for a YouTube-specific element that shows when logged in.
        try:
            page.wait_for_selector('ytd-masthead', timeout=120000)
            print("[+] Detected YouTube masthead; login probably successful.")
        except Exception:
            print("[!] Timeout waiting for YouTube masthead. If 2FA/CAPTCHA appeared, complete it in the browser now.")
            # Give user another manual chance to sign in
            if headed:
                print("[*] You are running in headed mode. Please finish sign-in manually in the opened browser window.")
                # Wait and poll
                max_wait = 300  # seconds
                waited = 0
                while waited < max_wait:
                    try:
                        page.wait_for_selector('ytd-masthead', timeout=5000)
                        print("[+] Login detected after manual intervention.")
                        break
                    except:
                        waited += 5
                        print(f"[*] Still waiting... ({waited}/{max_wait}s)")
                else:
                    print("[!] Still not logged in after waiting. Exiting with what cookies we have.")
            else:
                print("[!] Headless and timed out — try headed mode to complete 2FA.")
        
        # Give a little time for cookies to settle
        time.sleep(1)
        cookies = context.cookies()
        browser.close()

    # Save cookies in netscape format
    save_netscape_cookiefile(cookies, out_path)
    print("[*] Done. Use the cookies.txt with yt-dlp via --cookies cookies.txt")

if __name__ == "__main__":
    # Basic CLI parsing
    if "--manual" in sys.argv:
        # manual mode: open browser and sign-in yourself
        try:
            out = sys.argv[2]
        except:
            out = "cookies.txt"
        headed_flag = True if len(sys.argv) < 4 or sys.argv[3] != "headless" else False
        run(email=None, password=None, out_file=out, headed=headed_flag)
        sys.exit(0)

    if len(sys.argv) >= 4:
        email = sys.argv[1]
        password = sys.argv[2]
        out = sys.argv[3]
        headed_flag = True if len(sys.argv) < 5 or sys.argv[4].lower() != "headless" else False
        run(email=email, password=password, out_file=out, headed=headed_flag)
    else:
        print("Usage examples:")
        print("  python export_youtube_cookies.py youremail@gmail.com yourpassword cookies.txt headed")
        print("  python export_youtube_cookies.py --manual cookies.txt headed")
