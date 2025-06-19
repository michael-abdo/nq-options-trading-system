#!/usr/bin/env python3
"""
Complete Verified Scraper - Download all 35+ Databento documentation pages
Senior Engineer Approach: Scale the proven solution with comprehensive validation
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from datetime import datetime
import time

class CompleteDatabenteScraper:
    def __init__(self):
        self.base_dir = Path("/Users/Mike/trading/algos/EOD/databento_docs/complete_content")
        self.base_dir.mkdir(exist_ok=True)
        self.validation_log = []
        self.failed_urls = []
        self.successful_downloads = []

        # Complete list of documentation URLs (verified from previous research)
        self.documentation_urls = [
            # Core Documentation
            "https://databento.com/docs/quickstart",
            "https://databento.com/docs/api-reference-historical",
            "https://databento.com/docs/api-reference-live",
            "https://databento.com/docs/api-reference-reference",
            "https://databento.com/docs/examples",

            # Knowledge Base
            "https://databento.com/docs/knowledge-base/new-users/market-data-schemas",
            "https://databento.com/docs/knowledge-base/new-users/fields-by-schema",
            "https://databento.com/docs/knowledge-base/new-users/fields-by-schema/trades-trades",

            # FAQs
            "https://databento.com/docs/faqs/venues-and-publishers",
            "https://databento.com/docs/faqs/streaming-vs-batch-download",

            # Standards and Conventions
            "https://databento.com/docs/standards-and-conventions/normalization",
            "https://databento.com/docs/standards-and-conventions/databento-binary-encoding",

            # Schemas and Data Formats
            "https://databento.com/docs/schemas-and-data-formats/whats-a-schema",

            # API Reference - Historical
            "https://databento.com/docs/api-reference-historical/timeseries/timeseries-get-range/parameters",
            "https://databento.com/docs/api-reference-historical/basics/symbology",
            "https://databento.com/docs/api-reference-historical/basics/datasets",
            "https://databento.com/docs/api-reference-historical/helpers/bento-replay",

            # Portal & Management
            "https://databento.com/docs/portal/api-keys",
            "https://databento.com/docs/release-notes",

            # Additional discovered URLs
            "https://databento.com/docs/api-reference-live/subscription",
            "https://databento.com/docs/api-reference-live/authentication",
            "https://databento.com/docs/schemas-and-data-formats/mbo",
            "https://databento.com/docs/schemas-and-data-formats/mbp-10",
            "https://databento.com/docs/schemas-and-data-formats/mbp-1",
            "https://databento.com/docs/schemas-and-data-formats/tbbo",
            "https://databento.com/docs/schemas-and-data-formats/bbo",
            "https://databento.com/docs/schemas-and-data-formats/trades",
            "https://databento.com/docs/schemas-and-data-formats/ohlcv",
            "https://databento.com/docs/schemas-and-data-formats/definition",
            "https://databento.com/docs/schemas-and-data-formats/imbalance",
            "https://databento.com/docs/schemas-and-data-formats/statistics",
            "https://databento.com/docs/schemas-and-data-formats/status",
            "https://databento.com/docs/standards-and-conventions/common-fields",
            "https://databento.com/docs/standards-and-conventions/enums-and-types",
            "https://databento.com/docs/api-reference-historical/basics/overview",
            "https://databento.com/docs/api-reference-historical/basics/authentication",
            "https://databento.com/docs/api-reference-historical/basics/request-response",
            "https://databento.com/docs/api-reference-historical/timeseries/get-range",
            "https://databento.com/docs/api-reference-historical/batch/submit",
            "https://databento.com/docs/api-reference-historical/batch/list",
            "https://databento.com/docs/api-reference-historical/batch/download"
        ]

    def log_validation(self, step, status, message, data=None):
        """Log each validation step with timestamp"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "status": status,
            "message": message,
            "data": data
        }
        self.validation_log.append(entry)
        status_icon = "✅" if status == "SUCCESS" else "❌" if status == "FAILED" else "🔄" if status == "INFO" else "⚠️"
        print(f"{status_icon} {step}: {message}")

    async def scrape_single_page(self, url, page_num, total_pages):
        """Scrape a single page with comprehensive validation"""

        self.log_validation("PAGE_START", "INFO", f"[{page_num}/{total_pages}] Starting: {url}")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = await context.new_page()
                page.set_default_timeout(45000)  # Longer timeout for stability

                # Navigate with retry logic
                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        response = await page.goto(url, wait_until="networkidle", timeout=30000)
                        if response and response.status < 400:
                            break
                        elif attempt == max_retries - 1:
                            self.log_validation("NAVIGATE", "FAILED", f"HTTP {response.status if response else 'No response'} after {max_retries} attempts")
                            return False
                    except Exception as e:
                        if attempt == max_retries - 1:
                            self.log_validation("NAVIGATE", "FAILED", f"Navigation failed: {str(e)}")
                            return False
                        await asyncio.sleep(2)  # Wait before retry

                # Wait for JavaScript to fully render
                await page.wait_for_timeout(4000)

                # Validate content loaded
                title = await page.title()
                if not title or "404" in title or "Error" in title:
                    self.log_validation("VALIDATE", "FAILED", f"Invalid page title: {title}")
                    return False

                body_text = await page.evaluate("document.body.innerText")
                if "You need to enable JavaScript" in body_text:
                    self.log_validation("JS_CHECK", "FAILED", "JavaScript not properly rendered")
                    return False

                # Extract content
                content = await page.content()
                content_length = len(content)

                if content_length < 3000:  # Minimum content threshold
                    self.log_validation("CONTENT_SIZE", "FAILED", f"Content too small: {content_length} chars")
                    return False

                # Generate filename
                filename = url.replace("https://databento.com/docs/", "").replace("/", "_") + ".html"
                if filename.startswith("_"):
                    filename = "index.html"

                # Save content
                output_path = self.base_dir / filename
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                # Validate saved file
                if not output_path.exists() or output_path.stat().st_size < 1000:
                    self.log_validation("SAVE", "FAILED", f"File save validation failed")
                    return False

                file_size = output_path.stat().st_size
                self.log_validation("SUCCESS", "SUCCESS", f"[{page_num}/{total_pages}] {filename} ({file_size:,} bytes)")

                self.successful_downloads.append({
                    "url": url,
                    "filename": filename,
                    "size": file_size,
                    "title": title
                })

                await browser.close()
                return True

        except Exception as e:
            self.log_validation("ERROR", "FAILED", f"[{page_num}/{total_pages}] Exception: {str(e)}")
            self.failed_urls.append({"url": url, "error": str(e)})
            return False

    async def run_complete_download(self):
        """Download all documentation pages with progress tracking"""

        print("🚀 COMPLETE DATABENTO DOCUMENTATION DOWNLOAD")
        print("=" * 60)
        print(f"📊 Total pages to download: {len(self.documentation_urls)}")
        print("🔍 Each page will be validated before saving")
        print()

        start_time = time.time()

        # Process all URLs
        for i, url in enumerate(self.documentation_urls, 1):
            print(f"\n📄 Page {i}/{len(self.documentation_urls)}: {url.split('/')[-1]}")
            print("-" * 50)

            success = await self.scrape_single_page(url, i, len(self.documentation_urls))

            if not success:
                self.failed_urls.append({"url": url, "page_number": i})

            # Progress update every 5 pages
            if i % 5 == 0:
                success_rate = len(self.successful_downloads) / i * 100
                print(f"\n📈 Progress Update: {i}/{len(self.documentation_urls)} pages processed ({success_rate:.1f}% success rate)")

            # Respectful delay between requests
            await asyncio.sleep(2)

        # Final results
        end_time = time.time()
        duration = end_time - start_time

        print(f"\n🎯 DOWNLOAD COMPLETE")
        print("=" * 60)
        print(f"✅ Successfully downloaded: {len(self.successful_downloads)}")
        print(f"❌ Failed downloads: {len(self.failed_urls)}")
        print(f"📊 Success rate: {len(self.successful_downloads)/len(self.documentation_urls)*100:.1f}%")
        print(f"⏱️  Total time: {duration/60:.1f} minutes")

        # Calculate total data downloaded
        total_size = sum(item['size'] for item in self.successful_downloads)
        print(f"💾 Total data downloaded: {total_size/1024/1024:.1f} MB")

        # Save comprehensive report
        report = {
            "download_summary": {
                "start_time": datetime.fromtimestamp(start_time).isoformat(),
                "end_time": datetime.fromtimestamp(end_time).isoformat(),
                "duration_minutes": duration / 60,
                "total_pages_attempted": len(self.documentation_urls),
                "successful_downloads": len(self.successful_downloads),
                "failed_downloads": len(self.failed_urls),
                "success_rate_percent": len(self.successful_downloads)/len(self.documentation_urls)*100,
                "total_data_mb": total_size/1024/1024
            },
            "successful_downloads": self.successful_downloads,
            "failed_urls": self.failed_urls,
            "validation_log": self.validation_log[-50:]  # Last 50 entries
        }

        report_path = self.base_dir / "download_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"📋 Detailed report saved: {report_path}")

        # List downloaded files
        if self.successful_downloads:
            print(f"\n📁 Downloaded files:")
            for item in self.successful_downloads[:10]:  # Show first 10
                print(f"   - {item['filename']} ({item['size']:,} bytes)")
            if len(self.successful_downloads) > 10:
                print(f"   ... and {len(self.successful_downloads) - 10} more files")

        # Show failed URLs if any
        if self.failed_urls:
            print(f"\n⚠️  Failed URLs:")
            for item in self.failed_urls[:5]:  # Show first 5 failures
                print(f"   - {item['url']}")
            if len(self.failed_urls) > 5:
                print(f"   ... and {len(self.failed_urls) - 5} more failures")

        return len(self.successful_downloads), len(self.failed_urls)

if __name__ == "__main__":
    scraper = CompleteDatabenteScraper()

    print("🎯 Starting complete Databento documentation download...")
    print("   This will download all known documentation pages with validation")
    print("   Estimated time: 5-10 minutes")
    print()

    success_count, failure_count = asyncio.run(scraper.run_complete_download())

    if success_count > 30:
        print(f"\n🎉 EXCELLENT RESULTS! Downloaded {success_count} pages successfully")
        print("   Ready for content extraction and analysis")
    elif success_count > 20:
        print(f"\n✅ GOOD RESULTS! Downloaded {success_count} pages with {failure_count} failures")
        print("   Most content successfully captured")
    elif success_count > 10:
        print(f"\n⚠️  MIXED RESULTS! Downloaded {success_count} pages with {failure_count} failures")
        print("   Significant content captured but investigate failures")
    else:
        print(f"\n❌ ISSUES DETECTED! Only {success_count} pages downloaded")
        print("   Check download_report.json for failure analysis")
