#!/usr/bin/env python3
"""
Extract clean, readable content from verified HTML files
"""

from pathlib import Path
from bs4 import BeautifulSoup
import re

def extract_clean_content():
    """Extract the actual documentation content from HTML"""

    verified_dir = Path("/Users/Mike/trading/algos/EOD/databento_docs/verified_content")
    clean_dir = Path("/Users/Mike/trading/algos/EOD/databento_docs/clean_verified_content")
    clean_dir.mkdir(exist_ok=True)

    html_files = list(verified_dir.glob("*.html"))

    if not html_files:
        print("❌ No HTML files found in verified_content")
        return

    print(f"📄 Extracting content from {len(html_files)} verified files...")

    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()

            soup = BeautifulSoup(content, 'html.parser')

            # Remove all scripts, styles, and navigation
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()

            # Extract text content
            text_content = soup.get_text()

            # Clean up the text
            lines = text_content.split('\n')
            cleaned_lines = []

            for line in lines:
                line = line.strip()
                # Skip empty lines and common navigation text
                if line and not any(skip in line.lower() for skip in [
                    'you need to enable javascript',
                    'log in',
                    'sign up',
                    'api key',
                    'support'
                ]):
                    cleaned_lines.append(line)

            # Join lines and clean up spacing
            clean_text = '\n'.join(cleaned_lines)
            clean_text = re.sub(r'\n\s*\n\s*\n', '\n\n', clean_text)  # Remove excessive newlines

            # Save clean content
            clean_filename = html_file.stem + '_clean.txt'
            clean_path = clean_dir / clean_filename

            with open(clean_path, 'w', encoding='utf-8') as f:
                f.write(f"# {html_file.stem.replace('_', ' ').title()}\n")
                f.write(f"Source: {html_file.name}\n")
                f.write("=" * 60 + "\n\n")
                f.write(clean_text[:5000])  # First 5000 chars for preview
                f.write("\n\n[Content truncated for preview - full content available in HTML file]")

            print(f"✅ Extracted: {clean_filename} ({len(clean_text)} chars)")

        except Exception as e:
            print(f"❌ Failed to extract {html_file.name}: {str(e)}")

    print(f"\n📁 Clean content saved to: {clean_dir}")

if __name__ == "__main__":
    extract_clean_content()
