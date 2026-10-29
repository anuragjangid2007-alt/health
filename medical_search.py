import re
import requests
import xml.etree.ElementTree as ET

from html import unescape
from html.parser import HTMLParser


# MedlinePlus API URL
MEDLINEPLUS_API_URL = "https://wsearch.nlm.nih.gov/ws/query"


class HTMLTextExtractor(HTMLParser):
    """Remove HTML tags and extract readable text."""

    def __init__(self):
        super().__init__()
        self.text_parts = []

    def handle_data(self, data):
        self.text_parts.append(data)

    def get_text(self):
        return " ".join(self.text_parts)


def clean_text(value):
    """Clean HTML tags, entities, and extra whitespace."""

    if not value:
        return ""

    value = unescape(str(value))

    parser = HTMLTextExtractor()

    try:
        parser.feed(value)
        value = parser.get_text()
    except Exception:
        value = re.sub(r"<[^>]+>", " ", value)

    value = unescape(value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def search_medical_sources(question, max_results=5):
    """
    Search MedlinePlus for relevant healthcare information.

    Returns a list of dictionaries containing:
    title, summary, source_name, source_url, url,
    and source_type.
    """

    question = str(question).strip()

    if not question:
        return []

    try:
        response = requests.get(
            MEDLINEPLUS_API_URL,
            params={
                "db": "healthTopics",
                "term": question,
                "retmax": max_results,
            },
            headers={
                "User-Agent": "HealthCheckAI/1.0"
            },
            timeout=20,
        )

        response.raise_for_status()

        # Parse the XML response
        root = ET.fromstring(response.content)

        results = []

        # MedlinePlus provides each result as a document element.
        for document in root.findall(".//document"):

            # URL is an attribute of the document element.
            url = document.attrib.get("url", "").strip()

            # Only allow official MedlinePlus health-topic URLs.
            if not url.startswith("https://medlineplus.gov/"):
                continue

            title = ""
            summary = ""

            # Extract title and summary from content elements.
            for content in document.findall("content"):

                content_name = content.attrib.get(
                    "name", ""
                ).lower()

                content_value = clean_text(
                    "".join(content.itertext())
                )

                if content_name == "title":
                    title = content_value

                elif content_name in (
                    "fullsummary",
                    "snippet",
                    "description",
                ):
                    if content_value and not summary:
                        summary = content_value

            # Skip entries without a title.
            if not title:
                continue

            # Limit summary length for a readable dashboard.
            if len(summary) > 1200:
                summary = summary[:1200].rsplit(" ", 1)[0] + "..."

            results.append({
                "title": title,
                "summary": summary,
                "source_name": "MedlinePlus",
                "source_url": url,
                "url": url,

                # This key lets dashboard.html identify online results.
                "source_type": "online_reference",
            })

            if len(results) >= max_results:
                break

        return results

    except requests.exceptions.Timeout:
        print("MedlinePlus search timed out.")
        return []

    except requests.exceptions.RequestException as error:
        print("MedlinePlus connection error:", error)
        return []

    except ET.ParseError as error:
        print("Could not parse MedlinePlus response:", error)
        return []

    except Exception as error:
        print("Unexpected medical search error:", error)
        return []


# Test the medical search module directly.
if __name__ == "__main__":

    print("\nHealthCheck AI - Medical Search Test")
    print("=" * 40)

    test_question = "diabetes symptoms"

    print("Searching for:", test_question)

    medical_results = search_medical_sources(test_question)

    if medical_results:

        for index, item in enumerate(medical_results, start=1):

            print(f"\nResult {index}")
            print("Title:", item["title"])
            print("Summary:", item["summary"])
            print("Source:", item["source_name"])
            print("URL:", item["source_url"])
            print("Source Type:", item["source_type"])

    else:
        print("\nNo medical sources found.")
        print("Check your internet connection or API response.")