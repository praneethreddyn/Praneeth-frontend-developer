import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent
GITHUB_USERNAME = "praneethreddyn"
EXCLUDED_REPOSITORIES = {"praneeth-frontend-developer"}
RESUME_TEMPLATE = ROOT / "Praneeth_Reddy_Nalamalapu_Resume.docx"
RESUME_FILENAME = "Praneeth_Reddy_Nalamalapu_Resume.docx"
GITHUB_API_URL = "https://api.github.com/users/{}/repos".format(
    urllib.parse.quote(GITHUB_USERNAME, safe="")
)
PARAGRAPH_PATTERN = re.compile(rb"<w:p(?:\s[^>]*)?>.*?</w:p>", re.DOTALL)
TEXT_PATTERN = re.compile(rb"<w:t(?:\s[^>]*)?>(.*?)</w:t>", re.DOTALL)
PARAGRAPH_PROPERTIES_PATTERN = re.compile(
    rb"<w:pPr(?:\s[^>]*)?>.*?</w:pPr>", re.DOTALL
)
RUN_PROPERTIES_PATTERN = re.compile(
    rb"<w:rPr(?:\s[^>]*)?>.*?</w:rPr>|<w:rPr(?:\s[^>]*)?/>", re.DOTALL
)


def fetch_repositories():
    repositories = []
    page = 1
    while True:
        url = "{}?type=owner&sort=updated&per_page=100&page={}".format(
            GITHUB_API_URL, page
        )
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "PraneethPortfolio/1.0",
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            page_repositories = json.loads(response.read().decode("utf-8"))
        if not isinstance(page_repositories, list):
            raise ValueError("GitHub returned an unexpected repository response.")
        repositories.extend(page_repositories)
        if len(page_repositories) < 100:
            return [
                repository
                for repository in repositories
                if str(repository.get("name", "")).casefold()
                not in EXCLUDED_REPOSITORIES
            ]
        page += 1


def paragraph_text(paragraph):
    text = " ".join(
        html.unescape(match.group(1).decode("utf-8"))
        for match in TEXT_PATTERN.finditer(paragraph)
    )
    text = text.replace("\t", " ")
    return re.sub(r"\s+", " ", text).strip()


def normalized_name(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())


def clean_text(value, limit):
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    value = "".join(
        char for char in value
        if char in "\t\n\r" or ord(char) >= 32
    )
    if len(value) > limit:
        value = value[: limit - 1].rsplit(" ", 1)[0] + "…"
    return value


def make_paragraph(text, template_paragraph):
    properties = PARAGRAPH_PROPERTIES_PATTERN.search(template_paragraph)
    run_properties = RUN_PROPERTIES_PATTERN.search(template_paragraph)
    parts = [b"<w:p>"]
    if properties:
        parts.append(properties.group(0))
    parts.append(b"<w:r>")
    if run_properties:
        parts.append(run_properties.group(0))
    encoded_text = html.escape(text, quote=False).encode("utf-8")
    parts.append(b'<w:t xml:space="preserve">' + encoded_text + b"</w:t></w:r></w:p>")
    return b"".join(parts)


