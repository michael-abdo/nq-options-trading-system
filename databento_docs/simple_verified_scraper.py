#!/usr/bin/env python3
"""
Simple Verified Scraper - Prove it works on 1-2 pages
Senior Engineer Approach: Validate EVERYTHING at each step
"""

import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright
from datetime import datetime
import json

class VerifiedScraper:
    def __init__(self):
        self.base_dir = Path("/Users/Mike/trading/algos/EOD/databento_docs/verified_content")
        self.base_dir.mkdir(exist_ok=True)
        self.validation_log = []

    def log_validation(self, step, status, message, data=None):
        """Log each validation step"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "status": status,
            "message": message,
            "data": data
        }
        self.validation_log.append(entry)
        status_icon = "✅" if status == "SUCCESS" else "❌" if status == "FAILED" else "🔄"
        print(f"{status_icon} {step}: {message}")

    async def verify_single_page(self, url, expected_title_contains=None):
        """Scrape and verify a single page with full validation"""

        self.log_validation("INIT", "INFO", f"Starting scrape of: {url}")

        try:
            # Step 1: Launch browser
            async with async_playwright() as p:
                self.log_validation("BROWSER", "INFO", "Launching browser...")
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080}
                )
                page = await context.new_page()

                # Step 2: Navigate to page
                self.log_validation("NAVIGATE", "INFO", f"Navigating to {url}")
                response = await page.goto(url, wait_until="networkidle", timeout=30000)

                if not response or response.status >= 400:
                    self.log_validation("NAVIGATE", "FAILED", f"HTTP {response.status if response else 'No response'}")
                    return False

                # Step 3: Wait for content to load
                self.log_validation("LOAD", "INFO", "Waiting for content to load...")
                await page.wait_for_timeout(3000)  # Give JS time to render

                # Step 4: Validate page title
                title = await page.title()
                self.log_validation("TITLE", "INFO", f"Page title: {title}")

                if expected_title_contains and expected_title_contains.lower() not in title.lower():
                    self.log_validation("TITLE", "FAILED", f"Title doesn't contain '{expected_title_contains}'")
                    return False

                # Step 5: Check for JavaScript rendering
                body_text = await page.evaluate("document.body.innerText")
                if "You need to enable JavaScript" in body_text:
                    self.log_validation("JS_CHECK", "FAILED", "Page still showing JS warning")
                    return False

                self.log_validation("JS_CHECK", "SUCCESS", "JavaScript content loaded successfully")

                # Step 6: Extract content
                content = await page.content()
                content_length = len(content)
                self.log_validation("EXTRACT", "INFO", f"Extracted {content_length} characters")

                if content_length < 5000:  # Reasonable minimum for a doc page
                    self.log_validation("EXTRACT", "FAILED", f"Content too short: {content_length} chars")
                    return False

                # Step 7: Save content
                filename = url.replace("https://databento.com/docs/", "").replace("/", "_") + ".html"
                if filename.startswith("_"):
                    filename = "index.html"

                output_path = self.base_dir / filename
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                file_size = output_path.stat().st_size
                self.log_validation("SAVE", "SUCCESS", f"Saved to {filename} ({file_size} bytes)")

                # Step 8: Validate saved file
                if not output_path.exists():
                    self.log_validation("VALIDATE", "FAILED", "File not found after save")
                    return False

                if file_size < 1000:
                    self.log_validation("VALIDATE", "FAILED", f"Saved file too small: {file_size} bytes")
                    return False

                self.log_validation("VALIDATE", "SUCCESS", f"File validation passed")

                await browser.close()
                return True

        except Exception as e:
            self.log_validation("ERROR", "FAILED", f"Exception: {str(e)}")
            return False

    async def run_verification_test(self):
        """Run the verification test on 2 key pages"""

        print("🚀 SIMPLIFIED VERIFIED SCRAPER - PROVING IT WORKS")
        print("=" * 60)

        # Test pages - start with these 2 to prove concept
        test_pages = [
            {
                "url": "https://databento.com/docs/quickstart",
                "title_contains": "Getting started"
            },
            {
                "url": "https://databento.com/docs/api-reference-historical",
                "title_contains": "API"
            }
        ]

        results = []
        for i, page_config in enumerate(test_pages, 1):
            print(f"\n📄 TEST {i}/2: {page_config['url']}")
            print("-" * 40)

            success = await self.verify_single_page(
                page_config["url"],
                page_config["title_contains"]
            )

            results.append({
                "url": page_config["url"],
                "success": success
            })

            if success:
                self.log_validation("PAGE_RESULT", "SUCCESS", f"Page {i} successfully scraped and validated")
            else:
                self.log_validation("PAGE_RESULT", "FAILED", f"Page {i} failed validation")

        # Final validation report
        successful_pages = sum(1 for r in results if r["success"])
        total_pages = len(results)

        print(f"\n🎯 FINAL VALIDATION RESULTS:")
        print(f"   Successfully scraped: {successful_pages}/{total_pages} pages")

        if successful_pages == total_pages:
            self.log_validation("FINAL", "SUCCESS", "All pages successfully scraped - SCRAPER WORKS!")
            print("   ✅ SCRAPER VERIFIED - Ready for full download")
        elif successful_pages > 0:
            self.log_validation("FINAL", "PARTIAL", f"Partial success - {successful_pages} pages work")
            print("   ⚠️  PARTIAL SUCCESS - Some pages work, investigate failures")
        else:
            self.log_validation("FINAL", "FAILED", "No pages successfully scraped")
            print("   ❌ SCRAPER FAILED - Need to debug")

        # Save validation log
        log_path = self.base_dir / "validation_log.json"
        with open(log_path, 'w') as f:
            json.dump(self.validation_log, f, indent=2)

        print(f"\n📋 Validation log saved: {log_path}")

        # Show what files we have
        files = list(self.base_dir.glob("*.html"))
        if files:
            print(f"\n📁 Downloaded files:")
            for file in files:
                size = file.stat().st_size
                print(f"   - {file.name} ({size:,} bytes)")

        return successful_pages == total_pages

if __name__ == "__main__":
    scraper = VerifiedScraper()
    success = asyncio.run(scraper.run_verification_test())

    if success:
        print("\n🎉 VERIFICATION COMPLETE - Scraper is working!")
        print("    Ready to proceed with full documentation download.")
    else:
        print("\n⚠️  VERIFICATION ISSUES - Need to investigate failures.")
        print("    Check validation log for specific problems.")
