#!/usr/bin/env python3
"""
Extract clean, organized content from all downloaded documentation
"""

from pathlib import Path
from bs4 import BeautifulSoup
import json
import re

def extract_all_content():
    """Extract clean content from all downloaded HTML files"""

    complete_dir = Path("/Users/Mike/trading/algos/EOD/databento_docs/complete_content")
    clean_dir = Path("/Users/Mike/trading/algos/EOD/databento_docs/clean_complete_content")
    clean_dir.mkdir(exist_ok=True)

    # Organize by categories
    categories = {
        "api_reference": [],
        "schemas": [],
        "standards": [],
        "knowledge_base": [],
        "faqs": [],
        "examples": [],
        "portal": [],
        "misc": []
    }

    html_files = list(complete_dir.glob("*.html"))

    if not html_files:
        print("❌ No HTML files found")
        return

    print(f"📄 Extracting content from {len(html_files)} files...")

    extraction_summary = []

    for html_file in html_files:
        try:
            # Categorize file
            filename = html_file.stem
            if "api-reference" in filename:
                category = "api_reference"
            elif "schemas-and-data-formats" in filename:
                category = "schemas"
            elif "standards-and-conventions" in filename:
                category = "standards"
            elif "knowledge-base" in filename:
                category = "knowledge_base"
            elif "faqs" in filename:
                category = "faqs"
            elif "examples" in filename:
                category = "examples"
            elif "portal" in filename:
                category = "portal"
            else:
                category = "misc"

            categories[category].append(filename)

            # Extract content
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()

            soup = BeautifulSoup(content, 'html.parser')

            # Remove navigation and non-content elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()

            # Get page title
            title = soup.find('title')
            page_title = title.get_text() if title else filename.replace('_', ' ').title()

            # Extract main text content
            text_content = soup.get_text()

            # Clean up text
            lines = text_content.split('\n')
            cleaned_lines = []

            for line in lines:
                line = line.strip()
                if line and len(line) > 3 and not any(skip in line.lower() for skip in [
                    'you need to enable javascript', 'log in', 'sign up', 'menu'
                ]):
                    cleaned_lines.append(line)

            clean_text = '\n'.join(cleaned_lines)
            clean_text = re.sub(r'\n\s*\n\s*\n', '\n\n', clean_text)

            # Save organized content
            category_dir = clean_dir / category
            category_dir.mkdir(exist_ok=True)

            clean_filename = filename + '_content.txt'
            clean_path = category_dir / clean_filename

            with open(clean_path, 'w', encoding='utf-8') as f:
                f.write(f"# {page_title}\n")
                f.write(f"Category: {category.replace('_', ' ').title()}\n")
                f.write(f"Source: {html_file.name}\n")
                f.write("=" * 80 + "\n\n")
                f.write(clean_text)

            extraction_summary.append({
                "filename": filename,
                "category": category,
                "title": page_title,
                "content_length": len(clean_text),
                "output_file": str(clean_path)
            })

            print(f"✅ {category:15} | {filename[:40]:40} | {len(clean_text):6,} chars")

        except Exception as e:
            print(f"❌ Failed: {html_file.name} - {str(e)}")

    # Create master index
    index_content = "# DATABENTO DOCUMENTATION - COMPLETE INDEX\n\n"
    index_content += f"Total files processed: {len(extraction_summary)}\n"
    index_content += f"Total content extracted: {sum(item['content_length'] for item in extraction_summary):,} characters\n\n"

    for category, files in categories.items():
        if files:
            index_content += f"## {category.replace('_', ' ').title()} ({len(files)} files)\n\n"
            category_files = [item for item in extraction_summary if item['category'] == category]
            for item in sorted(category_files, key=lambda x: x['filename']):
                index_content += f"- **{item['title']}**\n"
                index_content += f"  - File: `{item['filename']}_content.txt`\n"
                index_content += f"  - Size: {item['content_length']:,} characters\n\n"

    index_path = clean_dir / "INDEX.md"
    with open(index_path, 'w') as f:
        f.write(index_content)

    # Save extraction report
    report_path = clean_dir / "extraction_report.json"
    with open(report_path, 'w') as f:
        json.dump({
            "extraction_summary": extraction_summary,
            "categories": {k: len(v) for k, v in categories.items()},
            "total_files": len(extraction_summary),
            "total_content_chars": sum(item['content_length'] for item in extraction_summary)
        }, f, indent=2)

    print(f"\n🎯 EXTRACTION COMPLETE")
    print(f"📂 Organized into {len([k for k, v in categories.items() if v])} categories")
    print(f"📄 Master index: {index_path}")
    print(f"📊 Extraction report: {report_path}")

    return extraction_summary

if __name__ == "__main__":
    extract_all_content()
