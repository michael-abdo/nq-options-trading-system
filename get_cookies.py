import subprocess
import json

# Use osascript to interact with Chrome
script = '''
tell application "Google Chrome"
    set activeTab to active tab of front window
    set cookieJS to "JSON.stringify(document.cookie)"
    set cookieString to execute activeTab javascript cookieJS
    return cookieString
end tell
'''

result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
if result.returncode == 0:
    cookie_string = json.loads(result.stdout.strip())
    print(f"Cookie string from page: {cookie_string}")
    
    # Parse cookies
    cookies = {}
    for cookie in cookie_string.split('; '):
        if '=' in cookie:
            name, value = cookie.split('=', 1)
            cookies[name] = value
    
    # Save
    with open('page_cookies.json', 'w', json.dumps(cookies, indent=2))
    print(f"Saved {len(cookies)} cookies")
