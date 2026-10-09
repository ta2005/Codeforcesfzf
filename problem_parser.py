import re
import urllib.request
import bs4
from typing import Dict, Any, List, Optional


def html_to_markdown(html_content: Any) -> str:
    """Converts a Codeforces HTML element or string into readable Markdown."""
    if not html_content:
        return ""

    if isinstance(html_content, str):
        soup = bs4.BeautifulSoup(html_content, "html.parser")
    else:
        soup = bs4.BeautifulSoup(str(html_content), "html.parser")

    # 1. Clean math delimiters: Codeforces uses $$$formula$$$ for MathJax
    # Convert $$$x$$$ to $x$ for standard markdown math
    for text_node in soup.find_all(string=True):
        if "$$$" in text_node:
            new_text = re.sub(r"\$\$\$(.*?)\$\$\$", r"$\1$", text_node)
            text_node.replace_with(new_text)

    # 2. Format inline elements
    for b in soup.find_all(["b", "strong"]):
        b.replace_with(f"**{b.get_text()}**")

    for i in soup.find_all(["i", "em"]):
        i.replace_with(f"*{i.get_text()}*")

    for code in soup.find_all("code"):
        code.replace_with(f"`{code.get_text()}`")

    # 3. Format lists
    for ul in soup.find_all("ul"):
        list_items = []
        for li in ul.find_all("li", recursive=False):
            list_items.append(f"- {li.get_text().strip()}")
        ul.replace_with("\n" + "\n".join(list_items) + "\n")

    for ol in soup.find_all("ol"):
        list_items = []
        for idx, li in enumerate(ol.find_all("li", recursive=False), 1):
            list_items.append(f"{idx}. {li.get_text().strip()}")
        ol.replace_with("\n" + "\n".join(list_items) + "\n")

    # 4. Format paragraphs
    paragraphs = []
    for p in soup.find_all("p"):
        p_text = p.get_text().strip()
        if p_text:
            paragraphs.append(p_text)

    if paragraphs:
        return "\n\n".join(paragraphs)

    return soup.get_text().strip()


def split_limit(text: str) -> Dict[str, Any]:
    parts = text.split()
    if len(parts) >= 2:
        return {"value": parts[0], "unit": " ".join(parts[1:])}
    return {"value": text, "unit": ""}


def get_sample_tests(soup: bs4.BeautifulSoup) -> List[Dict[str, str]]:
    samples = []
    sample_div = soup.find("div", class_="sample-test")
    if not sample_div:
        return samples

    inputs = [p.get_text("\n").strip() for p in sample_div.select(".input pre")]
    outputs = [p.get_text("\n").strip() for p in sample_div.select(".output pre")]

    for inp, out in zip(inputs, outputs):
        samples.append({"input": inp, "output": out})

    return samples


def parse_problem(problem_id: str) -> Dict[str, Any]:
    url = f"https://codeforces.com/problemset/problem/{problem_id}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        markup = resp.read().decode("utf-8")

    soup = bs4.BeautifulSoup(markup, "html.parser")
    statement_div = soup.find("div", class_="problem-statement")
    if not statement_div:
        raise ValueError("Could not find problem statement element on the page.")

    # Title
    title_el = statement_div.find("div", class_="title")
    title = title_el.get_text().strip() if title_el else f"Problem {problem_id}"

    # Time & memory limits
    time_limit_el = statement_div.find("div", class_="time-limit")
    time_limit = split_limit(time_limit_el.contents[1].get_text().strip()) if time_limit_el and len(time_limit_el.contents) > 1 else {}

    mem_limit_el = statement_div.find("div", class_="memory-limit")
    mem_limit = split_limit(mem_limit_el.contents[1].get_text().strip()) if mem_limit_el and len(mem_limit_el.contents) > 1 else {}

    # Main statement text (after header, before input-specification)
    header = statement_div.find("div", class_="header")
    body_nodes = []
    if header:
        curr = header.next_sibling
        while curr and getattr(curr, "get", lambda _: None)("class") != ["input-specification"]:
            if getattr(curr, "get", lambda _: None)("class") == ["sample-tests"]:
                break
            body_nodes.append(str(curr))
            curr = curr.next_sibling
    raw_statement = "".join(body_nodes)
    statement_md = html_to_markdown(raw_statement)

    # Input & Output specs
    input_spec_el = statement_div.find("div", class_="input-specification")
    input_spec_md = ""
    if input_spec_el:
        # Remove the "Input" title if present
        title_p = input_spec_el.find("div", class_="section-title")
        if title_p:
            title_p.decompose()
        input_spec_md = html_to_markdown(str(input_spec_el))

    output_spec_el = statement_div.find("div", class_="output-specification")
    output_spec_md = ""
    if output_spec_el:
        title_p = output_spec_el.find("div", class_="section-title")
        if title_p:
            title_p.decompose()
        output_spec_md = html_to_markdown(str(output_spec_el))

    # Samples
    samples = get_sample_tests(statement_div)

    # Note
    note_el = statement_div.find("div", class_="note")
    note_md = ""
    if note_el:
        title_p = note_el.find("div", class_="section-title")
        if title_p:
            title_p.decompose()
        note_md = html_to_markdown(str(note_el))

    return {
        "id": problem_id,
        "title": title,
        "timeLimit": time_limit,
        "memoryLimit": mem_limit,
        "statement": statement_md,
        "inputSpecification": input_spec_md,
        "outputSpecification": output_spec_md,
        "samples": samples,
        "note": note_md,
    }


def format_problem_markdown(p: Dict[str, Any]) -> str:
    """Formats parsed problem dictionary into a clean Markdown document for terminal viewing."""
    sections = []

    # Title & limits
    sections.append(f"# {p.get('title', 'Problem')}")
    time_val = p.get('timeLimit', {}).get('value', '')
    time_unit = p.get('timeLimit', {}).get('unit', '')
    mem_val = p.get('memoryLimit', {}).get('value', '')
    mem_unit = p.get('memoryLimit', {}).get('unit', '')

    limits = []
    if time_val:
        limits.append(f"⏱️ **Time Limit:** {time_val} {time_unit}")
    if mem_val:
        limits.append(f"🧠 **Memory Limit:** {mem_val} {mem_unit}")
    if limits:
        sections.append(" | ".join(limits))

    sections.append("---")

    # Problem Statement
    if p.get("statement"):
        sections.append(p["statement"])

    # Input Specification
    if p.get("inputSpecification"):
        sections.append("### 📥 Input")
        sections.append(p["inputSpecification"])

    # Output Specification
    if p.get("outputSpecification"):
        sections.append("### 📤 Output")
        sections.append(p["outputSpecification"])

    # Samples
    samples = p.get("samples", [])
    if samples:
        sections.append("### 🧪 Examples")
        for idx, s in enumerate(samples, 1):
            sections.append(f"**Sample {idx}**")
            sections.append(f"**Input:**\n```\n{s.get('input', '')}\n```")
            sections.append(f"**Output:**\n```\n{s.get('output', '')}\n```")

    # Note
    if p.get("note"):
        sections.append("### 💡 Note")
        sections.append(p["note"])

    return "\n\n".join(sections) + "\n"


if __name__ == "__main__":
    import sys
    pid = sys.argv[1] if len(sys.argv) > 1 else "1/A"
    data = parse_problem(pid)
    print(format_problem_markdown(data))
