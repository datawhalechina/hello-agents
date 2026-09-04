import re
import requests
from bs4 import BeautifulSoup

def browse(url, *, logger=None, proxy=None):
    content = ""
    try:
        request_options = {
            "headers": { "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36" }
        }
        if proxy:
            if proxy.startswith("http:"):
                request_options.update({ "proxies": { "http": proxy } })
            elif proxy.startswith("https:"):
                request_options.update({ "proxies": { "https": proxy } })
        page = requests.get(
            url,
            **request_options
        )
        soup = BeautifulSoup(page.content, "html.parser")
        # find text in p, list, pre (github code), td
        chunks = soup.find_all(["h1", "h2", "h3", "h4", "h5", "p", "pre", "td"])
        for chunk in chunks:
            if chunk.name.startswith("h"):
                content += "#" * int(chunk.name[-1]) + " " + chunk.get_text() + "\n"
            else:
                text = chunk.get_text()
                if text and text != "":
                    content += text + "\n"
        # find text in div that class=content
        divs = soup.find("div", class_="content")
        if divs:
            chunks_with_text = divs.find_all(text=True)
            for chunk in chunks_with_text:
                if isinstance(chunk, str) and chunk.strip():
                    content += chunk.strip() + "\n"
        content = re.sub(r"\n+", "\n", content)
        return content
    except Exception as e:
        if logger:
            logger.error(f"[Browse]: Can not browse '{ url }'.\tError: { str(e) }")
        return ""