def add_repositories_to_resume(repositories):
    if not RESUME_TEMPLATE.is_file():
        raise FileNotFoundError(
            "The resume template was not found: {}".format(RESUME_TEMPLATE.name)
        )

    output = BytesIO()
    with zipfile.ZipFile(RESUME_TEMPLATE, "r") as source:
        document_xml = source.read("word/document.xml")
        paragraphs = list(PARAGRAPH_PATTERN.finditer(document_xml))
        paragraph_texts = [paragraph_text(item.group(0)) for item in paragraphs]
        projects_index = next(
            (
                index
                for index, text in enumerate(paragraph_texts)
                if text.upper() == "PROJECTS"
            ),
            None,
        )
        education_index = next(
            (
                index
                for index, text in enumerate(paragraph_texts)
                if text.upper() == "EDUCATION"
            ),
            None,
        )
        if (
            projects_index is None
            or education_index is None
            or education_index <= projects_index
        ):
            raise ValueError("The resume template is missing its Projects or Education section.")

        project_paragraphs = paragraphs[projects_index + 1 : education_index]
        heading_template = next(
            (item.group(0) for item in project_paragraphs if b'w:pStyle w:val="ListParagraph"' not in item.group(0)),
            None,
        )
        bullet_template = next(
            (item.group(0) for item in project_paragraphs if b'w:pStyle w:val="ListParagraph"' in item.group(0)),
            None,
        )
        if heading_template is None or bullet_template is None:
            raise ValueError("The resume template is missing its project heading or description styles.")

        existing_names = set()
        for offset, text in enumerate(
            paragraph_texts[projects_index + 1 : education_index]
        ):
            paragraph = paragraphs[projects_index + 1 + offset].group(0)
            if text and b'w:pStyle w:val="ListParagraph"' not in paragraph:
                existing_names.add(
                    normalized_name(text.split("|", 1)[0].split("–", 1)[0].strip())
                )
        additions = []
        for repository in repositories:
            name = clean_text(repository.get("name"), 100)
            if name.casefold() in EXCLUDED_REPOSITORIES:
                continue
            url = clean_text(repository.get("html_url"), 300)
            if not name or not url:
                continue
            normalized = normalized_name(name)
            if any(normalized and normalized in existing for existing in existing_names):
                continue
            language = clean_text(repository.get("language") or "GitHub", 60)
            description = clean_text(
                repository.get("description")
                or "Explore this project in its GitHub repository.",
                360,
            )
            additions.append(
                make_paragraph("{} | {} | {}".format(name, language, url), heading_template)
            )
            additions.append(make_paragraph(description, bullet_template))
            existing_names.add(normalized)

        if additions:
            insertion_point = paragraphs[education_index].start()
            document_xml = (
                document_xml[:insertion_point]
                + b"".join(additions)
                + document_xml[insertion_point:]
            )

        with zipfile.ZipFile(output, "w") as generated:
            for entry in source.infolist():
                contents = (
                    document_xml
                    if entry.filename == "word/document.xml"
                    else source.read(entry.filename)
                )
                generated.writestr(entry, contents)
    return output.getvalue()


class PortfolioHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        origin = self.headers.get("Origin")
        if origin:
            parsed_origin = urlsplit(origin)
            if (
                parsed_origin.scheme == "http"
                and parsed_origin.hostname in ("localhost", "127.0.0.1")
            ):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
        super().end_headers()

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/repositories":
            self.handle_repositories()
        elif path == "/api/resume":
            self.handle_resume()
        else:
            super().do_GET()

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_repositories(self):
        try:
            self.send_json(200, fetch_repositories())
        except urllib.error.HTTPError as error:
            self.send_json(
                502,
                {"error": "GitHub API returned HTTP {}.".format(error.code)},
            )
        except (urllib.error.URLError, TimeoutError) as error:
            self.send_json(502, {"error": "Could not reach GitHub: {}".format(error)})
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json(502, {"error": "Could not read GitHub repositories: {}".format(error)})

    def handle_resume(self):
        try:
            resume = add_repositories_to_resume(fetch_repositories())
        except urllib.error.HTTPError as error:
            self.send_json(
                502,
                {"error": "GitHub API returned HTTP {}; the resume was not generated.".format(error.code)},
            )
            return
        except (urllib.error.URLError, TimeoutError) as error:
            self.send_json(502, {"error": "Could not reach GitHub; the resume was not generated: {}".format(error)})
            return
        except (OSError, ValueError, zipfile.BadZipFile, KeyError) as error:
            self.send_json(500, {"error": "Could not generate the resume: {}".format(error)})
            return

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.send_header(
            "Content-Disposition",
            'attachment; filename="{}"'.format(RESUME_FILENAME),
        )
        self.send_header("Content-Length", str(len(resume)))
        self.end_headers()
        self.wfile.write(resume)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), PortfolioHandler)
    print("Portfolio running at http://127.0.0.1:8000")
    print("Press Ctrl+C to stop the server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nPortfolio server stopped.")
    finally:
        server.server_close()
