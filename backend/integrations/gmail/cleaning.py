"""Email body text cleaning utilities."""

import re
import html2text


def html_to_text(html: str) -> str:
    """Convert HTML to clean plain text."""
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.ignore_emphasis = True
    h.ignore_tables = False
    h.body_width = 0  # Don't wrap lines
    h.skip_internal_links = True
    h.inline_links = False
    h.protect_links = False
    return h.handle(html)


def sanitize_body_text(text: str) -> str:
    """Clean up email body text by removing noise and normalizing whitespace."""
    if not text:
        return ""

    # Replace non-breaking/figure spaces with regular spaces
    text = (
        text.replace("\u00a0", " ")
        .replace("\u2007", " ")
        .replace("\u202f", " ")
    )

    # Remove zero-width and soft hyphen style characters
    text = re.sub(r"[\u200b\u200c\u200d\uFEFF\u2060\u034f\u00ad]", "", text)
    
    # Remove HTML entities that might have survived
    text = re.sub(r'&nbsp;', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'&amp;', '&', text, flags=re.IGNORECASE)
    text = re.sub(r'&lt;', '<', text, flags=re.IGNORECASE)
    text = re.sub(r'&gt;', '>', text, flags=re.IGNORECASE)
    text = re.sub(r'&quot;', '"', text, flags=re.IGNORECASE)
    text = re.sub(r'&#\d+;', '', text)  # Remove numeric HTML entities
    
    # Remove any remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove URLs in parentheses like "( https://... )" - common in plain text newsletters
    # text = re.sub(r'\(\s*https?://[^\s\)]+\s*\)', '', text)
    
    # Remove standalone URLs on their own line
    # text = re.sub(r'^\s*https?://[^\s]+\s*$', '', text, flags=re.MULTILINE)
    
    # Remove inline URLs
    # text = re.sub(r'https?://[^\s]+', '', text)
    
    # Remove markdown-style links [text](url)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # Remove separator lines (---, ===, ___, ***) 
    text = re.sub(r'^[\-=_\*]{3,}\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^-{3,}\s*\w+\s*-{3,}\s*$', '', text, flags=re.MULTILINE)  # ---section---
    
    # Remove common footer patterns
    footer_patterns = [
        r'(?i)^.*unsubscribe.*$',
        r'(?i)^.*click\s+here\s+to\s+unsubscribe.*$',
        r'(?i)^.*privacy\s+policy.*$',
        r'(?i)^.*view\s+(this\s+)?(email\s+)?in\s+(your\s+)?browser.*$',
        r'(?i)^.*view\s+(this\s+)?(post\s+)?on\s+the\s+web.*$',
        r'(?i)^.*sent\s+to\s+\S+@\S+.*$',
        r'(?i)^\s*©\s*\d{4}.*$',  # Copyright lines
        r'(?i)^.*all\s+rights\s+reserved.*$',
    ]
    for pattern in footer_patterns:
        text = re.sub(pattern, '', text, flags=re.MULTILINE)
    
    # Remove email addresses that appear alone on a line
    # text = re.sub(r'^\s*[\w\.-]+@[\w\.-]+\.\w+\s*$', '', text, flags=re.MULTILINE)
    
    # Remove lines that are just "sponsored" or "advertisement"
    # text = re.sub(r'(?i)^\s*(sponsored|advertisement|ad)\s*(by\s+\w+)?\s*$', '', text, flags=re.MULTILINE)
    
    # Clean up empty parentheses left after URL removal
    text = re.sub(r'\(\s*\)', '', text)
    
    # Collapse excessive spaces and newlines
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove lines that are only whitespace or very short (likely artifacts)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Keep lines that have meaningful content (more than 2 chars, not just punctuation)
        if len(stripped) > 2 and not re.match(r'^[\*\-\=\#\|\s]+$', stripped):
            cleaned_lines.append(line)
        elif len(stripped) == 0 and cleaned_lines and cleaned_lines[-1].strip():
            # Keep single blank lines for paragraph separation
            cleaned_lines.append('')
    
    text = '\n'.join(cleaned_lines)
    
    # Final cleanup
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()
