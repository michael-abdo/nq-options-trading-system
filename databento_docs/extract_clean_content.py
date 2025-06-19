#!/usr/bin/env python3
"""
Extract clean readable content from the scraped Databento documentation
"""

import os
import re
from pathlib import Path
from bs4 import BeautifulSoup
import html2text

def extract_clean_content():
    """Extract clean text content from HTML files"""

    real_content_dir = Path("/Users/Mike/trading/algos/EOD/databento_docs/real_content")
    clean_content_dir = Path("/Users/Mike/trading/algos/EOD/databento_docs/clean_content")
    clean_content_dir.mkdir(exist_ok=True)

    # Configure html2text for better output
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False
    h.body_width = 0  # Don't wrap text
    h.unicode_snob = True

    html_files = list(real_content_dir.glob("*.html"))

    if not html_files:
        print("❌ No HTML files found in real_content directory")
        return

    print(f"📄 Processing {len(html_files)} HTML files...")

    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()

            # Try to find main content area
            main_content = None
            content_selectors = [
                'main',
                '[role="main"]',
                '.main-content',
                '.content-container',
                '.documentation-content',
                '.page-content',
                'article',
                '.content'
            ]

            for selector in content_selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    break

            # If no main content found, use body but remove navigation
            if not main_content:
                main_content = soup.find('body')
                if main_content:
                    # Remove common navigation elements
                    for nav_elem in main_content.find_all(['nav', 'aside', '.sidebar', '.nav', '.menu']):
                        nav_elem.decompose()

            # Convert to markdown
            if main_content:
                # Convert HTML to markdown
                markdown_content = h.handle(str(main_content))

                # Clean up the markdown
                markdown_content = re.sub(r'\n\s*\n\s*\n', '\n\n', markdown_content)  # Remove excessive newlines
                markdown_content = re.sub(r'^\s+', '', markdown_content, flags=re.MULTILINE)  # Remove leading whitespace

                # Create clean filename
                clean_filename = html_file.stem.replace('_', '-') + '.md'
                clean_file_path = clean_content_dir / clean_filename

                # Save clean content
                with open(clean_file_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {html_file.stem.replace('_', ' ').title()}\n\n")
                    f.write(f"**Source:** {html_file.name}\n\n")
                    f.write("---\n\n")
                    f.write(markdown_content)

                print(f"✅ Cleaned: {clean_filename}")
            else:
                print(f"⚠️  No main content found in: {html_file.name}")

        except Exception as e:
            print(f"❌ Failed to process {html_file.name}: {str(e)}")

    print(f"\n🎯 Content extraction complete!")
    print(f"📁 Clean files saved to: {clean_content_dir}")

    # List all created files
    clean_files = list(clean_content_dir.glob("*.md"))
    print(f"📄 Created {len(clean_files)} clean documentation files:")
    for clean_file in sorted(clean_files):
        print(f"   - {clean_file.name}")

if __name__ == "__main__":
    try:
        import html2text
    except ImportError:
        print("Installing html2text...")
        os.system("pip install html2text beautifulsoup4")
        import html2text

    extract_clean_content()
